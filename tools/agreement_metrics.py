"""Jaccard@k and Kendall's weighted tau between global and silo-local SHAP
explanations. This is the headline computation -- the actual differentiator.

Reference class per eval sample: the TRUE family label, not each model's own
prediction. Chosen because (a) it's already saved in every .npz, no re-run
needed, and (b) it's a coherent, defensible target: "how does each model's
output support the true class," useful for both correct and incorrect
predictions alike.

Eligibility: recomputes the same T=400 (silo total size) and m=20 (per-family
count) filters from Pre-check C, applied to the SAME silo_sizes.csv already
on disk -- not re-derived differently here.

Run from project root: python tools/agreement_metrics.py
For a non-FedAvg manifest (e.g. FedProx), pass --manifest and --out so the
FedAvg agreement_metrics.csv is never touched:
  python tools/agreement_metrics.py \\
      --manifest results/inspection/best_rounds_manifest_fedprox_mu0.0005.json \\
      --out results/inspection/agreement_metrics_fedprox_mu0.0005.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import weightedtau

SHAP_ROOT = Path("results/shap")
MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
SIZES_PATH = Path("results/inspection/silo_sizes.csv")
OUT_PATH = Path("results/inspection/agreement_metrics.csv")

T_SILO = 400
M_FAMILY = 20
K_VALUES = (5, 10, 20)
N_FEATURES = 82


def jaccard_topk(a: np.ndarray, b: np.ndarray, k: int) -> float:
    """a, b: per-feature attribution vectors (signed). Top-k by |value|."""
    top_a = set(np.argsort(-np.abs(a))[:k])
    top_b = set(np.argsort(-np.abs(b))[:k])
    union = top_a | top_b
    if not union:
        return float("nan")
    return len(top_a & top_b) / len(union)


def chance_jaccard(k: int, n: int = N_FEATURES) -> float:
    """Expected Jaccard between two random k-subsets of n items."""
    exp_intersect = k * k / n
    exp_union = 2 * k - exp_intersect
    return exp_intersect / exp_union


def build_eligibility(alpha_str_map: dict) -> pd.DataFrame:
    sizes = pd.read_csv(SIZES_PATH)
    sizes["alpha"] = sizes["alpha"].astype(str)
    total = sizes.groupby(["alpha", "seed", "silo"])["n"].sum().reset_index()
    total["size_eligible"] = total["n"] >= T_SILO
    return total


def is_family_eligible(sizes_df: pd.DataFrame, alpha: str, seed: int, silo: int, family: str) -> bool:
    row = sizes_df[(sizes_df.alpha == alpha) & (sizes_df.seed == seed) &
                    (sizes_df.silo == silo) & (sizes_df.family == family)]
    if row.empty:
        return False
    return float(row["n"].iloc[0]) >= M_FAMILY


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=MANIFEST_PATH,
                     help="best-rounds manifest to read (default: results/inspection/best_rounds_manifest.json)")
    ap.add_argument("--out", type=Path, default=OUT_PATH,
                     help="output CSV path (default: results/inspection/agreement_metrics.csv)")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    sizes_long = pd.read_csv(SIZES_PATH)
    sizes_long["alpha"] = sizes_long["alpha"].astype(str)
    total_sizes = build_eligibility({})

    rows = []
    for entry in manifest:
        alpha, seed, tag = entry["alpha"], entry["seed"], entry["tag"]
        cfg_dir = SHAP_ROOT / tag

        global_npz = np.load(cfg_dir / "global_shap.npz", allow_pickle=True)
        global_sv = global_npz["shap_values"]            # (n_eval, 82, 9)
        eval_y = global_npz["eval_y"]                     # (n_eval,)
        eval_families = list(global_npz["eval_families"]) # (n_eval,) strings

        n_eval = global_sv.shape[0]

        for silo_id in range(10):
            size_row = total_sizes[(total_sizes.alpha == alpha) &
                                    (total_sizes.seed == seed) &
                                    (total_sizes.silo == silo_id)]
            silo_size_ok = bool(size_row["size_eligible"].iloc[0]) if not size_row.empty else False
            if not silo_size_ok:
                continue  # excluded silo (e.g. a0.1_s42 silo9) -- skip entirely

            silo_npz_path = cfg_dir / f"silo_{silo_id}_shap.npz"
            if not silo_npz_path.exists():
                continue
            silo_npz = np.load(silo_npz_path, allow_pickle=True)
            silo_sv = silo_npz["shap_values"]  # (n_eval, 82, 9)

            for sample_idx in range(n_eval):
                true_class = int(eval_y[sample_idx])
                family = str(eval_families[sample_idx])

                fam_eligible = is_family_eligible(sizes_long, alpha, seed, silo_id, family)

                g_vec = global_sv[sample_idx, :, true_class]
                s_vec = silo_sv[sample_idx, :, true_class]

                # weighted Kendall's tau -- downweights low-magnitude ranks
                try:
                    tau_w, _ = weightedtau(g_vec, s_vec)
                except Exception:
                    tau_w = float("nan")

                row = {
                    "alpha": alpha, "seed": seed, "silo": silo_id,
                    "sample_idx": sample_idx, "family": family,
                    "family_eligible": fam_eligible,
                    "kendall_weighted_tau": tau_w,
                }
                for k in K_VALUES:
                    row[f"jaccard_at_{k}"] = jaccard_topk(g_vec, s_vec, k)
                rows.append(row)

    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Written: {args.out}  ({len(df)} rows)")

    print("\n" + "=" * 70)
    print("CHANCE-LEVEL JACCARD BASELINE (random top-k overlap)")
    print("=" * 70)
    for k in K_VALUES:
        print(f"  k={k}: chance Jaccard = {chance_jaccard(k):.4f}")

    print("\n" + "=" * 70)
    print("MEDIAN AGREEMENT PER ALPHA (family_eligible rows only)")
    print("=" * 70)
    elig = df[df.family_eligible]
    summary = elig.groupby("alpha")[[f"jaccard_at_{k}" for k in K_VALUES] +
                                     ["kendall_weighted_tau"]].median()
    print(summary.to_string())

    print("\n" + "=" * 70)
    print("PER-FAMILY MEDIAN JACCARD@10 (family_eligible rows only) -- watch PortScan vs Bot/WebAttack")
    print("=" * 70)
    fam_summary = elig.groupby(["alpha", "family"])["jaccard_at_10"].agg(["median", "count"])
    print(fam_summary.to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
