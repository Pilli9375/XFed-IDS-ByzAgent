"""Chat 04 closeout -- two analyses, both from data already on disk.

1. Bootstrap 95% CIs for the headline comparison (alpha=0.1 federated
   agreement vs the centralized-seed instability floor). Uses a CLUSTER
   bootstrap (by silo, not by row) for the federated side, because rows
   from the same silo share the same model and are not independent --
   a naive row-level bootstrap would understate the true uncertainty.
   The floor gets special treatment: only 3 seeds exist, so the 3
   seed-pairs are NOT independent (each seed appears in 2 pairs) -- this
   is reported honestly rather than bootstrapped as if it were.

2. Within-alpha correlation between silo size and silo-level agreement.
   Valid as a descriptive measure, but it cannot by itself separate
   "heterogeneity causes low agreement" from "small silos just have
   noisier/worse models regardless of alpha": under dirichlet_assign()
   (src/data/partition.py), per-family proportions sum to 1 over silos by
   construction, so silo size is a deterministic output of the same
   label-skew draw that produces heterogeneity, not an independent
   variable to correlate size against. That separation question is
   addressed instead by the size-conditioned (partial-correlation)
   analysis in results/inspection/size_matched_heterogeneity.csv.

Run from project root: python tools/chat04_closeout.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

AGREEMENT_PATH = Path("results/inspection/agreement_metrics.csv")
FLOOR_PATH = Path("results/inspection/centralized_instability_floor.csv")
PER_SILO_PATH = Path("results/inspection/per_silo_agreement.csv")
SIZES_PATH = Path("results/inspection/silo_sizes.csv")

N_BOOT = 10000
RNG_SEED = 0
METRICS = ["jaccard_at_10", "kendall_weighted_tau"]


def cluster_bootstrap_median(df: pd.DataFrame, cluster_cols: list[str], metric: str,
                              n_boot: int, seed: int) -> tuple[float, float, float]:
    """Resample CLUSTERS (e.g. (seed,silo) pairs) with replacement, take all
    rows for each resampled cluster, compute the median. Returns
    (point_estimate, ci_low, ci_high).
    """
    rng = np.random.default_rng(seed)
    clusters = df[cluster_cols].drop_duplicates().to_records(index=False).tolist()
    n_clusters = len(clusters)
    point = df[metric].median()

    boot_medians = np.empty(n_boot)
    grouped = {tuple(c): g[metric].to_numpy() for c, g in df.groupby(cluster_cols)}
    for b in range(n_boot):
        picks = rng.choice(n_clusters, size=n_clusters, replace=True)
        vals = np.concatenate([grouped[clusters[i]] for i in picks])
        boot_medians[b] = np.median(vals)

    ci_low, ci_high = np.percentile(boot_medians, [2.5, 97.5])
    return point, ci_low, ci_high, n_clusters


def naive_row_bootstrap_median(values: np.ndarray, n_boot: int, seed: int):
    rng = np.random.default_rng(seed)
    n = len(values)
    point = np.median(values)
    boots = np.array([np.median(rng.choice(values, size=n, replace=True)) for _ in range(n_boot)])
    ci_low, ci_high = np.percentile(boots, [2.5, 97.5])
    return point, ci_low, ci_high


def main() -> int:
    print("=" * 78)
    print("PART 1: BOOTSTRAP CIs -- alpha=0.1 federated agreement vs centralized floor")
    print("=" * 78)

    agree = pd.read_csv(AGREEMENT_PATH)
    agree_elig = agree[agree.family_eligible].copy()
    agree_elig["alpha"] = agree_elig["alpha"].astype(str)
    a01 = agree_elig[agree_elig.alpha == "0.1"]

    floor = pd.read_csv(FLOOR_PATH)

    for metric in METRICS:
        print(f"\n--- {metric} ---")

        # Federated side: cluster bootstrap by (seed, silo)
        point, lo, hi, n_clusters = cluster_bootstrap_median(
            a01, ["seed", "silo"], metric, N_BOOT, RNG_SEED
        )
        print(f"alpha=0.1 federated agreement: median={point:.4f}  "
              f"95% CI=[{lo:.4f}, {hi:.4f}]  (cluster bootstrap, {n_clusters} silo-clusters)")

        # Also naive row-level bootstrap, flagged as likely too narrow
        p2, l2, h2 = naive_row_bootstrap_median(a01[metric].to_numpy(), N_BOOT, RNG_SEED)
        print(f"  (naive row-level bootstrap for comparison: [{l2:.4f}, {h2:.4f}] -- "
              f"likely too narrow, ignores within-silo correlation)")

        # Floor: report the raw 3 pair-medians directly -- NOT independent
        # (only 3 seeds exist; each seed appears in 2 of the 3 pairs)
        pair_medians = floor.groupby("seed_pair")[metric].median()
        print(f"\ncentralized floor -- raw per-pair medians (NOT independent, "
              f"only 3 underlying seeds):")
        for pair, val in pair_medians.items():
            print(f"    {pair}: {val:.4f}")
        print(f"  range: [{pair_medians.min():.4f}, {pair_medians.max():.4f}]  "
              f"(span={pair_medians.max()-pair_medians.min():.4f})")
        floor_median = floor[metric].median()
        print(f"  overall median (all 42 rows pooled): {floor_median:.4f}")

        # Naive row bootstrap on the floor too, heavily caveated
        pf, lf, hf = naive_row_bootstrap_median(floor[metric].to_numpy(), N_BOOT, RNG_SEED)
        print(f"  naive row-level bootstrap: [{lf:.4f}, {hf:.4f}] -- CAUTION: only 3 "
              f"independent models underlie this; this interval is almost certainly "
              f"too narrow to trust as-is.")

        # Overlap check using the more honest interval pairing:
        # federated cluster-bootstrap CI vs floor's raw pair-median range
        overlap_vs_range = not (hi < pair_medians.min() or lo > pair_medians.max())
        overlap_vs_naive = not (hi < lf or lo > hf)
        print(f"\n  Federated 95% CI vs floor's raw pair-median range: "
              f"{'OVERLAP' if overlap_vs_range else 'NO OVERLAP'}")
        print(f"  Federated 95% CI vs floor's naive bootstrap CI: "
              f"{'OVERLAP' if overlap_vs_naive else 'NO OVERLAP'}")

    print("\n" + "=" * 78)
    print("PART 2: WITHIN-ALPHA correlation -- silo agreement vs silo size")
    print("=" * 78)

    per_silo = pd.read_csv(PER_SILO_PATH)
    per_silo["alpha"] = per_silo["alpha"].astype(str)

    sizes_long = pd.read_csv(SIZES_PATH)
    sizes_long["alpha"] = sizes_long["alpha"].astype(str)
    sizes_total = sizes_long.groupby(["alpha", "seed", "silo"])["n"].sum().reset_index()
    sizes_total = sizes_total.rename(columns={"n": "total_size"})

    merged = per_silo.merge(sizes_total, on=["alpha", "seed", "silo"], how="left")

    for alpha_val in ["0.1", "0.5", "5.0"]:
        sub = merged[merged.alpha == alpha_val]
        print(f"\n--- alpha={alpha_val} (n={len(sub)} silos) ---")
        for metric in METRICS:
            valid = sub.dropna(subset=[metric, "total_size"])
            if len(valid) < 3:
                print(f"  {metric}: too few points ({len(valid)}) for correlation")
                continue
            r_p, p_p = pearsonr(valid["total_size"], valid[metric])
            r_s, p_s = spearmanr(valid["total_size"], valid[metric])
            print(f"  {metric} vs silo_size: Pearson r={r_p:+.3f} (p={p_p:.3f})  "
                  f"Spearman rho={r_s:+.3f} (p={p_s:.3f})  n={len(valid)}")

    out = merged[["alpha", "seed", "silo", "jaccard_at_10", "kendall_weighted_tau", "total_size"]]
    out_path = Path("results/inspection/silo_size_vs_agreement.csv")
    out.to_csv(out_path, index=False)
    print(f"\nWritten: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
