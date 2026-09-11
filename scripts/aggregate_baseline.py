#!/usr/bin/env python
"""Aggregate the 3-seed centralized baseline into mean +/- std.

Single-run numbers are not results (per project rules). This reads the three
metrics.json files the final baseline run wrote and produces the one table
that actually goes in the paper.

Usage:
    python scripts/aggregate_baseline.py
    python scripts/aggregate_baseline.py --tags baseline_s42 baseline_s1337 baseline_s2024
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, default=Path("results/centralized"))
    p.add_argument("--tags", nargs="+", default=["baseline_s42", "baseline_s1337", "baseline_s2024"])
    p.add_argument("--out", type=Path, default=Path("results/centralized_baseline_summary.json"))
    args = p.parse_args()

    runs = []
    for tag in args.tags:
        path = args.results_dir / tag / "metrics.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}. Run all {len(args.tags)} seeds before aggregating.")
        runs.append(json.loads(path.read_text()))

    class_names = runs[0]["class_names"]
    if any(r["class_names"] != class_names for r in runs):
        raise SystemExit("class_names differ across runs -- something is inconsistent, stop.")

    headline_f1 = np.array([r["test"]["macro_f1_headline"] for r in runs])
    all_f1 = np.array([r["test"]["macro_f1_all"] for r in runs])
    fpr = np.array([r["test"]["false_positive_rate"] for r in runs])
    recall = np.array([r["test"]["attack_recall"] for r in runs])

    print(f"\nCentralized baseline, {len(runs)} seeds\n")
    print(f"  macro-F1 (7 headline) : {headline_f1.mean():.4f} +/- {headline_f1.std():.4f}   {list(headline_f1.round(4))}")
    print(f"  macro-F1 (all 9)      : {all_f1.mean():.4f} +/- {all_f1.std():.4f}")
    print(f"  false positive rate   : {fpr.mean():.5f} +/- {fpr.std():.5f}")
    print(f"  attack recall         : {recall.mean():.4f} +/- {recall.std():.4f}")

    print(f"\n  {'family':<14}{'F1 mean':>10}{'F1 std':>9}{'support':>10}")
    per_class = {}
    for name in class_names:
        f1s = np.array([r["test"]["per_class"][name]["f1"] for r in runs])
        support = runs[0]["test"]["per_class"][name]["support"]
        mark = "" if name not in ("Heartbleed", "Infiltration") else "  (below floor)"
        print(f"  {name:<14}{f1s.mean():>10.4f}{f1s.std():>9.4f}{support:>10,}{mark}")
        per_class[name] = {"f1_mean": float(f1s.mean()), "f1_std": float(f1s.std()), "support": support}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "n_seeds": len(runs),
        "tags": args.tags,
        "macro_f1_headline_mean": float(headline_f1.mean()),
        "macro_f1_headline_std": float(headline_f1.std()),
        "macro_f1_all_mean": float(all_f1.mean()),
        "macro_f1_all_std": float(all_f1.std()),
        "false_positive_rate_mean": float(fpr.mean()),
        "false_positive_rate_std": float(fpr.std()),
        "attack_recall_mean": float(recall.mean()),
        "attack_recall_std": float(recall.std()),
        "per_class": per_class,
    }, indent=2))

    print(f"\n  written: {args.out}")
    print("\n  This is the reportable centralized number. Federated results (Chat 03")
    print("  next) get compared against this, not against any single pilot run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
