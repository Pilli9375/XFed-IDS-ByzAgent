"""Figure: the centralized-seed instability floor's MEDIAN AND RANGE, plotted
against the alpha agreement sweep -- the headline methodological contribution
of this project, which until now existed only as numbers (PROJECT_INSTRUCTIONS.md's
headline table, docs/contribution_a_results.md Sec 2).

Distinct from tools/plot_agreement_vs_alpha.py (which draws the floor as a
single median line): this figure shows the floor as a shaded RANGE (the span
across the 3 seed-pair medians -- not independent, only 3 seeds underlie it,
see centralized_instability_floor.csv), and overlays the cluster-bootstrap
95% CI at alpha=0.1 -- the only alpha where the "at or below the floor"
question is close enough to need one. The CI visibly overlaps the floor's
range in both panels: this is drawn deliberately so the figure cannot be
misread as showing statistical significance. alpha=0.5 and alpha=5.0 are
shown with their raw IQR band only (as in the existing headline figure) --
no bootstrap CI is claimed for those slices because none has been computed
for them anywhere in this project; nothing here should be read as implying
one.

Cluster-bootstrap CI at alpha=0.1 is reproduced via the exact function
already committed in tools/chat04_closeout.py (cluster_bootstrap_median,
resample by (seed, silo), RNG_SEED=0, N_BOOT=10000, fully deterministic) --
imported directly, not reimplemented, so this figure's CI is guaranteed
identical to the number already cited in PROJECT_INSTRUCTIONS.md
([0.250, 0.429]) and docs/contribution_a_results.md.

Run from project root: python tools/plot_instability_floor_vs_alpha.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "tools")
from chat04_closeout import cluster_bootstrap_median, N_BOOT, RNG_SEED  # noqa: E402  (reused, not reimplemented)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AGREEMENT_PATH = Path("results/inspection/agreement_metrics.csv")
FLOOR_PATH = Path("results/inspection/centralized_instability_floor.csv")
OUT_DIR = Path("results/figures")

CHANCE_JACCARD_10 = 0.0649  # analytical formula, k=10, n=82 features -- same constant as plot_agreement_vs_alpha.py


def main() -> int:
    df = pd.read_csv(AGREEMENT_PATH)
    df = df[df.family_eligible].copy()
    df["alpha_f"] = df["alpha"].astype(float)
    df["alpha_s"] = df["alpha"].astype(str)

    floor_df = pd.read_csv(FLOOR_PATH)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    metrics = [("jaccard_at_10", "Jaccard@10", CHANCE_JACCARD_10, axes[0]),
               ("kendall_weighted_tau", "Kendall's weighted tau", None, axes[1])]

    alphas_sorted = sorted(df["alpha_f"].unique())
    alpha_strs = [str(a) if a != 5.0 else "5.0" for a in alphas_sorted]

    for metric_col, metric_label, chance_val, ax in metrics:
        medians, q1s, q3s = [], [], []
        for a in alphas_sorted:
            vals = df[df.alpha_f == a][metric_col]
            medians.append(vals.median())
            q1s.append(vals.quantile(0.25))
            q3s.append(vals.quantile(0.75))
        medians, q1s, q3s = np.array(medians), np.array(q1s), np.array(q3s)

        ax.plot(alphas_sorted, medians, marker="o", color="tab:blue", linewidth=2,
                 label="Silo-local vs global (federated), IQR band", zorder=3)
        ax.fill_between(alphas_sorted, q1s, q3s, alpha=0.18, color="tab:blue", zorder=1)

        # Floor: shaded RANGE across the 3 (non-independent) seed-pair medians,
        # not just a single line -- this is the number that matters for the claim.
        pair_medians = floor_df.groupby("seed_pair")[metric_col].median()
        floor_lo, floor_hi = pair_medians.min(), pair_medians.max()
        floor_med = floor_df[metric_col].median()
        ax.axhspan(floor_lo, floor_hi, color="tab:red", alpha=0.15, zorder=0,
                    label=f"Instability floor range [{floor_lo:.3f}, {floor_hi:.3f}]\n"
                          f"(3 seed-pair medians, seeds 42/1337/2024 -- not independent)")
        ax.axhline(floor_med, color="tab:red", linestyle="--", linewidth=1.5,
                    label=f"Floor median ({floor_med:.3f})", zorder=2)

        # Cluster-bootstrap 95% CI at alpha=0.1 only -- the one slice this
        # project has actually computed a CI for. Drawn as an explicit error
        # bar so the overlap with the floor range is visible, not asserted.
        a01 = df[df.alpha_s == "0.1"]
        point, ci_lo, ci_hi, n_clusters = cluster_bootstrap_median(
            a01, ["seed", "silo"], metric_col, N_BOOT, RNG_SEED
        )
        ax.errorbar([0.1], [point], yerr=[[point - ci_lo], [ci_hi - point]],
                     fmt="D", color="black", markersize=7, capsize=6, linewidth=1.8,
                     zorder=4, label=f"alpha=0.1: 95% CI [{ci_lo:.3f}, {ci_hi:.3f}]\n"
                                      f"(cluster bootstrap, n={n_clusters} silo-clusters)")

        overlaps = not (ci_hi < floor_lo or ci_lo > floor_hi)
        ax.annotate("CIs overlap -- directional,\nnot significant" if overlaps else "no overlap",
                     xy=(0.1, ci_lo), xytext=(0.14, floor_lo - 0.11 if metric_col == "jaccard_at_10" else floor_lo - 0.09),
                     fontsize=8.5, color="black", style="italic",
                     arrowprops=dict(arrowstyle="-", color="gray", linewidth=0.8))

        if chance_val is not None:
            ax.axhline(chance_val, color="gray", linestyle=":", linewidth=1.5,
                        label=f"Chance level ({chance_val:.3f})", zorder=1)

        ax.set_xscale("log")
        ax.set_xticks(alphas_sorted)
        ax.set_xticklabels(alpha_strs)
        ax.set_xlabel("Dirichlet alpha (lower = more non-IID)")
        ax.set_ylabel(metric_label)
        ax.set_title(f"{metric_label} vs alpha, with instability floor")
        ax.legend(loc="lower right", fontsize=7)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Federated agreement vs the centralized-seed instability floor\n"
                  "(the null control: how much agreement varies from seed alone, federation removed)",
                  fontsize=12, y=1.03)
    fig.text(0.5, -0.02,
              "Source: results/inspection/agreement_metrics.csv, centralized_instability_floor.csv. "
              "alpha=0.1 CI reproduced via tools/chat04_closeout.py::cluster_bootstrap_median (seed=0, deterministic).",
              ha="center", fontsize=7.5, color="dimgray")
    fig.tight_layout()

    out_path = OUT_DIR / "instability_floor_vs_alpha.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
