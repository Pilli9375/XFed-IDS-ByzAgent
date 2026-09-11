"""
XFed-IDS -- Phase 3, step 1: raw -> clean.

Applies exactly the decisions recorded in configs/data.yaml. Every removal is
counted and logged -- nothing is dropped silently.

ORDER MATTERS HERE. Family mapping happens FIRST, then Inf/NaN removal, then
family-conflict removal, then cross-file deduplication. Conflicts and duplicates
are evaluated against the FAMILY, not the raw label, because the family is what
the model is trained to predict. Two raw labels mapping to the same family are
not in conflict with each other. (Chat 02 finding: doing this in the wrong
order discarded 58,307 perfectly learnable PortScan rows, because
"Infiltration - Portscan" and "Portscan" both map to PortScan.)

What this script does NOT do: floor exclusion, train/test split, Dirichlet
partitioning, or scaling. Those live in families.py and partition.py.

Input:  raw CSVs at paths.raw_dir (config)
Output: <processed_dir>/clean.parquet   (includes a 'family' column)
        <processed_dir>/clean_log.json  (row counts + conflict breakdown)

Usage:
    python src/data/clean.py [--config configs/data.yaml]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from mapping import assign_families


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_raw(raw_dir: Path) -> pd.DataFrame:
    """Load all CSVs, tag source file, downcast floats/ints as we go."""
    paths = sorted(raw_dir.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSVs found in {raw_dir}")

    frames = []
    for p in paths:
        print(f"  loading {p.name}")
        df = pd.read_csv(p, low_memory=False)
        df.columns = [c.strip() for c in df.columns]  # defensive; none found in Phase 1
        for c in df.select_dtypes(include=["float64"]).columns:
            df[c] = df[c].astype(np.float32)
        for c in df.select_dtypes(include=["int64"]).columns:
            df[c] = pd.to_numeric(df[c], downcast="integer")
        df["__source_file"] = p.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def drop_inf_nan(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, int]:
    numeric = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    block = df[numeric]
    bad = block.isna().any(axis=1) | np.isinf(
        block.select_dtypes(include=[np.floating])
    ).any(axis=1)
    n = int(bad.sum())
    return df.loc[~bad].copy(), n


def drop_family_conflicts(
    df: pd.DataFrame, feature_cols: list[str], family_col: str = "family"
) -> tuple[pd.DataFrame, int, dict]:
    """
    Drop entire groups of feature-identical rows carrying more than one FAMILY.

    No classifier can separate identical inputs mapped to different targets, so
    keeping any member injects label noise and imposes a ceiling on macro-F1.

    Evaluated on family, not raw label -- see module docstring.

    Also reports which family combinations conflicted and how many rows each
    cost. Required for data/README.md: dropping a material fraction of the data
    without being able to say what it was is not defensible in review.
    """
    n_fams = df.groupby(feature_cols, sort=False)[family_col].transform("nunique")
    conflict = n_fams > 1
    n = int(conflict.sum())

    detail: dict = {}
    if n:
        sub = df.loc[conflict]
        combos = sub.groupby(feature_cols, sort=False)[family_col].agg(
            lambda s: " | ".join(sorted(s.unique()))
        )
        sizes = sub.groupby(feature_cols, sort=False)[family_col].size()
        summary = (
            pd.DataFrame({"combo": combos, "rows": sizes})
            .groupby("combo")["rows"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "rows_dropped", "count": "n_groups"})
            .sort_values("rows_dropped", ascending=False)
        )
        detail = {
            "by_family_combination": summary.to_dict(orient="index"),
            "rows_dropped_per_family": sub[family_col].value_counts().to_dict(),
        }
        print("\n        conflicting FAMILY combinations:")
        print(summary.head(15).to_string())

    return df.loc[~conflict].copy(), n, detail


def dedup_cross_file_only(
    df: pd.DataFrame, feature_cols: list[str], label_col: str
) -> tuple[pd.DataFrame, int]:
    """
    Drop duplicate rows (features + RAW LABEL) ONLY within groups spanning more
    than one source file.

    Note the key: raw label, NOT family -- deliberately different from
    drop_family_conflicts above. The two filters answer different questions:

      - conflicts ask "is this learnable?"    -> keyed on FAMILY (the target)
      - duplicates ask "is this the same
        captured event, recorded twice?"      -> keyed on RAW LABEL (provenance)

    Capture overlap means identical traffic appearing in two day-files; the
    labelling pipeline would assign it the same raw label both times. Two rows
    with DIFFERENT raw labels on different days are different events that merely
    collapse to identical features once identifier columns are dropped -- e.g.
    Thursday's internal "Infiltration - Portscan" and Friday's external
    "Portscan". Keying this on family would wrongly delete 58k such rows.

    Same-file duplicates are left untouched -- see configs/data.yaml for why
    (structural duplication in scan and bot traffic once ports/IPs are dropped).
    Residual train/test leakage from those is handled by group-aware splitting
    in families.py, not by deletion.
    """
    key = feature_cols + [label_col]
    n_files = df.groupby(key, sort=False)["__source_file"].transform("nunique")
    cross_file = n_files > 1

    subset = df.loc[cross_file]
    redundant = subset.duplicated(subset=key, keep="first")
    drop_index = subset.index[redundant]

    return df.drop(index=drop_index).copy(), len(drop_index)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    raw_dir = Path(cfg["paths"]["raw_dir"])
    out_dir = Path(cfg["paths"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    label_col = cfg["schema"]["label_col"]
    attempted_col = cfg["schema"]["attempted_col"]
    id_cols = set(cfg["schema"]["identifier_cols"])
    suffix = cfg["attempted_handling"]["suffix"]

    print("[1/5] loading raw CSVs")
    df = load_raw(raw_dir)
    n_start = len(df)
    print(f"        {n_start:,} rows loaded")

    feature_cols = [
        c for c in df.columns
        if c not in id_cols and c not in (label_col, attempted_col, "__source_file")
    ]
    print(f"        {len(feature_cols)} candidate feature columns")

    log = {"n_start": n_start}

    print("[2/5] mapping raw labels -> family")
    df["is_attempted"] = df[label_col].str.endswith(suffix)
    df["family"] = assign_families(df, label_col, cfg["family_map"])
    log["family_counts_pre_clean"] = df["family"].value_counts().to_dict()
    print(f"        {df['family'].nunique()} families assigned")

    if cfg["cleaning"]["drop_inf_nan_rows"]:
        print("[3/5] dropping Inf/NaN rows")
        df, n = drop_inf_nan(df, feature_cols)
        log["dropped_inf_nan"] = n
        print(f"        dropped {n:,} rows")

    if cfg["cleaning"]["drop_label_conflicts"]:
        print("[4/5] dropping family-conflicting duplicate groups")
        df, n, detail = drop_family_conflicts(df, feature_cols)
        log["dropped_family_conflicts"] = n
        log["family_conflict_detail"] = detail
        print(f"        dropped {n:,} rows")

    if cfg["cleaning"]["dedup_cross_file_only"]:
        print("[5/5] deduping cross-file-only groups")
        df, n = dedup_cross_file_only(df, feature_cols, label_col)
        log["dropped_cross_file_dupes"] = n
        print(f"        dropped {n:,} rows")

    # Leakage exposure: how many rows still share a feature vector with at
    # least one other row. These are NOT deleted -- they are real, distinct
    # events that collapse to identical features once identifiers are dropped.
    # families.py handles them with group-aware splitting so that no feature
    # vector can appear on both sides of the train/test boundary.
    dup_mask = df.duplicated(subset=feature_cols, keep=False)
    log["rows_sharing_a_feature_vector"] = int(dup_mask.sum())
    log["rows_sharing_a_feature_vector_by_family"] = (
        df.loc[dup_mask, "family"].value_counts().to_dict()
    )
    print(
        f"\n        leakage exposure: {int(dup_mask.sum()):,} rows share a feature "
        f"vector with another row"
    )
    print("        (handled by group-aware splitting in families.py, not deletion)")

    log["n_end"] = len(df)
    log["n_dropped_total"] = n_start - len(df)
    log["pct_dropped"] = round((n_start - len(df)) / n_start * 100, 4)
    log["family_counts_post_clean"] = df["family"].value_counts().to_dict()

    out_parquet = out_dir / "clean.parquet"
    df.to_parquet(out_parquet, index=False)
    (out_dir / "clean_log.json").write_text(json.dumps(log, indent=2))

    print(f"\n{len(df):,} rows remain ({log['pct_dropped']}% dropped)")
    print(f"Wrote {out_parquet}")
    print(f"Wrote {out_dir / 'clean_log.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
