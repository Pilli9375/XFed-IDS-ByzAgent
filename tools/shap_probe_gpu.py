"""Does running GradientExplainer on the GPU change the cost picture?

Every probe so far was CPU-only (hardcoded device="cpu"). The model is tiny
and the workload is pure forward/backward passes -- exactly what the RTX 4050
should accelerate heavily. Measure before compromising on nsamples or on the
number of explained rows.

Run from project root: python tools/shap_probe_gpu.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "federated")

import numpy as np
import shap
import torch

from xfed_federated import task  # noqa: E402

PROBE_ALPHA = "0.5"
PROBE_SEED = 42
PROBE_SILO = 0
MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")


def run_one(model, splits, device, n_bg, nsamples, n_explain=5):
    rng = np.random.default_rng(0)
    n_bg = min(n_bg, len(splits.y_train))
    bg_idx = rng.choice(len(splits.y_train), size=n_bg, replace=False)
    background = torch.from_numpy(splits.X_train[bg_idx].copy()).to(device)

    ex_idx = rng.choice(len(splits.y_train), size=n_explain, replace=False)
    explain_X = torch.from_numpy(splits.X_train[ex_idx].copy()).to(device)

    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explain_X, nsamples=nsamples)
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - t0

    sv = np.array(shap_values)
    with torch.no_grad():
        f_explain = model(explain_X).cpu().numpy()
        f_bg_mean = model(background).cpu().numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_explain - f_bg_mean[None, :])
    return float(np.abs(diff).max()), elapsed


def main() -> int:
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device: {torch.cuda.get_device_name(0)}")
        free, total = torch.cuda.mem_get_info()
        print(f"VRAM free/total: {free/1e9:.2f} / {total/1e9:.2f} GB")
    else:
        print("No CUDA -- this probe can only report CPU timings.")

    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    splits = task.load_silo_for_client(
        PROBE_SILO, PROBE_ALPHA, PROBE_SEED, data_cfg, model_cfg, class_weights
    )

    tag = f"fedavg_a{PROBE_ALPHA}_s{PROBE_SEED}"
    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = next(e for e in manifest if e["tag"] == tag)
    ckpt_path = entry["silo_checkpoints"][PROBE_SILO]

    devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    NSAMPLES = 4000  # fixed; we're measuring device speedup, not convergence

    print(f"\n{'device':<8}{'nsamples':<10}{'max_abs_diff':<15}"
          f"{'sec_for_5_rows':<17}{'sec_per_row'}")
    print("-" * 65)

    timings = {}
    for device in devices:
        model = task.build_model(model_cfg, seed=PROBE_SEED, device=device)
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        model.eval()

        max_diff, elapsed = run_one(model, splits, device, n_bg=200, nsamples=NSAMPLES)
        per_row = elapsed / 5
        timings[device] = per_row
        print(f"{device:<8}{NSAMPLES:<10}{max_diff:<15.4f}{elapsed:<17.1f}{per_row:.2f}")

    if "cuda" in timings and "cpu" in timings:
        speedup = timings["cpu"] / timings["cuda"]
        print(f"\nGPU speedup: {speedup:.1f}x")
        gpu_per_row = timings["cuda"]
        print("\nFull-pipeline estimates on GPU (90 config-silo pairs):")
        for n_rows in (20, 50, 100, 200):
            for ns, scale in ((4000, 1.0), (16000, 4.0)):
                total_min = gpu_per_row * scale * n_rows * 90 / 60
                print(f"  nsamples={ns:<6} {n_rows:>3} rows/silo -> "
                      f"{total_min:>8.1f} min ({total_min/60:.1f} hr)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
