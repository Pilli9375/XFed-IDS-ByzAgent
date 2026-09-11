"""Figure: the central claim, directly -- validation accuracy rising while
explanation agreement declines, across federated rounds, at the two non-IID
settings (alpha=0.1, alpha=0.5); flat agreement at alpha=5.0 where there is
little heterogeneity to decouple from. One panel per alpha (not overlaid, as
in the existing results/figures/agreement_vs_round.png) specifically so each
alpha's own accuracy-vs-agreement shape is unambiguous -- an overlay across
3 alphas on shared axes makes the divergence pattern hard to read at a
glance, which is the whole point of this figure.

Source: results/inspection/round_wise_agreement.csv (mean Jaccard@10 over
family_eligible==True rows, per (alpha, round), computed by
tools/round_wise_agreement.py at reduced fidelity nsamples=1000 -- a
convergence-shape check, not directly comparable in magnitude to the
headline agreement_metrics.csv numbers, see that script's docstring) and
results/federated/<tag>/round_history.json (val_macro_f1_headline, logged
during training, not re-evaluated here). No new SHAP or training.

Run from project root: python tools/plot_accuracy_agreement_decoupling.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROUND_AGREE_PATH = Path("results/inspection/round_wise_agreement.csv")
MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
FEDERATED_ROOT = Path("results/federated")
OUT_DIR = Path("results/figures")

ROUNDS = [5, 10, 15, 20]
ALPHAS = ["0.1", "0.5", "5.0"]
COLORS = {"0.1": "tab:red", "0.5": "tab:orange", "5.0": "tab:blue"}


def load_val_f1(manifest: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in manifest:
        alpha, seed, tag = entry["alpha"], entry["seed"], entry["tag"]
        history = json.loads((FEDERATED_ROOT / tag / "round_history.json").read_text())
        by_round = {h["round"]: h["val_macro_f1_headline"] for h in history}
        for r in ROUNDS:
            if r in by_round:
                rows.append({"alpha": alpha, "round": r, "val_f1": by_round[r]})
    return pd.DataFrame(rows)


def main() -> int:
    agree = pd.read_csv(ROUND_AGREE_PATH)
    agree["alpha"] = agree["alpha"].astype(str)
    agree_mean = agree.groupby(["alpha", "round"])["jaccard_at_10"].mean().reset_index()

    manifest = json.loads(MANIFEST_PATH.read_text())
    f1 = load_val_f1(manifest)
    f1_mean = f1.groupby(["alpha", "round"])["val_f1"].mean().reset_index()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharex=True)

    labels = {"0.1": "severe non-IID", "0.5": "moderate non-IID", "5.0": "near-IID"}

    for ax, alpha in zip(axes, ALPHAS):
        a_sub = agree_mean[agree_mean.alpha == alpha].sort_values("round")
        f_sub = f1_mean[f1_mean.alpha == alpha].sort_values("round")

        ax2 = ax.twinx()
        l1, = ax.plot(a_sub["round"], a_sub["jaccard_at_10"], marker="o", color=COLORS[alpha],
                        linewidth=2.4, label="Mean Jaccard@10 (agreement)")
        l2, = ax2.plot(f_sub["round"], f_sub["val_f1"], marker="s", linestyle="--",
                         color="black", linewidth=1.8, alpha=0.7, label="Val macro-F1 (accuracy)")

        j_delta = a_sub["jaccard_at_10"].iloc[-1] - a_sub["jaccard_at_10"].iloc[0]
        f_delta = f_sub["val_f1"].iloc[-1] - f_sub["val_f1"].iloc[0]
        verdict = "DECLINES" if j_delta < -0.01 else ("rises" if j_delta > 0.01 else "flat")
        ax.set_title(f"alpha={alpha} ({labels[alpha]})\n"
                      f"agreement {verdict} ({j_delta:+.3f}), accuracy {f_delta:+.3f}",
                      fontsize=10.5)

        ax.set_xlabel("Federated round")
        ax.set_xticks(ROUNDS)
        ax.grid(True, alpha=0.3)
        if alpha == "0.1":
            ax.set_ylabel("Mean Jaccard@10", color=COLORS[alpha])
        ax2.set_ylabel("Val macro-F1 (headline)" if alpha == "5.0" else "", color="black")
        ax.tick_params(axis="y", labelcolor=COLORS[alpha])

        if alpha == "0.1":
            ax.legend(handles=[l1, l2], loc="upper left", fontsize=8, bbox_to_anchor=(0.0, -0.16),
                       ncol=1, frameon=True)

    fig.suptitle("Accuracy and explanation agreement decouple under non-IID federation\n"
                  "(reduced-fidelity round-wise SHAP, nsamples=1000 -- convergence-shape check, "
                  "not the headline numbers)",
                  fontsize=12, y=1.06)
    fig.text(0.5, -0.03,
              "Source: results/inspection/round_wise_agreement.csv, results/federated/<tag>/round_history.json.",
              ha="center", fontsize=7.5, color="dimgray")
    fig.tight_layout()

    out_path = OUT_DIR / "accuracy_agreement_decoupling.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
