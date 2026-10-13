"""Efficiency Part B -- inference speed of the served model
(fedavg_a0.5_s42, round 18) as PyTorch eager, ONNX Runtime fp32 and ONNX
Runtime int8 (dynamic quantization). Validation rows only.

The eager model, scaler and validation split come from
backend/model_loader.load_and_verify(), which re-checks validation macro-F1
against round_history.json before returning and never reads
test_global.parquet. Timings cover the forward pass on already-scaled float32
rows; the scaler is identical for every variant and is not timed.

Run from project root: python tools/efficiency_inference_speed.py
"""
from __future__ import annotations

import pyarrow  # noqa: F401  -- must import before torch in this env (parquet segfault)

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import pandas as pd
import torch
import yaml
from onnx import helper, numpy_helper
from onnxruntime.quantization import QuantType, quantize_dynamic

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.model_loader import (  # noqa: E402
    _load_manifest_entry,
    load_and_verify,
    load_backend_config,
    resolve_path,
)
from src.data.schema import encode_families, load_label_vocabulary  # noqa: E402
from src.train.metrics import compute_metrics  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs/efficiency.yaml"


def cpu_name() -> str:
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor).Name"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return out or platform.processor()
    except Exception:
        return platform.processor()


def gemm_to_matmul(model: onnx.ModelProto) -> onnx.ModelProto:
    """Rewrite each Gemm(A, B, C; transB=1, alpha=beta=1) as MatMul(A, B^T) + C.
    ONNX Runtime's dynamic quantizer quantizes MatMul but not Gemm, which is
    what torch exports for nn.Linear."""
    g = model.graph
    inits = {i.name: i for i in g.initializer}
    new_nodes = []
    for node in g.node:
        if node.op_type != "Gemm":
            new_nodes.append(node)
            continue
        attrs = {a.name: helper.get_attribute_value(a) for a in node.attribute}
        assert attrs.get("alpha", 1.0) == 1.0 and attrs.get("beta", 1.0) == 1.0, attrs
        assert attrs.get("transA", 0) == 0, attrs
        a, b, c = node.input
        w = numpy_helper.to_array(inits[b])
        if attrs.get("transB", 0) == 1:
            w = w.T
        wt_name = b + "_T"
        g.initializer.append(numpy_helper.from_array(np.ascontiguousarray(w), wt_name))
        mm_out = node.output[0] + "_mm"
        new_nodes.append(helper.make_node("MatMul", [a, wt_name], [mm_out], name=node.name + "_matmul"))
        new_nodes.append(helper.make_node("Add", [mm_out, c], [node.output[0]], name=node.name + "_add"))
    del g.node[:]
    g.node.extend(new_nodes)
    used = {i for n in g.node for i in n.input}
    keep = [i for i in g.initializer if i.name in used]
    del g.initializer[:]
    g.initializer.extend(keep)
    onnx.checker.check_model(model)
    return model


def op_counts(path: Path) -> dict[str, int]:
    m = onnx.load(str(path))
    counts: dict[str, int] = {}
    for n in m.graph.node:
        counts[n.op_type] = counts.get(n.op_type, 0) + 1
    return counts


