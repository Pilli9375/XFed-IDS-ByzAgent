#!/usr/bin/env python
"""Aggregate multi-seed runs into mean +/- std tables.

Single-run numbers are not results. This collects the per-seed metrics.json
files that src.train.centralized already wrote and produces the per-family
variance table required before any federated comparison can mean anything --
if the centralized baseline's own spread is unknown, a federated-vs-centralized
gap cannot be interpreted.

Reports population std (ddof=0) over the seeds actually run, and says n
explicitly. With n=3 no significance test is appropriate and none is computed:
mean and spread, stated honestly, is the defensible presentation.

Usage:
    python scripts/aggregate_seeds.py
    python scripts/aggregate_seeds.py --pattern "baseline_s*" --label centralized
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

HEADLINE_METRICS = [
    ("macro_f1_headline", "macro-F1 (7 headline)"),
    ("macro_f1_all", "macro-F1 (all 9)"),
    ("false_positive_rate", "false positive rate"),
    ("attack_recall", "attack recall"),
    ("accuracy", "accuracy"),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, default=Path("results/centralized"))
    p.add_argument("--pattern", default="baseline_s*")
    p.add_argument("--label", default="centralized")
    p.add_argument("--out-dir", type=Path, default=Path("results/aggregated"))
    p.add_argument("--cv-flag-threshold", type=float, default=0.01,
                   help="Flag a family whose F1 std/mean exceeds this.")
    args = p.parse_args()

    runs = sorted(args.results_dir.glob(args.pattern))
    loaded: list[tuple[str, dict]] = []
    for d in runs:
        mpath = d / "metrics.json"
        if mpath.exists():
            loaded.append((d.name, json.loads(mpath.read_text())))

    if not loaded:
        print(f"No metrics.json found under {args.results_dir}/{args.pattern}")
        return 1

    n = len(loaded)
    print(f"\n{args.label}: aggregating {n} run(s)")
    for name, _ in loaded:
        print(f"  - {name}")
    if n < 3:
        print(f"\n  WARNING: n={n}. Report this as a preliminary number, not a result.")

    class_names = loaded[0][1]["class_names"]

    # ---- headline ---------------------------------------------------------
    print(f"\n  {'metric':<24}{'mean':>10}{'std':>10}{'min':>10}{'max':>10}")
    headline_rows = []
    for key, label in HEADLINE_METRICS:
        vals = np.array([m["test"][key] for _, m in loaded], dtype=float)
        row = {
            "metric": label, "n": n,
            "mean": float(vals.mean()), "std": float(vals.std()),
            "min": float(vals.min()), "max": float(vals.max()),
        }
        headline_rows.append(row)
        print(f"  {label:<24}{row['mean']:>10.4f}{row['std']:>10.4f}"
              f"{row['min']:>10.4f}{row['max']:>10.4f}")

    # ---- per family -------------------------------------------------------
    print(f"\n  {'family':<14}{'F1 mean':>10}{'F1 std':>10}{'prec':>9}{'recall':>9}{'support':>10}")
    family_rows = []
    flagged: list[str] = []
    for fam in class_names:
        f1 = np.array([m["test"]["per_class"][fam]["f1"] for _, m in loaded], dtype=float)
        pr = np.array([m["test"]["per_class"][fam]["precision"] for _, m in loaded], dtype=float)
        rc = np.array([m["test"]["per_class"][fam]["recall"] for _, m in loaded], dtype=float)
        support = loaded[0][1]["test"]["per_class"][fam]["support"]

        cv = float(f1.std() / f1.mean()) if f1.mean() > 0 else 0.0
        if cv > args.cv_flag_threshold:
            flagged.append(fam)

        row = {
            "family": fam, "n": n, "support": support,
            "f1_mean": float(f1.mean()), "f1_std": float(f1.std()),
            "f1_min": float(f1.min()), "f1_max": float(f1.max()),
            "precision_mean": float(pr.mean()), "precision_std": float(pr.std()),
            "recall_mean": float(rc.mean()), "recall_std": float(rc.std()),
            "f1_cv": cv,
        }
        family_rows.append(row)
        mark = "  <-- unstable" if fam in flagged else ""
        print(f"  {fam:<14}{row['f1_mean']:>10.4f}{row['f1_std']:>10.4f}"
              f"{row['precision_mean']:>9.4f}{row['recall_mean']:>9.4f}{support:>10,}{mark}")

    if flagged:
        print(f"\n  Families with F1 coefficient of variation > {args.cv_flag_threshold}: {flagged}")
        print(f"  Seed-to-seed instability is a result to report, not noise to average away.")
        print(f"  Give per-seed values for these families rather than the mean alone.")

    # ---- per-seed detail for the unstable families ------------------------
    # F1 first, since the flag is computed on F1. Precision and recall are shown
    # alongside because they identify WHICH one is moving -- a family can be
    # flagged on F1 while its recall is identical across every seed.
    if flagged:
        print(f"\n  per-seed detail (flag is on F1; prec/recall show the source)")
        for fam in flagged:
            print(f"    {fam}")
            for metric in ("f1", "precision", "recall"):
                vals = "  ".join(
                    f"{name.split('_')[-1]}={m['test']['per_class'][fam][metric]:.4f}"
                    for name, m in loaded
                )
                print(f"      {metric:<10} {vals}")

    # ---- write ------------------------------------------------------------
    args.out_dir.mkdir(parents=True, exist_ok=True)

    hpath = args.out_dir / f"{args.label}_headline.csv"
    with hpath.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(headline_rows[0]))
        w.writeheader()
        w.writerows(headline_rows)

    fpath = args.out_dir / f"{args.label}_per_family.csv"
    with fpath.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(family_rows[0]))
        w.writeheader()
        w.writerows(family_rows)

    # LaTeX-ready, so the paper table is generated rather than transcribed.
    tex = [
        f"% mean +/- std over {n} seeds",
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Family & Test F1 (mean $\\pm$ std) & Support \\\\",
        "\\midrule",
    ]
    headline_set = set(loaded[0][1].get("headline_classes", []))
    for r in family_rows:
        note = "" if not headline_set or r["family"] in headline_set else "$^{\\dagger}$"
        tex.append(f"{r['family']}{note} & ${r['f1_mean']:.4f} \\pm {r['f1_std']:.4f}$ "
                   f"& {r['support']:,} \\\\")
    tex += ["\\bottomrule", "\\end{tabular}"]
    tpath = args.out_dir / f"{args.label}_per_family.tex"
    tpath.write_text("\n".join(tex))

    print(f"\n  written: {hpath}")
    print(f"  written: {fpath}")
    print(f"  written: {tpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
