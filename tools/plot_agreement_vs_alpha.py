"""The headline figure: cross-silo explanation agreement vs alpha, with the
chance-level baseline and the centralized-seed instability floor overlaid.

This is the single plot that carries the differentiator's finding: accuracy
parity does not imply explanation parity, and at severe heterogeneity
(alpha=0.1) agreement falls below what pure seed noise alone would produce.

Run from project root: python tools/plot_agreement_vs_alpha.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AGREEMENT_PATH = Path("results/inspection/agreement_metrics.csv")
FLOOR_PATH = Path("results/inspection/centralized_instability_floor.csv")
OUT_DIR = Path("results/figures")

CHANCE_JACCARD_10 = 0.0649  # from the analytical formula, k=10, n=82 features


def main() -> int:
    df = pd.read_csv(AGREEMENT_PATH)
    df = df[df.family_eligible]  # only eligibility-passing rows, as pre-registered
    df["alpha_f"] = df["alpha"].astype(float)

    floor_df = pd.read_csv(FLOOR_PATH)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    metrics = [("jaccard_at_10", "Jaccard@10", CHANCE_JACCARD_10, axes[0]),
               ("kendall_weighted_tau", "Kendall's weighted tau", None, axes[1])]

    alphas_sorted = sorted(df["alpha_f"].unique())

    for metric_col, metric_label, chance_val, ax in metrics:
        medians, q1s, q3s = [], [], []
        for a in alphas_sorted:
            vals = df[df.alpha_f == a][metric_col]
            medians.append(vals.median())
            q1s.append(vals.quantile(0.25))
            q3s.append(vals.quantile(0.75))

        medians = np.array(medians)
        q1s = np.array(q1s)
        q3s = np.array(q3s)

        ax.plot(alphas_sorted, medians, marker="o", color="tab:blue",
                linewidth=2, label="Silo-local vs global (federated)", zorder=3)
        ax.fill_between(alphas_sorted, q1s, q3s, alpha=0.2, color="tab:blue", zorder=2)

        floor_val = floor_df[metric_col].median()
        ax.axhline(floor_val, color="tab:red", linestyle="--", linewidth=1.5,
                   label=f"Centralized-seed instability floor ({floor_val:.3f})", zorder=2)

        if chance_val is not None:
            ax.axhline(chance_val, color="gray", linestyle=":", linewidth=1.5,
                       label=f"Chance level ({chance_val:.3f})", zorder=1)

        ax.set_xscale("log")
        ax.set_xticks(alphas_sorted)
        ax.set_xticklabels([str(a) for a in alphas_sorted])
        ax.set_xlabel("Dirichlet alpha (lower = more non-IID)")
        ax.set_ylabel(metric_label)
        ax.set_title(f"{metric_label} vs alpha\n(shaded band = IQR across eligible silo-samples)")
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Cross-silo explanation agreement vs non-IID severity", fontsize=13, y=1.02)
    fig.tight_layout()

    out_path = OUT_DIR / "agreement_vs_alpha.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Saved: {out_path}")

    print("\nSummary table:")
    summary = df.groupby("alpha_f")[["jaccard_at_10", "kendall_weighted_tau"]].agg(["median", "count"])
    print(summary.to_string())
    print(f"\nCentralized floor -- jaccard_at_10: {floor_df['jaccard_at_10'].median():.4f}, "
          f"kendall_weighted_tau: {floor_df['kendall_weighted_tau'].median():.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
