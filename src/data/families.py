"""
XFed-IDS -- Phase 3, step 2: floor flagging + global stratified split.

Reads data/processed/clean.parquet, which already carries a 'family' column
(assigned in clean.py -- see that module's docstring for why the mapping has to
happen before conflict/duplicate removal).

This script flags families under family_floor, then performs ONE global
family-stratified train/test split. This is the split that both the Chat 03
centralized baseline and the federated global model get evaluated against, so
the comparison is apples-to-apples. Per-silo local test shards come from
applying the SAME Dirichlet assignment to this test set in partition.py, not
from a second independent split.

Output:
    <processed_dir>/train_pool.parquet
    <processed_dir>/test_global.parquet
    <processed_dir>/family_distribution.csv
    <processed_dir>/family_log.json

Usage:
    python src/data/families.py [--config configs/data.yaml]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import StratifiedGroupKFold


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    out_dir = Path(cfg["paths"]["processed_dir"])
    floor = cfg["family_floor"]
    seed = cfg["split"]["seed"]
    test_size = cfg["split"]["test_size"]

    print("[1/4] loading clean.parquet")
    df = pd.read_parquet(out_dir / "clean.parquet")
    print(f"        {len(df):,} rows")

    if "family" not in df.columns:
        raise ValueError(
            "clean.parquet has no 'family' column. Re-run clean.py -- family "
            "assignment moved there so that conflict detection operates on the "
            "family rather than the raw label."
        )

    print("[2/4] flagging families below floor")
    counts = df["family"].value_counts()
    below_floor = set(counts[counts < floor].index)
    df["below_floor"] = df["family"].isin(below_floor)

    dist = counts.rename("flows").to_frame()
    dist["below_floor"] = dist.index.isin(below_floor)
    dist.to_csv(out_dir / "family_distribution.csv")
    print(dist.to_string())
    if below_floor:
        print(
            f"\n        below {floor}-flow floor, excluded from headline "
            f"macro-F1: {sorted(below_floor)}"
        )

    too_small = counts[counts < 2]
    if len(too_small):
        raise ValueError(
            f"Families with under 2 members can't be stratified-split: "
            f"{too_small.to_dict()}. Fix the family_map or the upstream "
            f"cleaning rules before continuing -- this would otherwise fail "
            f"inside sklearn with a much less useful error."
        )

    print(f"\n[3/4] group-aware stratified split (test_size={test_size}, seed={seed})")

    # Group = the feature vector itself. Rows that are feature-identical are
    # forced onto the SAME side of the train/test boundary.
    #
    # Why: after cleaning, a large share of scan and bot traffic still shares
    # feature vectors with other rows -- these are genuinely distinct events
    # that collapse together once identifier columns (ports, IPs) are dropped.
    # A plain random split would put copies of the same vector in both train
    # and test, handing the model free correct answers and inflating every
    # reported metric. Deleting them instead would strip most of the mass out
    # of PortScan. Grouping solves the leakage without losing the data.
    feature_cols = [
        c for c in df.columns
        if c not in ("family", "below_floor", "is_attempted", "__source_file")
        and c not in (cfg["schema"]["label_col"], cfg["schema"]["attempted_col"])
        and c not in set(cfg["schema"]["identifier_cols"])
    ]
    groups = pd.util.hash_pandas_object(df[feature_cols], index=False)
    n_groups = groups.nunique()
    print(f"        {n_groups:,} distinct feature vectors across {len(df):,} rows")

    n_splits = int(round(1 / test_size))
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    train_idx, test_idx = next(sgkf.split(df, y=df["family"], groups=groups))
    train_pool = df.iloc[train_idx]
    test_global = df.iloc[test_idx]

    print(
        f"        train_pool: {len(train_pool):,}  test_global: {len(test_global):,} "
        f"({len(test_global) / len(df):.1%})"
    )

    # Verify the guarantee actually holds rather than trusting the library.
    overlap = set(groups.iloc[train_idx]) & set(groups.iloc[test_idx])
    if overlap:
        raise RuntimeError(
            f"{len(overlap):,} feature vectors appear in BOTH train and test. "
            f"The group split did not hold -- do not proceed, results would be "
            f"leakage-inflated."
        )
    print("        verified: no feature vector appears in both train and test")

    print("\n        per-family split balance:")
    balance = pd.DataFrame({
        "train": train_pool["family"].value_counts(),
        "test": test_global["family"].value_counts(),
    }).fillna(0).astype(int)
    balance["test_pct"] = (
        balance["test"] / (balance["train"] + balance["test"]) * 100
    ).round(1)
    print(balance.to_string())

    # Group-aware splitting can starve a family that has few DISTINCT feature
    # vectors: if a family's rows form only one or two groups, they can all land
    # on the same side. Catch it here rather than discovering it as a zero F1
    # in Chat 03.
    starved = balance[(balance["train"] == 0) | (balance["test"] == 0)]
    if len(starved):
        print(
            f"\n        WARNING: {len(starved)} family/families have zero rows on "
            f"one side of the split:\n{starved.to_string()}"
        )
        print(
            "        These families have too few distinct feature vectors to "
            "split. Report this -- do not silently train on it."
        )
    log_starved = starved.index.tolist()

    print("[4/4] writing outputs")
    train_pool.to_parquet(out_dir / "train_pool.parquet", index=False)
    test_global.to_parquet(out_dir / "test_global.parquet", index=False)

    log = {
        "family_counts": counts.to_dict(),
        "below_floor_families": sorted(below_floor),
        "family_floor": floor,
        "n_distinct_feature_vectors": int(n_groups),
        "families_starved_by_group_split": log_starved,
        "per_family_split_balance": balance.to_dict(orient="index"),
        "n_train_pool": len(train_pool),
        "n_test_global": len(test_global),
        "split_seed": seed,
        "test_size": test_size,
    }
    (out_dir / "family_log.json").write_text(json.dumps(log, indent=2))

    print(
        f"\nWrote train_pool.parquet, test_global.parquet, "
        f"family_distribution.csv, family_log.json in {out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
