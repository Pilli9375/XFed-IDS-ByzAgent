#!/usr/bin/env python
"""Run one pilot sweep and write a comparison table.

Each arm is a separate subprocess call to src.train.centralized, so every run
gets a clean interpreter, its own seed state, and its own artifact directory.
The table is then assembled from the metrics.json files each run wrote -- the
table is never computed here, only collected, so it cannot disagree with the
artifacts it summarizes.

Sweeps, in the order they should be run (each locks a value for the next):

  scaler        standard vs robust vs robust_clipped
  weights       none, inverse_sqrt, effective_number at three betas
  architecture  width/depth and dropout

Usage:
    python scripts/run_pilots.py --pilot scaler
    python scripts/run_pilots.py --pilot weights --max-epochs 20
    python scripts/run_pilots.py --pilot architecture
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

# Each arm: (tag_suffix, [CLI args to src.train.centralized])
PILOTS: dict[str, list[tuple[str, list[str]]]] = {
    "scaler": [
        ("standard",       ["--scaler", "standard"]),
        ("robust",         ["--scaler", "robust"]),
        ("robust_clipped", ["--scaler", "robust_clipped"]),
    ],
    # beta=0.999 saturates the effective-number formula at 10^3 samples, which
    # is uninformative when classes span 10^3 to 10^6. Swept rather than assumed.
    "weights": [
        ("none",      ["--weight-scheme", "none"]),
        ("invsqrt",   ["--weight-scheme", "inverse_sqrt"]),
        ("eff_999",   ["--weight-scheme", "effective_number", "--beta", "0.999"]),
        ("eff_9999",  ["--weight-scheme", "effective_number", "--beta", "0.9999"]),
        ("eff_99999", ["--weight-scheme", "effective_number", "--beta", "0.99999"]),
    ],
    "architecture": [
        ("h128_64_d01",      ["--hidden-dims", "128", "64", "--dropout", "0.1"]),
        ("h128_64_d03",      ["--hidden-dims", "128", "64", "--dropout", "0.3"]),
        ("h256_128_d01",     ["--hidden-dims", "256", "128", "--dropout", "0.1"]),
        ("h256_128_d03",     ["--hidden-dims", "256", "128", "--dropout", "0.3"]),
        ("h512_256_128_d01", ["--hidden-dims", "512", "256", "128", "--dropout", "0.1"]),
        ("h512_256_128_d03", ["--hidden-dims", "512", "256", "128", "--dropout", "0.3"]),
    ],
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pilot", required=True, choices=sorted(PILOTS))
    p.add_argument("--max-epochs", type=int, default=20,
                   help="Pilots are for ranking arms, not for the final number.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--extra", nargs=argparse.REMAINDER, default=[],
                   help="Passed through to every arm, e.g. --extra --scaler robust")
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    args = p.parse_args()

    arms = PILOTS[args.pilot]
    print(f"\n{args.pilot} pilot: {len(arms)} arms, {args.max_epochs} epochs each, seed {args.seed}\n")

    failed: list[str] = []
    for i, (suffix, arm_args) in enumerate(arms, 1):
        tag = f"pilot_{args.pilot}_{suffix}"
        cmd = [
            sys.executable, "-m", "src.train.centralized",
            "--tag", tag,
            "--max-epochs", str(args.max_epochs),
            "--seed", str(args.seed),
            *arm_args, *args.extra,
        ]
        print(f"[{i}/{len(arms)}] {suffix}")
        if subprocess.run(cmd).returncode != 0:
            print(f"  ARM FAILED: {suffix}")
            failed.append(suffix)

    # ---- collect ---------------------------------------------------------
    rows: list[dict] = []
    for suffix, _ in arms:
        mpath = args.results_dir / "centralized" / f"pilot_{args.pilot}_{suffix}" / "metrics.json"
        if not mpath.exists():
            continue
        m = json.loads(mpath.read_text())
        test = m["test"]
        row = {
            "arm": suffix,
            "val_macro_f1_headline": round(m["best_val_macro_f1_headline"], 4),
            "test_macro_f1_headline": round(test["macro_f1_headline"], 4),
            "test_macro_f1_all": round(test["macro_f1_all"], 4),
            "false_positive_rate": round(test["false_positive_rate"], 5),
            "attack_recall": round(test["attack_recall"], 4),
            "best_epoch": m["best_epoch"],
        }
        for fam, fm in test["per_class"].items():
            row[f"f1_{fam}"] = round(fm["f1"], 4)
        rows.append(row)

    if not rows:
        print("\nNo arm produced metrics. Nothing to compare.")
        return 1

    out = args.results_dir / "pilots"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{args.pilot}_comparison.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---- print -----------------------------------------------------------
    print(f"\n{args.pilot.upper()} PILOT\n")
    print(f"  {'arm':<18}{'val mF1':>9}{'test mF1':>10}{'FPR':>9}{'WebAttack':>11}{'DDoS':>8}{'Bot':>8}")
    for r in sorted(rows, key=lambda r: -r["val_macro_f1_headline"]):
        print(f"  {r['arm']:<18}{r['val_macro_f1_headline']:>9.4f}"
              f"{r['test_macro_f1_headline']:>10.4f}{r['false_positive_rate']:>9.5f}"
              f"{r.get('f1_WebAttack', 0):>11.4f}{r.get('f1_DDoS', 0):>8.4f}{r.get('f1_Bot', 0):>8.4f}")

    best = max(rows, key=lambda r: r["val_macro_f1_headline"])
    print(f"\n  Best on VALIDATION: {best['arm']}")
    print("  Select on the validation column. The test column is shown to confirm the")
    print("  ranking is not an artifact of the val split -- selecting on test would")
    print("  make every later test number optimistically biased.")
    if failed:
        print(f"\n  FAILED ARMS: {failed}")
    print(f"\n  written: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
