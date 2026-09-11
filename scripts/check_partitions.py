#!/usr/bin/env python
"""Pre-flight check on the materialized Dirichlet partitions.

Matches the actual on-disk layout:
  assign_a{alpha}_s{seed}_{train|test}.parquet   -> one column: 'silo'
  label_distribution_a{alpha}_s{seed}.csv        -> per-silo class counts (train only)

Answers one question before any Flower code exists: does any (alpha, seed)
combination produce a silo that will *crash* a federated round?

HARD failures (exit 1):
  - a silo with zero TRAIN rows              -> fit() iterates an empty loader
  - a silo with zero TEST rows               -> evaluate() returns NaN, poisons aggregation
  - a class absent from the union of all TRAIN shards at a given seed
    (i.e. a column in label_distribution that sums to zero across all silos)

SOFT findings (reported, exit 0):
  - single-class silos, tiny silos, min/max silo size per (alpha, seed)

Usage:
    python scripts/check_partitions.py --partition-dir data/processed/partitions
    python scripts/check_partitions.py --partition-dir ... --alphas 0.1 0.5 5.0 --seeds 42 1337 2024
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--partition-dir", type=Path, required=True)
    p.add_argument("--alphas", nargs="+", default=["0.1", "0.5", "5.0"])
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 1337, 2024])
    p.add_argument("--n-silos", type=int, default=10)
    p.add_argument("--small-silo-threshold", type=int, default=500,
                   help="Reported only. Not a floor — locked decision 5 forbids exclusion from training.")
    p.add_argument("--out", type=Path, default=Path("results/partition_check.json"))
    args = p.parse_args()

    hard_failures: list[str] = []
    report: dict[str, dict] = {}

    for alpha, seed in product(args.alphas, args.seeds):
        key = f"a{alpha}_s{seed}"
        entry: dict = {}

        # --- row counts per silo, train + test, from the assign_* files ---
        for split in ("train", "test"):
            path = args.partition_dir / f"assign_a{alpha}_s{seed}_{split}.parquet"
            if not path.exists():
                hard_failures.append(f"MISSING SHARD: {path}")
                continue
            df = pd.read_parquet(path)
            counts = df["silo"].value_counts().reindex(range(args.n_silos), fill_value=0)
            empty = counts[counts == 0].index.tolist()
            if empty:
                hard_failures.append(f"EMPTY {split.upper()} SILOS at {key}: {empty}")
            entry[split] = {
                "rows_per_silo": counts.tolist(),
                "min_silo": int(counts.min()),
                "max_silo": int(counts.max()),
                "empty_silos": empty,
                "silos_below_threshold": counts[counts < args.small_silo_threshold].index.tolist(),
            }

        # --- class vocabulary + single-class silos, from label_distribution CSV (train only) ---
        dist_path = args.partition_dir / f"label_distribution_a{alpha}_s{seed}.csv"
        if not dist_path.exists():
            hard_failures.append(f"MISSING LABEL DISTRIBUTION: {dist_path}")
        else:
            dist = pd.read_csv(dist_path, index_col="silo")
            class_totals = dist.sum(axis=0)
            dead_classes = class_totals[class_totals == 0].index.tolist()
            if dead_classes:
                hard_failures.append(
                    f"CLASS ABSENT FROM ALL TRAIN SHARDS at {key}: {dead_classes}"
                )
            per_silo_class_count = (dist > 0).sum(axis=1)
            entry["single_class_silos"] = per_silo_class_count[per_silo_class_count == 1].index.tolist()
            entry["classes_per_silo"] = per_silo_class_count.reindex(range(args.n_silos), fill_value=0).tolist()

        report[key] = entry
        tr = entry.get("train", {})
        if tr:
            print(
                f"{key:14s} train min={tr['min_silo']:>8,}  max={tr['max_silo']:>9,}  "
                f"empty={len(tr['empty_silos'])}  single-class={len(entry.get('single_class_silos', []))}  "
                f"below {args.small_silo_threshold}={len(tr['silos_below_threshold'])}"
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(f"\nWritten: {args.out}")

    if hard_failures:
        print("\nHARD FAILURES — do not write Flower code until these are resolved:")
        for f in hard_failures:
            print(f"  - {f}")
        return 1

    print("\nNo hard failures. Every silo has train and test rows at every (alpha, seed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
