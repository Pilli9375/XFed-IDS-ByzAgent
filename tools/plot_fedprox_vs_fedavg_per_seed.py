"""Figure: FedProx (mu=0.0005) vs FedAvg, per INDIVIDUAL seed, at alpha=0.1
and alpha=0.5 -- deliberately not pooled across seeds. The point is seed
1337's reversal at alpha=0.1 (agreement AND accuracy both move down under
FedProx, while seeds 42 and 2024 both move up) -- a pooled mean would hide
exactly this, which is why docs/contribution_a_results.md Sec 6 calls
alpha=0.1 "inconclusive at n=3" rather than a clean finding either way.

Source: results/inspection/agreement_metrics.csv,
results/inspection/agreement_metrics_fedprox_mu0.0005.csv (mean Jaccard@10
over family_eligible==True rows, per alpha/seed -- same aggregation already
used and reported in docs/contribution_a_results.md Sec 6), and the two
best_rounds_manifest*.json files for test_macro_f1_headline. No new SHAP or
training; this is a re-plot of already-computed, already-reported numbers.

Run from project root: python tools/plot_fedprox_vs_fedavg_per_seed.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FEDAVG_AGREE = Path("results/inspection/agreement_metrics.csv")
FEDPROX_AGREE = Path("results/inspection/agreement_metrics_fedprox_mu0.0005.csv")
FEDAVG_MANIFEST = Path("results/inspection/best_rounds_manifest.json")
FEDPROX_MANIFEST = Path("results/inspection/best_rounds_manifest_fedprox_mu0.0005.json")
OUT_DIR = Path("results/figures")

SEEDS = [42, 1337, 2024]
ALPHAS = ["0.1", "0.5"]


def agree_per_seed(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["alpha"] = df["alpha"].astype(str)
    elig = df[df.family_eligible]
    return elig.groupby(["alpha", "seed"])["jaccard_at_10"].mean()


def f1_per_seed(path: Path) -> pd.Series:
    df = pd.DataFrame(json.loads(path.read_text()))
    df["alpha"] = df["alpha"].astype(str)
    return df.set_index(["alpha", "seed"])["test_macro_f1_headline"]


def main() -> int:
    fa_j = agree_per_seed(FEDAVG_AGREE)
    fp_j = agree_per_seed(FEDPROX_AGREE)
    fa_f1 = f1_per_seed(FEDAVG_MANIFEST)
    fp_f1 = f1_per_seed(FEDPROX_MANIFEST)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    x = np.arange(len(SEEDS))
    width = 0.32

    for ax, alpha in zip(axes, ALPHAS):
        j_fa = [fa_j[(alpha, s)] for s in SEEDS]
        j_fp = [fp_j[(alpha, s)] for s in SEEDS]

        bars_fa = ax.bar(x - width / 2, j_fa, width, label="FedAvg", color="tab:blue",
                           edgecolor="black", linewidth=0.6)
        bars_fp = ax.bar(x + width / 2, j_fp, width, label="FedProx (mu=0.0005)", color="tab:green",
                           edgecolor="black", linewidth=0.6)

        for i, s in enumerate(SEEDS):
            delta = j_fp[i] - j_fa[i]
            f1_delta = fp_f1[(alpha, s)] - fa_f1[(alpha, s)]
            color = "black"
            highlight = alpha == "0.1" and s == 1337
            ax.annotate(f"{delta:+.3f}\n(testF1 {f1_delta:+.3f})",
                         xy=(i, max(j_fa[i], j_fp[i]) + 0.015),
                         ha="center", fontsize=8,
                         color="tab:red" if highlight else "dimgray",
                         fontweight="bold" if highlight else "normal")

        if alpha == "0.1":
            # Circle seed 1337's bars -- the reversal this figure exists to show.
            idx_1337 = SEEDS.index(1337)
            ax.add_patch(plt.Rectangle((idx_1337 - width - 0.05, 0), 2 * width + 0.1,
                                         max(j_fa[idx_1337], j_fp[idx_1337]) + 0.06,
                                         fill=False, edgecolor="tab:red", linewidth=2,
                                         linestyle="--", zorder=5))
            ax.annotate("seed 1337 reverses:\nboth agreement and\naccuracy move DOWN\nunder FedProx",
                         xy=(idx_1337, j_fp[idx_1337]), xytext=(idx_1337 + 0.75, j_fa[idx_1337] + 0.09),
                         fontsize=8.5, color="tab:red", style="italic",
                         arrowprops=dict(arrowstyle="->", color="tab:red", linewidth=1.2))

        ax.set_xticks(x)
        ax.set_xticklabels([f"seed {s}" for s in SEEDS])
        ax.set_ylabel("Mean Jaccard@10 (family-eligible)")
        ax.set_title(f"alpha={alpha}", fontsize=11)
        ax.legend(loc="lower right", fontsize=8.5)
        ax.grid(True, axis="y", alpha=0.3)

    fig.suptitle("FedProx (mu=0.0005) vs FedAvg, per seed -- not pooled\n"
                  "labels: Delta Jaccard@10 (Delta test macro-F1(headline) in parens)",
                  fontsize=11.5, y=1.05)
    fig.text(0.5, -0.02,
              "Source: results/inspection/agreement_metrics.csv, agreement_metrics_fedprox_mu0.0005.csv, "
              "best_rounds_manifest.json, best_rounds_manifest_fedprox_mu0.0005.json.",
              ha="center", fontsize=7.5, color="dimgray")
    fig.tight_layout()

    out_path = OUT_DIR / "fedprox_vs_fedavg_per_seed.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
