"""Per-silo agreement breakdown -- the one cut of agreement_metrics.csv we
never actually printed. No new computation, just a different groupby on
data already on disk.

Run from project root: python tools/per_silo_breakdown.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

AGREEMENT_PATH = Path("results/inspection/agreement_metrics.csv")

def main() -> int:
    df = pd.read_csv(AGREEMENT_PATH)
    elig = df[df.family_eligible]

    print("=" * 70)
    print("PER-SILO MEDIAN AGREEMENT (family_eligible rows only)")
    print("=" * 70)
    per_silo = elig.groupby(["alpha", "seed", "silo"])[
        ["jaccard_at_5", "jaccard_at_10", "jaccard_at_20", "kendall_weighted_tau"]
    ].median()
    per_silo["n_samples"] = elig.groupby(["alpha", "seed", "silo"]).size()
    print(per_silo.to_string())

    print("\n" + "=" * 70)
    print("OUTLIER CHECK: silos whose jaccard_at_10 deviates >0.15 from their alpha's median")
    print("=" * 70)
    alpha_medians = elig.groupby("alpha")["jaccard_at_10"].median()
    per_silo_flat = elig.groupby(["alpha", "seed", "silo"])["jaccard_at_10"].median().reset_index()
    per_silo_flat["alpha_median"] = per_silo_flat["alpha"].map(alpha_medians)
    per_silo_flat["deviation"] = per_silo_flat["jaccard_at_10"] - per_silo_flat["alpha_median"]
    outliers = per_silo_flat[per_silo_flat["deviation"].abs() > 0.15].sort_values("deviation")
    if outliers.empty:
        print("None -- every silo's median sits within 0.15 of its alpha's overall median.")
    else:
        print(outliers.to_string(index=False))

    out_path = Path("results/inspection/per_silo_agreement.csv")
    per_silo.to_csv(out_path)
    print(f"\nWritten: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
