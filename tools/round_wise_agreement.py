"""Round-wise explanation agreement: does explanation consistency converge at
the same rate as accuracy, or lag it? Computed at rounds 5, 10, 15, 20 (not
just the best-by-validation round R*) using the SHAP values round_wise_shap.py
wrote to results/shap/<tag>/round_wise/round_NNN/.

REDUCED FIDELITY, THIS PASS ONLY: the input SHAP values used nsamples=1000
(headline pipeline uses 4000) -- see round_wise_shap.py. Do not compare these
jaccard_at_10 / tau_w numbers directly against results/inspection/
agreement_metrics.csv (the headline file); treat this pass as a convergence
shape check, not a replacement for the headline numbers.

Metric functions (jaccard_topk, chance_jaccard) and the weighted-Kendall's-tau
call are reused from tools/agreement_metrics.py, not reimplemented. Only the
per-round orchestration and aggregation are new.

Eligibility: same T_SILO=400 / M_FAMILY=20 filters as the headline pipeline,
computed once from results/inspection/silo_sizes.csv (a property of each
silo's data, not of the round) and applied identically at every round.

Aggregation: mean jaccard_at_10 / tau_w across the 14 fixed eval rows,
restricted to family_eligible rows, per (tag, alpha, seed, round, silo_id) --
matching agreement_metrics.py's own "family_eligible rows only" convention
for comparability of method, not of absolute numbers (see fidelity note
above).

Accuracy overlay: the figure plots val_macro_f1_headline, not accuracy or
test performance. This project never reports raw accuracy (severe class
imbalance), and the test set has already been touched once (locked decision)
-- reusing it here to score every round would touch it a second time. Per-
round val_macro_f1_headline is already logged in
results/federated/<tag>/round_history.json from training and requires no new
evaluation.

Run from project root: python tools/round_wise_agreement.py
"""
from __future__ import annotations

import sys
sys.path.insert(0, "tools")
# local_shap_pipeline (pyarrow -> shap -> torch) imported first, before numpy/
# pandas/matplotlib -- see the import-order note in round_wise_shap.py's
# docstring (importing torch ahead of shap crashed with 0xC0000005 here).
from local_shap_pipeline import EVAL_SEED  # noqa: E402
import agreement_metrics as am  # noqa: E402  (reused, not reimplemented)

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROUNDS = [5, 10, 15, 20]
NSAMPLES_USED = 1000  # reduced fidelity, this pass only -- see docstring

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
SHAP_ROOT = Path("results/shap")
FEDERATED_ROOT = Path("results/federated")
OUT_CSV = Path("results/inspection/round_wise_agreement.csv")
OUT_META = Path("results/inspection/round_wise_agreement_metadata.json")
OUT_FIG = Path("results/figures/agreement_vs_round.png")


