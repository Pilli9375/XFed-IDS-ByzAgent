"""Pre-check C v2: aggregate the 9 label_distribution_*.csv files directly.
No parquet reads needed - these CSVs are per-silo per-family counts from the
Chat 02 pipeline. Run from project root: python tools/precheck_C.py
"""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

PART_DIR = Path("data/processed/partitions")
OUT = Path("results/inspection/silo_sizes.csv")

RE = re.compile(r"label_distribution_a([\d.]+)_s(\d+)\.csv")

def main():
    files = sorted(PART_DIR.glob("label_distribution_*.csv"))
    if not files:
        print(f"NO FILES FOUND under {PART_DIR.resolve()}")
        return 1

    rows = []
    for f in files:
        m = RE.match(f.name)
        if not m:
            print(f"  !! unparsed filename: {f.name}")
            continue
        alpha, seed = m.group(1), m.group(2)
        df = pd.read_csv(f)
        family_cols = [c for c in df.columns if c != "silo"]
        for _, r in df.iterrows():
            silo = int(r["silo"])
            for fam in family_cols:
                n = int(r[fam])
                if n > 0:
                    rows.append({"alpha": alpha, "seed": seed, "silo": silo,
                                 "family": fam, "n": n})

    long_df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(OUT, index=False)

    print("=" * 70)
    print("PER-SILO TOTAL SIZES (all 90 = 10 silos x 3 alpha x 3 seed)")
    print("=" * 70)
    tot = long_df.groupby(["alpha", "seed", "silo"])["n"].sum().reset_index()
    tot = tot.rename(columns={"n": "total_rows"})
    print(tot.pivot_table(index="silo", columns=["alpha", "seed"],
                          values="total_rows", fill_value=0).to_string())

    print("\n" + "=" * 70)
    print("SORTED SILO SIZES (all 90) - looking for a natural gap")
    print("=" * 70)
    st = tot.sort_values("total_rows")
    print(st.to_string(index=False))

    print("\n" + "=" * 70)
    print("GAP ANALYSIS: consecutive ratio in sorted sizes")
    print("=" * 70)
    sizes = st["total_rows"].to_numpy()
    for i in range(1, len(sizes)):
        if sizes[i-1] > 0:
            ratio = sizes[i] / sizes[i-1]
            if ratio > 1.5:  # flag notable jumps
                print(f"  jump at rank {i}: {sizes[i-1]} -> {sizes[i]}  (x{ratio:.2f})")

    print("\n" + "=" * 70)
    print("PER-FAMILY NONZERO COVERAGE BY SILO, per (alpha, seed)")
    print("(cell = row count if >0, blank if silo has ZERO of that family)")
    print("=" * 70)
    for (a, s), g in long_df.groupby(["alpha", "seed"]):
        print(f"\n--- alpha={a}  seed={s} ---")
        piv = g.pivot_table(index="silo", columns="family", values="n", fill_value=0)
        print(piv.to_string())

    print("\n" + "=" * 70)
    print("ELIGIBILITY CANDIDATES: silos below various size thresholds, per alpha")
    print("=" * 70)
    for thresh in [100, 200, 400, 1000]:
        below = tot[tot["total_rows"] < thresh]
        print(f"\nThreshold={thresh} rows:")
        summary = below.groupby("alpha").size().reindex(["0.1", "0.5", "5.0"], fill_value=0)
        print(summary.to_string())

    print(f"\nWritten long-format data: {OUT}")
    return 0

if __name__ == "__main__":
    exit(main())
