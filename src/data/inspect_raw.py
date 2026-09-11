"""
XFed-IDS -- Phase 1 raw data inspection.

Diagnostic only. This script DECIDES NOTHING and WRITES NO PROCESSED DATA.
Its job is to replace assumptions with measured numbers so that the
preprocessing decisions (Attempted handling, dedup, 14->8 family mapping,
feature list) can be made from evidence.

Dataset: Distrinet-CIC-IDS2017, Kaggle (dhoogla), versions/4
         = Liu et al. 2022 (IEEE CNS) update, extending Engelen et al. 2021 (WTMC).

Output: results/inspection/REPORT.md  (+ supporting CSVs)

Note on config: experiment hyperparameters live in YAML per project standards.
This is a one-off diagnostic, not an experiment, so paths sit at the top of the
file. Nothing here feeds a reported result.

Usage:
    python src/data/inspect_raw.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

DATASET_DIR = Path(r"C:\Pilli\Capstone\Dataset")
OUT_DIR = Path(r"C:\Pilli\Capstone\xfed-ids\results\inspection")

# Columns flagged as identifiers in the header inspection. Matched
# case-insensitively after stripping whitespace.
IDENTIFIER_COLS = {
    "id",
    "flow id",
    "src ip",
    "src port",
    "dst ip",
    "dst port",
    "timestamp",
}

# Columns whose values should never be negative if the data is sound.
# Matched as substrings, lowercased. Used only to flag corruption.
NONNEGATIVE_HINTS = ("packet", "byte", "duration", "length", "count", "flag")

# A column is "near-constant" if its most common value covers at least this
# fraction of rows. Reported, not acted on.
NEAR_CONSTANT_THRESHOLD = 0.999

SAMPLE_ROWS_FOR_HASH = 5  # rows shown per preview table


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def norm(col: str) -> str:
    """Normalise a column name for matching: strip whitespace, lowercase."""
    return col.strip().lower()


def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Checksum a file. Goes in the manifest later; recorded now as a baseline."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def md_table(df: pd.DataFrame, index: bool = True) -> str:
    """Render a DataFrame as a markdown table, or a note if empty."""
    if df.empty:
        return "_(none)_\n"
    return df.to_markdown(index=index) + "\n"


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_headers(paths: list[Path]) -> tuple[list[str], list[str]]:
    """
    Read only the header row of each CSV.

    Answers: are the five files column-identical (safe to concat), and what are
    the EXACT column names including any leading/trailing whitespace? Stray
    whitespace in CICIDS column names is a classic source of silent KeyErrors.

    Returns (reference column list, report lines).
    """
    lines: list[str] = ["## 1. Headers\n"]
    headers: dict[str, list[str]] = {}

    for p in paths:
        cols = pd.read_csv(p, nrows=0).columns.tolist()
        headers[p.name] = cols

    ref_name, ref_cols = next(iter(headers.items()))
    lines.append(f"Reference file: `{ref_name}` -- **{len(ref_cols)} columns**\n")

    mismatches = []
    for name, cols in headers.items():
        if cols != ref_cols:
            only_here = sorted(set(cols) - set(ref_cols))
            missing = sorted(set(ref_cols) - set(cols))
            order_only = not only_here and not missing
            mismatches.append(
                {
                    "file": name,
                    "n_cols": len(cols),
                    "order_differs_only": order_only,
                    "extra": ", ".join(only_here) or "-",
                    "missing": ", ".join(missing) or "-",
                }
            )

    if mismatches:
        lines.append(
            "**Column sets are NOT identical across files.** "
            "Do not concat blindly -- align columns first.\n"
        )
        lines.append(md_table(pd.DataFrame(mismatches), index=False))
    else:
        lines.append("All five files are column-identical. Safe to concat.\n")

    # repr() so that whitespace is visible rather than invisible.
    whitespace_cols = [c for c in ref_cols if c != c.strip()]
    lines.append(f"\nColumns with leading/trailing whitespace: **{len(whitespace_cols)}**\n")
    if whitespace_cols:
        lines.append("```\n" + "\n".join(repr(c) for c in whitespace_cols) + "\n```\n")

    lines.append("\n<details><summary>Full column list (repr)</summary>\n\n```\n")
    lines.extend(f"{i:>3}  {c!r}\n" for i, c in enumerate(ref_cols))
    lines.append("```\n</details>\n")

    return ref_cols, lines


def classify_columns(cols: list[str]) -> dict[str, list[str]]:
    """
    Split columns into identifiers / label-like / attempted-like / candidate features.

    Detection is by substring rather than exact name so that the script does not
    depend on assumed spelling of the label columns.
    """
    ids, labels, attempted, features = [], [], [], []
    for c in cols:
        n = norm(c)
        if n in IDENTIFIER_COLS:
            ids.append(c)
        elif "attempt" in n:
            attempted.append(c)
        elif "label" in n:
            labels.append(c)
        else:
            features.append(c)
    return {
        "identifier": ids,
        "label": labels,
        "attempted": attempted,
        "feature": features,
    }


def label_audit(
    paths: list[Path], label_col: str, attempted_col: str | None
) -> tuple[pd.DataFrame, list[str]]:
    """
    Load ONLY the label columns across all files. Cheap -- seconds, not minutes.

    Answers three things at once:
      - the exact raw label strings and their counts (input to the 14->8 mapping)
      - whether `Attempted Category` is boolean or multi-valued
      - whether Attempted is non-null on Benign rows (it should not be)
    """
    lines: list[str] = ["\n## 2. Labels and Attempted Category\n"]
    usecols = [label_col] + ([attempted_col] if attempted_col else [])

    frames = []
    per_file_counts = {}
    for p in paths:
        df = pd.read_csv(p, usecols=usecols, low_memory=False)
        per_file_counts[p.name] = df[label_col].value_counts()
        frames.append(df)
    labels_df = pd.concat(frames, ignore_index=True)

    lines.append(f"Total rows across all five files: **{len(labels_df):,}**\n")

    counts = labels_df[label_col].value_counts(dropna=False)
    counts_tbl = counts.rename("flows").to_frame()
    counts_tbl["pct"] = (counts_tbl["flows"] / len(labels_df) * 100).round(4)
    lines.append("\n### 2a. Raw label counts (pooled)\n")
    lines.append(md_table(counts_tbl))

    # repr() again -- label strings carry whitespace surprisingly often.
    lines.append("\nExact label strings (repr):\n```\n")
    lines.extend(f"{v!r}\n" for v in counts.index.tolist())
    lines.append("```\n")

    lines.append("\n### 2b. Labels present per day-file\n")
    lines.append(
        "_Relevant later: this dataset is already non-IID by day before "
        "Dirichlet partitioning touches it._\n\n"
    )
    per_file_tbl = pd.DataFrame(per_file_counts).fillna(0).astype(int)
    lines.append(md_table(per_file_tbl))

    if attempted_col:
        lines.append("\n### 2c. Attempted Category value counts\n")
        att_counts = labels_df[attempted_col].value_counts(dropna=False)
        lines.append(md_table(att_counts.rename("flows").to_frame()))
        lines.append(
            f"\nDistinct values (incl. null): **{labels_df[attempted_col].nunique(dropna=False)}** "
            "-- if this is >2, the field is a reason code, not a boolean flag.\n"
        )

        lines.append("\n### 2d. Label x Attempted Category crosstab\n")
        crosstab = pd.crosstab(
            labels_df[label_col],
            labels_df[attempted_col].fillna("<NULL>"),
            dropna=False,
        )
        lines.append(md_table(crosstab))
        crosstab.to_csv(OUT_DIR / "label_attempted_crosstab.csv")
    else:
        lines.append("\n**No Attempted-like column detected.** Check the header list above.\n")

    counts_tbl.to_csv(OUT_DIR / "raw_label_counts.csv")
    per_file_tbl.to_csv(OUT_DIR / "labels_per_file.csv")
    return labels_df, lines


def load_full(paths: list[Path], cols: list[str]) -> pd.DataFrame:
    """
    Load all files fully, downcasting floats to float32 as we go.

    float64 across ~2M rows x ~82 numeric columns is wasteful; float32 halves it
    and is more than enough precision for these features. Downcasting per file
    keeps peak memory near one file's footprint plus the growing concat.
    """
    frames = []
    for p in paths:
        df = pd.read_csv(p, low_memory=False)
        for c in df.select_dtypes(include=["float64"]).columns:
            df[c] = df[c].astype(np.float32)
        for c in df.select_dtypes(include=["int64"]).columns:
            df[c] = pd.to_numeric(df[c], downcast="integer")
        df["__source_file"] = p.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def dtype_audit(df: pd.DataFrame, feature_cols: list[str]) -> list[str]:
    """
    Flag feature columns that did NOT parse as numeric.

    A numeric column silently loaded as `object` -- usually caused by a stray
    string such as "Infinity" or an empty field -- will corrupt scaling
    downstream while looking fine. This is the single highest-value check here.
    """
    lines = ["\n## 3. Dtypes\n"]
    present = [c for c in feature_cols if c in df.columns]
    dtypes = df[present].dtypes

    non_numeric = dtypes[~dtypes.apply(pd.api.types.is_numeric_dtype)]
    lines.append(f"Candidate feature columns: **{len(present)}**\n")
    lines.append(f"Non-numeric feature columns: **{len(non_numeric)}**\n")

    if len(non_numeric):
        lines.append(
            "\n**These parsed as non-numeric. Investigate before scaling.**\n\n"
        )
        rows = []
        for c in non_numeric.index:
            offenders = (
                df[c][pd.to_numeric(df[c], errors="coerce").isna() & df[c].notna()]
                .astype(str)
                .value_counts()
                .head(SAMPLE_ROWS_FOR_HASH)
            )
            rows.append(
                {
                    "column": c,
                    "dtype": str(non_numeric[c]),
                    "sample_offending_values": "; ".join(
                        f"{v!r} x{n}" for v, n in offenders.items()
                    )
                    or "-",
                }
            )
        lines.append(md_table(pd.DataFrame(rows), index=False))
    else:
        lines.append("\nAll candidate features parsed as numeric.\n")

    return lines


def numeric_health(df: pd.DataFrame, feature_cols: list[str]) -> list[str]:
    """
    Count Inf / -Inf / NaN per numeric feature, plus zero-duration flows.

    Flow Bytes/s and Flow Packets/s are the classic offenders: they divide by
    flow duration, so duration == 0 produces Inf. Handle explicitly rather than
    dropping silently -- how many rows are affected determines whether dropping
    them is cheap or destroys a rare class.
    """
    lines = ["\n## 4. Inf / NaN / zero-duration\n"]
    numeric = [
        c
        for c in feature_cols
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]

    rows = []
    for c in numeric:
        col = df[c]
        n_pinf = int((np.isinf(col) & (col > 0)).sum()) if col.dtype.kind == "f" else 0
        n_ninf = int((np.isinf(col) & (col < 0)).sum()) if col.dtype.kind == "f" else 0
        n_nan = int(col.isna().sum())
        n_neg = int((col < 0).sum())
        if n_pinf or n_ninf or n_nan or n_neg:
            rows.append(
                {
                    "column": c,
                    "+Inf": n_pinf,
                    "-Inf": n_ninf,
                    "NaN": n_nan,
                    "negative": n_neg,
                    "suspicious_negative": any(
                        h in norm(c) for h in NONNEGATIVE_HINTS
                    )
                    and n_neg > 0,
                }
            )

    health = pd.DataFrame(rows)
    if health.empty:
        lines.append("No Inf, NaN, or negative values in any numeric feature.\n")
    else:
        lines.append(
            f"**{len(health)} of {len(numeric)}** numeric features have at least one "
            "Inf, NaN, or negative value.\n\n"
        )
        lines.append(md_table(health.sort_values("NaN", ascending=False), index=False))
        health.to_csv(OUT_DIR / "numeric_health.csv", index=False)

    # Rows affected -- more decision-relevant than columns affected.
    num_block = df[numeric]
    bad_mask = num_block.isna().any(axis=1) | np.isinf(
        num_block.select_dtypes(include=[np.floating])
    ).any(axis=1)
    lines.append(
        f"\nRows with at least one Inf or NaN: **{int(bad_mask.sum()):,}** "
        f"({bad_mask.mean() * 100:.4f}%)\n"
    )

    dur_cols = [c for c in numeric if "duration" in norm(c)]
    for c in dur_cols:
        n_zero = int((df[c] == 0).sum())
        lines.append(f"\n`{c}` == 0: **{n_zero:,}** rows (direct cause of rate-column Inf)\n")

    return lines, bad_mask


def duplicate_audit(
    df: pd.DataFrame, feature_cols: list[str], label_col: str
) -> list[str]:
    """
    Exact duplicates and conflicting-label duplicates.

    The Distrinet changelog's "0 duplicate records" claim is documented for the
    parquet cleaning step (V2/V5), NOT the raw V4 CSVs. Verify, do not inherit.

    Two distinct problems:
      - exact dupes (same features AND same label) inflate a class and, if split
        across train/test or across silos, are direct leakage
      - feature-identical rows with DIFFERENT labels are a labelling-consistency
        problem: no model can separate them, and they put a hard ceiling on F1
    """
    lines = ["\n## 5. Duplicates\n"]
    present = [c for c in feature_cols if c in df.columns]

    n_exact = int(df.duplicated(subset=present + [label_col]).sum())
    n_feat = int(df.duplicated(subset=present).sum())
    n_conflict = n_feat - n_exact

    lines.append(f"- Exact duplicate rows (features + label): **{n_exact:,}** "
                 f"({n_exact / len(df) * 100:.4f}%)\n")
    lines.append(f"- Feature-identical rows (label ignored): **{n_feat:,}**\n")
    lines.append(f"- Implied feature-identical but label-CONFLICTING: **{n_conflict:,}**\n")

    if n_exact:
        dup_mask = df.duplicated(subset=present + [label_col], keep=False)
        by_label = df.loc[dup_mask, label_col].value_counts()
        lines.append("\n### 5a. Which labels carry duplicate mass\n")
        lines.append(md_table(by_label.rename("rows_in_dup_groups").to_frame()))
        by_label.to_csv(OUT_DIR / "duplicates_by_label.csv")

        cross_file = (
            df.loc[dup_mask]
            .groupby(present + [label_col], observed=True)["__source_file"]
            .nunique()
        )
        n_cross = int((cross_file > 1).sum())
        lines.append(
            f"\nDuplicate groups spanning MORE THAN ONE day-file: **{n_cross:,}**\n"
            "_Cross-file duplicates suggest capture overlap, not just repeated traffic._\n"
        )

    if n_conflict:
        lines.append(
            "\n**Conflicting labels exist.** These cap achievable macro-F1 and need an "
            "explicit resolution rule (drop all, majority vote, or keep-first) recorded "
            "in data/README.md.\n"
        )

    return lines


def variance_audit(df: pd.DataFrame, feature_cols: list[str]) -> list[str]:
    """
    Constant and near-constant columns.

    Dropping these is a variance-based schema decision, not feature selection --
    it carries no information and needs no held-out data, so it is leakage-safe.
    Likely explains part of the gap between your 82 candidates and the "78
    features" figure commonly quoted in the CICIDS literature.
    """
    lines = ["\n## 6. Constant / near-constant features\n"]
    present = [
        c
        for c in feature_cols
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]

    rows = []
    n = len(df)
    for c in present:
        vc = df[c].value_counts(dropna=False)
        top_frac = vc.iloc[0] / n if len(vc) else 1.0
        if df[c].nunique(dropna=False) <= 1 or top_frac >= NEAR_CONSTANT_THRESHOLD:
            rows.append(
                {
                    "column": c,
                    "n_unique": int(df[c].nunique(dropna=False)),
                    "top_value": vc.index[0] if len(vc) else None,
                    "top_value_frac": round(float(top_frac), 6),
                    "constant": bool(df[c].nunique(dropna=False) <= 1),
                }
            )

    tbl = pd.DataFrame(rows)
    if tbl.empty:
        lines.append("No constant or near-constant features found.\n")
    else:
        n_const = int(tbl["constant"].sum())
        lines.append(
            f"**{n_const}** strictly constant, **{len(tbl) - n_const}** near-constant "
            f"(top value covers >= {NEAR_CONSTANT_THRESHOLD:.1%} of rows).\n\n"
        )
        lines.append(md_table(tbl.sort_values("top_value_frac", ascending=False), index=False))
        tbl.to_csv(OUT_DIR / "constant_features.csv", index=False)

    lines.append(
        f"\nCandidate features surviving this check: "
        f"**{len(present) - len(tbl)}** of {len(present)}\n"
    )
    return lines


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    if not DATASET_DIR.exists():
        print(f"Dataset directory not found: {DATASET_DIR}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    paths = sorted(DATASET_DIR.glob("*.csv"))
    if not paths:
        print(f"No CSVs found in {DATASET_DIR}", file=sys.stderr)
        return 1

    report: list[str] = [
        "# XFed-IDS -- Raw Data Inspection Report\n",
        "Dataset: Distrinet-CIC-IDS2017 v4 (Liu et al. 2022, IEEE CNS; "
        "extends Engelen et al. 2021, WTMC)\n",
        "\n## 0. Files\n",
    ]

    file_rows = []
    for p in paths:
        print(f"[hash] {p.name}")
        file_rows.append(
            {
                "file": p.name,
                "size_MB": round(p.stat().st_size / 1e6, 1),
                "sha256": file_sha256(p)[:16] + "...",
            }
        )
    report.append(md_table(pd.DataFrame(file_rows), index=False))
    pd.DataFrame(file_rows).to_csv(OUT_DIR / "file_checksums.csv", index=False)

    print("[1/6] headers")
    ref_cols, lines = check_headers(paths)
    report.extend(lines)

    groups = classify_columns(ref_cols)
    report.append("\n### Column classification\n")
    report.append(
        md_table(
            pd.DataFrame(
                [{"group": k, "n": len(v), "columns": ", ".join(v) or "-"}
                 for k, v in groups.items()]
            ),
            index=False,
        )
    )

    if not groups["label"]:
        print("No label-like column detected. Check header output.", file=sys.stderr)
        (OUT_DIR / "REPORT.md").write_text("".join(report), encoding="utf-8")
        return 1

    label_col = groups["label"][0]
    attempted_col = groups["attempted"][0] if groups["attempted"] else None
    feature_cols = groups["feature"]

    print("[2/6] labels (cheap, label columns only)")
    _, lines = label_audit(paths, label_col, attempted_col)
    report.extend(lines)

    print("[3/6] full load (float32 downcast)")
    df = load_full(paths, ref_cols)
    mem_gb = df.memory_usage(deep=True).sum() / 1e9
    report.append(f"\n_Full frame in memory: {mem_gb:.2f} GB, {len(df):,} rows._\n")
    print(f"        loaded {len(df):,} rows, {mem_gb:.2f} GB")

    print("[4/6] dtypes")
    report.extend(dtype_audit(df, feature_cols))

    print("[5/6] numeric health")
    lines, _ = numeric_health(df, feature_cols)
    report.extend(lines)

    print("[6/6] duplicates + variance")
    numeric_features = [
        c
        for c in feature_cols
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]
    report.extend(duplicate_audit(df, numeric_features, label_col))
    report.extend(variance_audit(df, feature_cols))

    report.append(
        "\n---\n\n**Nothing was decided or written by this script.** "
        "Attempted handling, dedup rule, 14->8 mapping, floor exclusions, and the "
        "final feature list are all still open.\n"
    )

    out = OUT_DIR / "REPORT.md"
    out.write_text("".join(report), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
