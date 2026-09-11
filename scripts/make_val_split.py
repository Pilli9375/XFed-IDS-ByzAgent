#!/usr/bin/env python
"""Carve a group-aware validation mask out of train_pool.parquet.

The group key is reproduced EXACTLY from families.py (lines 99-105):

    feature_cols = [c for c in df.columns
                    if c not in ("family", "below_floor", "is_attempted", "__source_file")
                    and c not in (label_col, attempted_col)
                    and c not in set(identifier_cols)]
    groups = pd.util.hash_pandas_object(df[feature_cols], index=False)

The group IS the feature vector. hash_pandas_object combines per-column hashes in
column order, so the derivation must reproduce the same list in the same order --
hence reading configs/data.yaml rather than reimplementing the exclusion by hand.

Writes a boolean mask of length len(train_pool), in train_pool's positional order,
which is the same order as the `silo` column in assign_*.parquet. That alignment
keeps the 9 partition files and their SHA256 manifest valid and untouched.

Refuses to write if:
  - the derived feature count is not 82
  - any group spans the train/val boundary
  - any headline family lands entirely on one side (families.py lines 140-144
    flags this risk for the 75/25 split; it is sharper at 90/10)

Usage:
    python scripts/make_val_split.py
    python scripts/make_val_split.py --val-fraction 0.10 --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import StratifiedGroupKFold

NON_FEATURE_COLS = ("family", "below_floor", "is_attempted", "__source_file")
EXPECTED_N_FEATURES = 82

HEADLINE_FAMILIES = ["Benign", "Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]


def derive_feature_cols(df: pd.DataFrame, cfg: dict) -> list[str]:
    """Reproduce families.py's feature_cols derivation exactly, order included."""
    try:
        schema = cfg["schema"]
        label_col = schema["label_col"]
        attempted_col = schema["attempted_col"]
        identifier_cols = set(schema["identifier_cols"])
    except KeyError as e:
        raise SystemExit(
            f"configs/data.yaml is missing schema key {e}. The val split must use the "
            f"same exclusion logic as families.py; it will not guess."
        )

    return [
        c for c in df.columns
        if c not in NON_FEATURE_COLS
        and c not in (label_col, attempted_col)
        and c not in identifier_cols
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--train-pool", type=Path, default=Path("data/processed/train_pool.parquet"))
    p.add_argument("--data-config", type=Path, default=Path("configs/data.yaml"))
    p.add_argument("--out", type=Path, default=Path("data/processed/val_mask.parquet"))
    p.add_argument("--report", type=Path, default=Path("results/val_split_report.json"))
    p.add_argument("--val-fraction", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=42, help="Matches configs/data.yaml split.seed.")
    args = p.parse_args()

    cfg = yaml.safe_load(args.data_config.read_text())

    print(f"Reading {args.train_pool} ...")
    df = pd.read_parquet(args.train_pool)
    n = len(df)
    print(f"  {n:,} rows")

    feature_cols = derive_feature_cols(df, cfg)
    print(f"  derived {len(feature_cols)} feature columns")
    if len(feature_cols) != EXPECTED_N_FEATURES:
        raise SystemExit(
            f"\nExpected {EXPECTED_N_FEATURES} features, derived {len(feature_cols)}.\n"
            f"The schema has changed since Chat 02. Resolve that before splitting -- "
            f"a silent feature-count change invalidates the partitions too.\n"
            f"Derived: {feature_cols}"
        )

    print("  hashing feature vectors (this is the group key) ...")
    groups = pd.util.hash_pandas_object(df[feature_cols], index=False).to_numpy()
    n_groups = len(np.unique(groups))
    print(f"  {n_groups:,} distinct feature vectors across {n:,} rows")

    n_splits = int(round(1.0 / args.val_fraction))
    print(f"  StratifiedGroupKFold(n_splits={n_splits}, seed={args.seed}) -> 1 fold as val")

    y = df["family"].to_numpy()
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed)
    _, val_idx = next(sgkf.split(np.zeros(n), y, groups))

    mask = np.zeros(n, dtype=bool)
    mask[val_idx] = True

    # --- guarantee 1: no group spans the boundary -------------------------------
    overlap = np.intersect1d(np.unique(groups[mask]), np.unique(groups[~mask]))
    if overlap.size:
        raise SystemExit(
            f"LEAKAGE: {overlap.size:,} feature vector(s) appear in BOTH train and val. "
            f"Do not proceed -- val macro-F1 would be leakage-inflated and early "
            f"stopping would fire late."
        )
    print("  verified: no feature vector appears in both train and val")

    # --- guarantee 2: no headline family starved on either side -----------------
    trn_counts = df.loc[~mask, "family"].value_counts()
    val_counts = df.loc[mask, "family"].value_counts()
    starved = [
        f for f in HEADLINE_FAMILIES
        if trn_counts.get(f, 0) == 0 or val_counts.get(f, 0) == 0
    ]
    if starved:
        raise SystemExit(
            f"STARVED HEADLINE FAMILIES: {starved}\n"
            f"Group-aware splitting put an entire family on one side (families.py "
            f"lines 140-144 flags this risk; it is sharper at {100/n_splits:.0f}% than at 25%).\n"
            f"Either the family has too few distinct feature vectors to split, or the "
            f"val fraction is too small. Do not proceed -- retry with a different seed "
            f"or a larger --val-fraction, and record which was used."
        )
    print("  verified: every headline family present in both train and val")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"is_val": mask}).to_parquet(args.out, index=False)
    digest = hashlib.sha256(mask.tobytes()).hexdigest()

    print(f"\n  train {(~mask).sum():>10,}   val {mask.sum():>10,}")
    print(f"\n  {'family':<14}{'train':>12}{'val':>10}")
    for fam in sorted(set(trn_counts.index) | set(val_counts.index)):
        flag = "" if fam in HEADLINE_FAMILIES else "   (below floor)"
        print(f"  {fam:<14}{trn_counts.get(fam, 0):>12,}{val_counts.get(fam, 0):>10,}{flag}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({
        "n_rows": int(n),
        "n_train": int((~mask).sum()),
        "n_val": int(mask.sum()),
        "seed": args.seed,
        "n_splits": n_splits,
        "n_features": len(feature_cols),
        "n_distinct_feature_vectors": int(n_groups),
        "group_key": "pd.util.hash_pandas_object(df[feature_cols], index=False)",
        "sha256_mask": digest,
        "train_family_counts": {str(k): int(v) for k, v in trn_counts.items()},
        "val_family_counts": {str(k): int(v) for k, v in val_counts.items()},
    }, indent=2))

    print(f"\n  SHA256(mask): {digest}")
    print(f"  Written: {args.out}")
    print(f"  Written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