def compute_rows(manifest: list[dict], sizes_long: pd.DataFrame, total_sizes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for entry in manifest:
        alpha, seed, tag = entry["alpha"], entry["seed"], entry["tag"]

        for round_num in ROUNDS:
            round_dir = SHAP_ROOT / tag / "round_wise" / f"round_{round_num:03d}"
            global_npz = np.load(round_dir / "global_shap.npz", allow_pickle=True)
            global_sv = global_npz["shap_values"]             # (n_eval, 82, 9)
            eval_y = global_npz["eval_y"]
            eval_families = list(global_npz["eval_families"])
            n_eval = global_sv.shape[0]

            for silo_id in range(10):
                size_row = total_sizes[(total_sizes.alpha == alpha) &
                                        (total_sizes.seed == seed) &
                                        (total_sizes.silo == silo_id)]
                silo_size_ok = bool(size_row["size_eligible"].iloc[0]) if not size_row.empty else False
                if not silo_size_ok:
                    continue  # excluded silo -- same eligibility as the headline pipeline

                silo_npz_path = round_dir / f"silo_{silo_id}_shap.npz"
                if not silo_npz_path.exists():
                    continue
                silo_sv = np.load(silo_npz_path, allow_pickle=True)["shap_values"]

                jaccards, taus = [], []
                for sample_idx in range(n_eval):
                    family = str(eval_families[sample_idx])
                    if not am.is_family_eligible(sizes_long, alpha, seed, silo_id, family):
                        continue
                    true_class = int(eval_y[sample_idx])
                    g_vec = global_sv[sample_idx, :, true_class]
                    s_vec = silo_sv[sample_idx, :, true_class]

                    jaccards.append(am.jaccard_topk(g_vec, s_vec, k=10))
                    try:
                        tau_w, _ = am.weightedtau(g_vec, s_vec)
                    except Exception:
                        tau_w = float("nan")
                    taus.append(tau_w)

                if not jaccards:
                    continue  # no family-eligible eval rows for this silo

                rows.append({
                    "tag": tag, "alpha": alpha, "seed": seed, "round": round_num,
                    "silo_id": silo_id,
                    "jaccard_at_10": float(np.nanmean(jaccards)),
                    "tau_w": float(np.nanmean(taus)),
                })

    return pd.DataFrame(rows)


def load_val_f1_by_round(manifest: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in manifest:
        alpha, seed, tag = entry["alpha"], entry["seed"], entry["tag"]
        history = json.loads((FEDERATED_ROOT / tag / "round_history.json").read_text())
        by_round = {h["round"]: h["val_macro_f1_headline"] for h in history}
        for round_num in ROUNDS:
            if round_num in by_round:
                rows.append({"alpha": alpha, "seed": seed, "round": round_num,
                              "val_macro_f1_headline": by_round[round_num]})
    return pd.DataFrame(rows)


def make_figure(agreement_df: pd.DataFrame, f1_df: pd.DataFrame) -> None:
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(8, 5.5))
    ax2 = ax1.twinx()

    colors = {"0.1": "tab:red", "0.5": "tab:orange", "5.0": "tab:blue"}
    alphas_sorted = sorted(agreement_df["alpha"].unique(), key=float)

    for alpha in alphas_sorted:
        sub = agreement_df[agreement_df.alpha == alpha]
        agg = sub.groupby("round")["jaccard_at_10"].mean().reindex(ROUNDS)
        ax1.plot(ROUNDS, agg.values, marker="o", linewidth=2,
                  color=colors.get(alpha, "black"), label=f"alpha={alpha} (Jaccard@10)")

        f1_sub = f1_df[f1_df.alpha == alpha]
        f1_agg = f1_sub.groupby("round")["val_macro_f1_headline"].mean().reindex(ROUNDS)
        ax2.plot(ROUNDS, f1_agg.values, marker="s", linestyle="--", linewidth=1.5,
                  color=colors.get(alpha, "black"), alpha=0.5)

    ax1.set_xlabel("Federated round")
    ax1.set_ylabel("Mean Jaccard@10 (silo-local vs global, family-eligible)")
    ax2.set_ylabel("Val macro-F1 (headline classes), dashed")
    ax1.set_xticks(ROUNDS)
    ax1.set_title(f"Explanation agreement vs val macro-F1 across rounds\n"
                   f"(reduced fidelity: nsamples={NSAMPLES_USED}, see script docstring)")
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=200, bbox_inches="tight")
    print(f"Saved: {OUT_FIG}")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text())
    sizes_long = pd.read_csv(am.SIZES_PATH)
    sizes_long["alpha"] = sizes_long["alpha"].astype(str)
    total_sizes = am.build_eligibility({})

    df = compute_rows(manifest, sizes_long, total_sizes)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"Written: {OUT_CSV}  ({len(df)} rows)")

    meta = {
        "generated_by": "tools/round_wise_agreement.py + tools/round_wise_shap.py",
        "nsamples": NSAMPLES_USED,
        "nsamples_note": "reduced fidelity, this pass only -- headline pipeline (results/inspection/agreement_metrics.csv) used nsamples=4000",
        "rounds": ROUNDS,
        "n_eval_rows": 14,
        "eval_seed": EVAL_SEED,
        "eligibility_filters": {"T_SILO": am.T_SILO, "M_FAMILY": am.M_FAMILY,
                                 "note": "computed once from silo_sizes.csv, applied identically at every round"},
        "aggregation": "mean jaccard_at_10 / tau_w across family-eligible eval rows, per (tag, alpha, seed, round, silo_id)",
        "accuracy_overlay_metric": "val_macro_f1_headline (not accuracy, not test -- see script docstring)",
        "n_configs": len(manifest),
    }
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(f"Written: {OUT_META}")

    f1_df = load_val_f1_by_round(manifest)
    make_figure(df, f1_df)

    print("\nMean Jaccard@10 by (alpha, round):")
    print(df.groupby(["alpha", "round"])["jaccard_at_10"].mean().to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
