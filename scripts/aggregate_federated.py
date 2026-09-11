#!/usr/bin/env python
"""Aggregate the 9-combination (alpha x seed) federated sweep.

Reads results/federated/fedavg_a{alpha}_s{seed}/final_metrics.json for every
combination and produces:

  federated_headline.csv     macro-F1 mean/std/min/max per alpha
  federated_per_family.csv   per-family F1 mean/std per alpha
  federated_collapse.csv     every (alpha, seed, family) where recall fell
                              below --collapse-threshold -- the evidence for
                              the "which family gets erased is arbitrary"
                              finding, not an average that would hide it
  round_lottery.csv          best-by-val vs final-round test macro-F1 per run,
                              quantifying how much the validation-selection
                              fix actually mattered

Usage:
    python scripts/aggregate_federated.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ALPHAS = ["0.1", "0.5", "5.0"]
SEEDS = [42, 1337, 2024]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, default=Path("results/federated"))
    p.add_argument("--out-dir", type=Path, default=Path("results/aggregated"))
    p.add_argument("--collapse-threshold", type=float, default=0.05,
                   help="Headline-family recall below this counts as collapsed.")
    args = p.parse_args()

    runs: dict[str, dict] = {}
    missing = []
    for alpha in ALPHAS:
        for seed in SEEDS:
            path = args.results_dir / f"fedavg_a{alpha}_s{seed}" / "final_metrics.json"
            if path.exists():
                runs[f"{alpha}_{seed}"] = json.loads(path.read_text())
            else:
                missing.append(str(path))

    if missing:
        print("MISSING RUNS:")
        for m in missing:
            print(f"  {m}")
    print(f"\nLoaded {len(runs)}/9 runs\n")
    if not runs:
        return 1

    headline_names = next(iter(runs.values()))["headline_classes"]
    class_names = next(iter(runs.values()))["class_names"]

    # ---- headline table -----------------------------------------------
    print(f"  {'alpha':<8}{'n':>4}{'mean':>10}{'std':>10}{'min':>10}{'max':>10}")
    headline_rows = []
    for alpha in ALPHAS:
        vals = [runs[f"{alpha}_{s}"]["test"]["macro_f1_headline"]
                for s in SEEDS if f"{alpha}_{s}" in runs]
        if not vals:
            continue
        arr = np.array(vals)
        row = {"alpha": alpha, "n": len(vals),
               "mean": float(arr.mean()), "std": float(arr.std()),
               "min": float(arr.min()), "max": float(arr.max())}
        headline_rows.append(row)
        print(f"  {alpha:<8}{row['n']:>4}{row['mean']:>10.4f}{row['std']:>10.4f}"
              f"{row['min']:>10.4f}{row['max']:>10.4f}")

    # ---- per-family table -----------------------------------------------
    family_rows = []
    print(f"\n  per-family F1 mean (std) by alpha:")
    print(f"  {'family':<14}" + "".join(f"{'a='+a:>18}" for a in ALPHAS))
    for fam in class_names:
        line = f"  {fam:<14}"
        row = {"family": fam}
        for alpha in ALPHAS:
            vals = [runs[f"{alpha}_{s}"]["test"]["per_class"][fam]["f1"]
                    for s in SEEDS if f"{alpha}_{s}" in runs]
            if vals:
                arr = np.array(vals)
                row[f"a{alpha}_mean"] = float(arr.mean())
                row[f"a{alpha}_std"] = float(arr.std())
                line += f"{arr.mean():>12.4f}±{arr.std():.3f}"
            else:
                line += f"{'--':>18}"
        family_rows.append(row)
        print(line)

    # ---- collapse table: the arbitrary-erasure evidence -------------------
    collapse_rows = []
    print(f"\n  HEADLINE FAMILIES WITH RECALL < {args.collapse_threshold} (collapsed):")
    for alpha in ALPHAS:
        for seed in SEEDS:
            key = f"{alpha}_{seed}"
            if key not in runs:
                continue
            per_class = runs[key]["test"]["per_class"]
            collapsed = [f for f in headline_names if per_class[f]["recall"] < args.collapse_threshold]
            if collapsed:
                print(f"    alpha={alpha:<6} seed={seed:<6} -> {collapsed}")
            for fam in collapsed:
                collapse_rows.append({
                    "alpha": alpha, "seed": seed, "family": fam,
                    "recall": per_class[fam]["recall"],
                    "precision": per_class[fam]["precision"],
                    "support": per_class[fam]["support"],
                })
    if not collapse_rows:
        print("    none")

    # ---- round lottery: best-by-val vs final-round, per run ---------------
    lottery_rows = []
    print(f"\n  ROUND LOTTERY (best-by-val vs final-round test macro-F1):")
    print(f"  {'alpha':<8}{'seed':<8}{'best':>10}{'final':>10}{'gap':>10}")
    for alpha in ALPHAS:
        for seed in SEEDS:
            key = f"{alpha}_{seed}"
            if key not in runs:
                continue
            r = runs[key]
            best = r["test"]["macro_f1_headline"]
            final = r.get("test_final_round_unselected", {}).get("macro_f1_headline")
            if final is None:
                continue
            gap = best - final
            lottery_rows.append({"alpha": alpha, "seed": seed,
                                 "best": best, "final": final, "gap": gap})
            print(f"  {alpha:<8}{seed:<8}{best:>10.4f}{final:>10.4f}{gap:>10.4f}")

    # ---- write --------------------------------------------------------
    args.out_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(name, rows):
        if not rows:
            return
        path = args.out_dir / name
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  written: {path}")

    write_csv("federated_headline.csv", headline_rows)
    write_csv("federated_per_family.csv", family_rows)
    write_csv("federated_collapse.csv", collapse_rows)
    write_csv("round_lottery.csv", lottery_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
