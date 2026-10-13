"""Efficiency Part B -- median and range across the timing sessions appended
to results/efficiency/inference_speed_sessions.jsonl by
tools/efficiency_inference_speed.py. Accuracy, size and hardware are taken
from the latest full session file (results/efficiency/inference_speed.json).

Run from project root: python tools/efficiency_inference_summary.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import yaml

cfg = yaml.safe_load(Path("configs/efficiency.yaml").read_text())["inference"]
sessions = [json.loads(l) for l in Path(cfg["sessions_log"]).read_text().splitlines() if l.strip()]
latest = json.loads(Path(cfg["output"]).read_text())

summary = {}
for v in cfg["variants"]:
    s = {}
    for k in ("p50_us", "p95_us", "rows_per_sec"):
        vals = [x[v][k] for x in sessions]
        s[k] = {"median_of_sessions": statistics.median(vals), "min": min(vals), "max": max(vals), "per_session": vals}
    f1s = {x[v]["val_macro_f1_headline"] for x in sessions}
    assert len(f1s) == 1, (v, f1s)  # accuracy must not vary between sessions
    lv = latest["variants"][v]
    summary[v] = {**s, "val_macro_f1_headline": lv["val_macro_f1_headline"],
                  "delta_vs_eager": lv["delta_vs_eager"],
                  "prediction_agreement_with_eager": lv["prediction_agreement_with_eager"],
                  "per_class_f1": lv["per_class_f1"],
                  "size_bytes": lv["size_bytes"], "file": lv["file"]}

out = {
    "source": (f"{len(sessions)} timing sessions in {cfg['sessions_log']} (each: "
               f"{cfg['latency']['repeats']} latency repeats x {cfg['latency']['n_rows']} single-row calls after "
               f"{cfg['latency']['warmup_calls']} warm-up calls; {cfg['throughput']['repeats']} throughput passes "
               f"after {cfg['throughput']['warmup_batches']} warm-up batches) plus {cfg['output']} for accuracy, "
               "size and hardware. Validation rows only. Script: tools/efficiency_inference_summary.py."),
    "kind": f"{len(sessions)} timing sessions, one machine; accuracy is deterministic (identical in every session)",
    "n_sessions": len(sessions),
    "session_times_utc": [x["measured_at_utc"] for x in sessions],
    "hardware": latest["hardware"],
    "protocol": latest["protocol"],
    "model": latest["model"],
    "variants": summary,
    "flag_delta_over_bound": latest["flag_delta_over_bound"],
    "variants_identical_to_eager_at_3dp": latest["variants_identical_to_eager_at_3dp"],
    "gemm_to_matmul_rewrite_check": latest["gemm_to_matmul_rewrite_check"],
}
Path("results/efficiency/inference_speed_summary.json").write_text(json.dumps(out, indent=2))
for v, s in summary.items():
    print(f"{v:18s} p50 {s['p50_us']['median_of_sessions']:.1f}us [{s['p50_us']['min']:.1f},{s['p50_us']['max']:.1f}]  "
          f"p95 {s['p95_us']['median_of_sessions']:.1f}us [{s['p95_us']['min']:.1f},{s['p95_us']['max']:.1f}]  "
          f"thr {s['rows_per_sec']['median_of_sessions']:,.0f}/s [{s['rows_per_sec']['min']:,.0f},{s['rows_per_sec']['max']:,.0f}]  "
          f"F1 {s['val_macro_f1_headline']:.4f} ({s['delta_vs_eager']:+.4f})  {s['size_bytes']:,} B")
