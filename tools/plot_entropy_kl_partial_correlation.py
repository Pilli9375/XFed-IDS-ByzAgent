"""Figure: zero-order vs log(size)-partial correlation with agreement, for
the two heterogeneity covariates this project tried in sequence -- label
entropy (pre-specified, abandoned) and KL divergence from the global label
distribution (its replacement) -- side by side across alpha. Makes visible
the confounding signature described in docs/measurement_protocol.md Sec 10
item 5: entropy's correlation with agreement WEAKENS AND FLIPS SIGN once
log(silo size) is partialled out (the signature of an effect actually
carried by size), while KL's does not.

Source: results/inspection/size_matched_heterogeneity.csv (per-silo
log_size, entropy, kl_from_global, jaccard_at_10, kendall_weighted_tau) --
already on disk, produced by an earlier (uncommitted, one-off) analysis
script; no new SHAP, training, or partitioning here. This script computes
Pearson zero-order correlations directly, and partial correlations by the
standard residualization method (regress X on log_size, regress Y on
log_size, correlate the two residual sets) -- the same definition
docs/measurement_protocol.md Sec 10 item 5 describes ("partial correlation
controlling for log(silo size)"). Numbers are cross-checked at the bottom of this script's output against the
ranges already published there (entropy zero-order approx -0.12 to -0.15 at
alpha=0.5; entropy partial +0.13/+0.23 magnitudes; KL partial -0.57 at
alpha=0.1, -0.82/-0.87 at alpha=0.5) as a consistency check, not introduced
as new findings. One correction fell out of this check: the published text
paired the entropy-partial magnitudes as "+0.13/+0.23 for Jaccard@10/
weighted tau" -- recomputing directly from this CSV gives Jaccard@10=+0.23,
weighted tau=+0.13, the reverse pairing (same two magnitudes, swapped
metric). Fixed in docs/measurement_protocol.md Sec 10 item 5 and
docs/contribution_a_results.md Sec 5 as part of producing this figure.

Run from project root: python tools/plot_entropy_kl_partial_correlation.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

DATA_PATH = Path("results/inspection/size_matched_heterogeneity.csv")
OUT_DIR = Path("results/figures")

METRIC = "jaccard_at_10"  # the primary headline metric used throughout this project
ALPHAS = ["0.1", "0.5", "5.0"]


def partial_corr(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    """Standard residualization partial correlation of x,y controlling for z."""
    bx = np.polyfit(z, x, 1)
    by = np.polyfit(z, y, 1)
    resid_x = x - np.polyval(bx, z)
    resid_y = y - np.polyval(by, z)
    r, _ = pearsonr(resid_x, resid_y)
    return r


def main() -> int:
    df = pd.read_csv(DATA_PATH)
    df["alpha"] = df["alpha"].astype(str)
    df.loc[df["alpha"] == "5", "alpha"] = "5.0"

    rows = []
    for alpha in ALPHAS:
        sub = df[df.alpha == alpha]
        y = sub[METRIC].to_numpy()
        z = sub["log_size"].to_numpy()

        for covariate, label in [("entropy", "Label entropy (pre-specified)"),
                                  ("kl_from_global", "KL from global (replacement)")]:
            x = sub[covariate].to_numpy()
            r0, _ = pearsonr(x, y)
            rp = partial_corr(x, y, z)
            rows.append({"alpha": alpha, "covariate": label, "zero_order": r0, "partial": rp, "n": len(sub)})

    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    print("\nConsistency check against docs/measurement_protocol.md Sec 10 item 5:")
    a05_entropy = res[(res.alpha == "0.5") & (res.covariate.str.startswith("Label"))].iloc[0]
    a05_kl = res[(res.alpha == "0.5") & (res.covariate.str.startswith("KL"))].iloc[0]
    a01_kl = res[(res.alpha == "0.1") & (res.covariate.str.startswith("KL"))].iloc[0]
    print(f"  entropy zero-order @ a=0.5: {a05_entropy.zero_order:.3f}  (published range: -0.12 to -0.15)")
    print(f"  entropy partial    @ a=0.5: {a05_entropy.partial:.3f}  (published, corrected: +0.23, jaccard@10)")
    print(f"  KL partial         @ a=0.5: {a05_kl.partial:.3f}  (published: -0.82, jaccard@10)")
    print(f"  KL partial         @ a=0.1: {a01_kl.partial:.3f}  (published: -0.57)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
    colors = {"Label entropy (pre-specified)": "tab:orange", "KL from global (replacement)": "tab:purple"}
    x_pos = np.arange(len(ALPHAS))
    width = 0.32

    for ax, kind, title in [(axes[0], "zero_order", "Zero-order correlation with Jaccard@10"),
                             (axes[1], "partial", "Partial correlation, controlling for log(silo size)")]:
        for i, covariate in enumerate(["Label entropy (pre-specified)", "KL from global (replacement)"]):
            vals = [res[(res.alpha == a) & (res.covariate == covariate)][kind].iloc[0] for a in ALPHAS]
            offset = (i - 0.5) * width
            ax.bar(x_pos + offset, vals, width, label=covariate, color=colors[covariate],
                    edgecolor="black", linewidth=0.6)
        ax.axhline(0, color="black", linewidth=0.9)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(ALPHAS)
        ax.set_xlabel("Dirichlet alpha")
        ax.set_title(title, fontsize=10.5)
        ax.grid(True, axis="y", alpha=0.3)

    axes[0].set_ylabel(f"Pearson r ({METRIC})")
    axes[1].legend(loc="lower right", fontsize=8.5)

    # Highlight the sign-flip at alpha=0.5 explicitly.
    a05_idx = ALPHAS.index("0.5")
    axes[1].annotate("sign flip vs.\nzero-order panel",
                       xy=(a05_idx - width / 2, a05_entropy.partial),
                       xytext=(a05_idx - width / 2 - 0.55, a05_entropy.partial + 0.28),
                       fontsize=8.5, style="italic", color="tab:orange",
                       arrowprops=dict(arrowstyle="->", color="tab:orange", linewidth=1.2))

    fig.suptitle("Entropy's correlation with agreement is carried by silo size; KL's is not\n"
                  "(size and heterogeneity are jointly determined by the same Dirichlet draw -- see Sec 10 item 5)",
                  fontsize=11.5, y=1.04)
    fig.text(0.5, -0.02,
              "Source: results/inspection/size_matched_heterogeneity.csv. Partial r controls for log(silo size) "
              "via linear residualization.",
              ha="center", fontsize=7.5, color="dimgray")
    fig.tight_layout()

    out_path = OUT_DIR / "entropy_kl_partial_correlation.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