def main() -> None:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["inference"]
    threads = int(cfg["intra_op_threads"])
    torch.set_num_threads(threads)

    # ---- served model, verified on validation by the backend's own loader ----
    loaded = load_and_verify(cfg["backend_config"])
    assert loaded.tag == cfg["expected_tag"], loaded.tag
    assert loaded.best_round == cfg["expected_best_round"], loaded.best_round
    model = loaded.model.cpu().eval()

    bcfg = load_backend_config(cfg["backend_config"])
    paths = bcfg["paths"]
    entry = _load_manifest_entry(resolve_path(paths, "best_rounds_manifest"), loaded.tag)
    ckpt_path = PROJECT_ROOT / entry["global_checkpoint"]

    # Validation rows: train_pool rows where val_mask is True (same as the loader).
    pool = pd.read_parquet(resolve_path(paths, "train_pool"), columns=loaded.feature_cols + ["family"])
    mask = pd.read_parquet(resolve_path(paths, "val_mask"))["is_val"].to_numpy()
    X_val = loaded.scaler.transform(pool.loc[mask, loaded.feature_cols].to_numpy(np.float32)).astype(np.float32)
    y_val = encode_families(pool.loc[mask, "family"], load_label_vocabulary(loaded.model_cfg))
    del pool
    n_classes = int(loaded.model_cfg["labels"]["n_classes"])
    print(f"validation rows: {len(X_val):,}")

    # ---- export ----
    onnx_dir = PROJECT_ROOT / cfg["onnx"]["dir"]
    onnx_dir.mkdir(parents=True, exist_ok=True)
    fp32_path = onnx_dir / f"{loaded.tag}_r{loaded.best_round:03d}_fp32.onnx"
    mm_path = onnx_dir / f"{loaded.tag}_r{loaded.best_round:03d}_fp32_matmul.onnx"
    int8_path = onnx_dir / f"{loaded.tag}_r{loaded.best_round:03d}_int8_dynamic.onnx"
    torch.onnx.export(
        model, torch.from_numpy(X_val[:2]), str(fp32_path),
        input_names=["x"], output_names=["logits"],
        dynamic_axes={"x": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=int(cfg["onnx"]["opset"]), do_constant_folding=True, dynamo=False,
    )
    onnx.save(gemm_to_matmul(onnx.load(str(fp32_path))), str(mm_path))
    quantize_dynamic(str(mm_path), str(int8_path),
                     weight_type=getattr(QuantType, cfg["onnx"]["int8_weight_type"]))

    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    sessions = {
        "ort_fp32": ort.InferenceSession(str(fp32_path), so, providers=["CPUExecutionProvider"]),
        "ort_int8_dynamic": ort.InferenceSession(str(int8_path), so, providers=["CPUExecutionProvider"]),
    }

    def make_fn(variant):
        if variant == "torch_eager":
            @torch.inference_mode()
            def fn(x):
                return model(torch.from_numpy(x)).numpy()
            return fn
        sess = sessions[variant]
        return lambda x: sess.run(None, {"x": x})[0]

    files = {"torch_eager": ckpt_path, "ort_fp32": fp32_path, "ort_int8_dynamic": int8_path}
    lat_cfg, thr_cfg = cfg["latency"], cfg["throughput"]
    rng = np.random.default_rng(int(lat_cfg["sample_seed"]))
    lat_idx = rng.choice(len(X_val), size=int(lat_cfg["n_rows"]), replace=False)
    bs = int(thr_cfg["batch_size"])

    results = {}
    eager_f1 = None
    for variant in cfg["variants"]:
        fn = make_fn(variant)

        # -- accuracy on the full validation split (batched) --
        preds = np.concatenate([fn(X_val[i:i + bs]).argmax(1) for i in range(0, len(X_val), bs)])
        m = compute_metrics(y_val, preds, n_classes, loaded.class_names, loaded.headline_idx)

        # -- latency, batch 1 --
        for i in range(int(lat_cfg["warmup_calls"])):
            fn(X_val[lat_idx[i % len(lat_idx)]][None, :])
        lat_repeats = []
        for _ in range(int(lat_cfg["repeats"])):
            t = np.empty(len(lat_idx))
            for k, i in enumerate(lat_idx):
                x = X_val[i][None, :]
                t0 = time.perf_counter_ns()
                fn(x)
                t[k] = time.perf_counter_ns() - t0
            lat_repeats.append({"p50_us": float(np.percentile(t, 50) / 1e3),
                                "p95_us": float(np.percentile(t, 95) / 1e3),
                                "mean_us": float(t.mean() / 1e3)})
        all_p50 = [r["p50_us"] for r in lat_repeats]
        all_p95 = [r["p95_us"] for r in lat_repeats]

        # -- throughput, batch 1024 --
        n_full = (len(X_val) // bs) * bs  # full batches only, so every call is batch 1024
        for i in range(int(thr_cfg["warmup_batches"])):
            fn(X_val[i * bs:(i + 1) * bs])
        thr_repeats = []
        for _ in range(int(thr_cfg["repeats"])):
            t0 = time.perf_counter()
            for i in range(0, n_full, bs):
                fn(X_val[i:i + bs])
            thr_repeats.append(n_full / (time.perf_counter() - t0))

        f1 = m["macro_f1_headline"]
        if variant == "torch_eager":
            eager_f1, eager_preds = f1, preds
        results[variant] = {
            "file": str(files[variant].relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "size_bytes": files[variant].stat().st_size,
            "val_macro_f1_headline": f1,
            "val_macro_f1_all": m["macro_f1_all"],
            "delta_vs_eager": f1 - eager_f1,
            "prediction_agreement_with_eager": float((preds == eager_preds).mean()),
            "per_class_f1": {c: v["f1"] for c, v in m["per_class"].items()},
            "latency_batch1": {"p50_us_median_of_repeats": float(np.median(all_p50)),
                               "p95_us_median_of_repeats": float(np.median(all_p95)),
                               "repeats": lat_repeats},
            "throughput_batch1024": {"rows_per_sec_median_of_repeats": float(np.median(thr_repeats)),
                                     "rows_per_sec_repeats": thr_repeats,
                                     "rows_per_repeat": n_full},
        }
        if variant != "torch_eager":
            results[variant]["onnx_op_counts"] = op_counts(files[variant])
        r = results[variant]
        print(f"{variant:18s} F1={f1:.4f} d={r['delta_vs_eager']:+.4f} agree={r['prediction_agreement_with_eager']:.6f} "
              f"p50={r['latency_batch1']['p50_us_median_of_repeats']:.1f}us "
              f"p95={r['latency_batch1']['p95_us_median_of_repeats']:.1f}us "
              f"thr={r['throughput_batch1024']['rows_per_sec_median_of_repeats']:,.0f}/s "
              f"size={r['size_bytes']:,}B")

    # The int8 model is quantized from the Gemm->MatMul rewrite; check that the
    # rewrite alone (still fp32) reproduces eager predictions exactly.
    mm_sess = ort.InferenceSession(str(mm_path), so, providers=["CPUExecutionProvider"])
    mm_preds = np.concatenate([mm_sess.run(None, {"x": X_val[i:i + bs]})[0].argmax(1)
                               for i in range(0, len(X_val), bs)])
    rewrite_check = {"file": str(mm_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                     "prediction_agreement_with_eager": float((mm_preds == eager_preds).mean())}
    print(f"rewrite check (fp32 MatMul graph vs eager): {rewrite_check['prediction_agreement_with_eager']:.6f}")

    flagged = [v for v, r in results.items() if abs(r["delta_vs_eager"]) > cfg["max_abs_macro_f1_delta"]]
    dec = int(cfg["backend_wiring_decimals"])
    wiring_ok = [v for v, r in results.items()
                 if v != "torch_eager" and round(r["val_macro_f1_headline"], dec) == round(eager_f1, dec)]

    out = {
        "source": ("Timing runs on validation rows only (train_pool rows with val_mask=True, "
                   f"{len(X_val):,} rows); model, scaler and validation check from "
                   "backend/model_loader.load_and_verify(). Script: tools/efficiency_inference_speed.py. "
                   "Config: configs/efficiency.yaml (inference). No test rows read."),
        "kind": "single timing session on one machine",
        "model": {"tag": loaded.tag, "best_round": loaded.best_round,
                  "checkpoint": str(ckpt_path.relative_to(PROJECT_ROOT)).replace("\\", "/")},
        "hardware": {"cpu": cpu_name(), "logical_cpus": __import__("os").cpu_count(),
                     "os": platform.platform(), "python": platform.python_version(),
                     "torch": torch.__version__, "onnxruntime": ort.__version__, "onnx": onnx.__version__,
                     "intra_op_threads": threads, "device": "cpu"},
        "protocol": {"latency": lat_cfg, "throughput": thr_cfg,
                     "timed": "forward pass on already-scaled float32 rows (scaler not timed)",
                     "metric": "macro_f1_headline (7 families, Infiltration/Heartbleed excluded)"},
        "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "variants": results,
        "gemm_to_matmul_rewrite_check": rewrite_check,
        "flag_delta_over_bound": flagged,
        "variants_identical_to_eager_at_3dp": wiring_ok,
    }
    out_path = PROJECT_ROOT / cfg["output"]
    out_path.write_text(json.dumps(out, indent=2))
    # Laptop timings vary between sessions; every session is appended here so
    # the report can give the spread across sessions, not one run.
    with open(PROJECT_ROOT / cfg["sessions_log"], "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "measured_at_utc": out["measured_at_utc"],
            **{v: {"p50_us": r["latency_batch1"]["p50_us_median_of_repeats"],
                   "p95_us": r["latency_batch1"]["p95_us_median_of_repeats"],
                   "rows_per_sec": r["throughput_batch1024"]["rows_per_sec_median_of_repeats"],
                   "val_macro_f1_headline": r["val_macro_f1_headline"]}
               for v, r in results.items()}}) + "\n")
    print(f"flagged (|delta| > {cfg['max_abs_macro_f1_delta']}): {flagged}")
    print(f"identical to eager at {dec} dp: {wiring_ok}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
