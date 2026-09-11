"""Deletion faithfulness curve -- one config (alpha=0.5, seed=42), global
model + 3 silos. Confirms the explanations being compared for agreement are
actually faithful, not two possibly-wrong explainers agreeing with each
other (the exact caveat in the project instructions).

Substitution value: per-feature TRAIN-SET MEAN of that model's own scaled
data, not zero -- 28 of 82 features are zero-inflated, so zero is itself a
meaningful, on-manifold value, and using it would mean measuring the model's
response to a plausible input rather than to feature removal.

Reuses already-computed SHAP values (no re-running SHAP) -- only does cheap
forward passes to trace the confidence-collapse curve.

Run from project root: python tools/deletion_curve.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "federated")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

from xfed_federated import task  # noqa: E402
from xfed_federated._vendored.schema import derive_feature_cols, load_label_vocabulary  # noqa: E402

from eval_set_config import N_EVAL_ROWS, EVAL_SEED  # noqa: E402

ALPHA, SEED = "0.5", 42
SILO_IDS = [0, 1, 2]

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
SHAP_DIR = Path(f"results/shap/fedavg_a{ALPHA}_s{SEED}")
OUT_DIR = Path("results/figures")
CSV_OUT = Path("results/inspection/deletion_auc.csv")


def trapz_auc(curve: np.ndarray) -> float:
    """Version-safe trapezoidal AUC, normalized to [0,1] range regardless of
    curve length. np.trapz was removed in NumPy 2.0 (renamed np.trapezoid),
    so this works across versions without depending on either name existing.
    """
    n = len(curve) - 1
    area = 0.5 * (curve[0] + curve[-1]) + curve[1:-1].sum()
    return float(area / n)


def rebuild_eval_rows(data_cfg, model_cfg):
    test_path = Path("data/processed/test_global.parquet")
    columns = list(pq.ParquetFile(test_path).schema_arrow.names)
    feature_cols = derive_feature_cols(columns, data_cfg)
    df = pd.read_parquet(test_path, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)
    vocab = load_label_vocabulary(model_cfg)
    headline = model_cfg["labels"]["headline_classes"]

    n_per_class = max(1, N_EVAL_ROWS // len(headline))
    picked_X, picked_fam = [], []
    for fam in headline:
        fam_df = df[df.family == fam]
        n = min(n_per_class, len(fam_df))
        s = fam_df.sample(n=n, random_state=EVAL_SEED)
        picked_X.append(s[feature_cols].to_numpy(np.float32))
        picked_fam.extend([fam] * n)
    X_raw = np.concatenate(picked_X, axis=0)
    y = np.array([vocab[f] for f in picked_fam], dtype=np.int64)
    return X_raw, y, picked_fam


def scale_rows(X_raw, center, scale):
    return ((X_raw - center) / scale).astype(np.float32)


def deletion_curve_for_model(model, eval_X_scaled: np.ndarray, eval_y: np.ndarray,
                              shap_values: np.ndarray, feature_mean: np.ndarray) -> np.ndarray:
    """Returns array of shape (n_features+1,): mean true-class softmax
    probability as 0, 1, 2, ... features are progressively deleted (top
    |SHAP| first). Deletion order and substitution done per-sample.
    """
    n_samples, n_features = eval_X_scaled.shape
    curve = np.zeros(n_features + 1, dtype=np.float64)

    with torch.no_grad():
        for i in range(n_samples):
            true_class = int(eval_y[i])
            sv = shap_values[i, :, true_class]
            order = np.argsort(-np.abs(sv))  # most important first

            x = eval_X_scaled[i].copy()
            probs = []
            for n_deleted in range(n_features + 1):
                xt = torch.from_numpy(x[None, :].astype(np.float32))
                logits = model(xt).numpy()[0]
                p = np.exp(logits - logits.max())
                p = p / p.sum()
                probs.append(p[true_class])
                if n_deleted < n_features:
                    feat_idx = order[n_deleted]
                    x[feat_idx] = feature_mean[feat_idx]
            curve += np.array(probs)

    return curve / n_samples


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    manifest = json.loads(MANIFEST_PATH.read_text())
    tag = f"fedavg_a{ALPHA}_s{SEED}"
    entry = next(e for e in manifest if e["tag"] == tag)

    eval_X_raw, eval_y, eval_families = rebuild_eval_rows(data_cfg, model_cfg)

    curves = {}
    aucs = {}

    # --- Global model ---
    print("Global model ...")
    centralized_splits = task.load_centralized_for_server(data_cfg, model_cfg)
    global_model = task.build_model(model_cfg, seed=SEED, device="cpu")
    global_model.load_state_dict(torch.load(entry["global_checkpoint"], map_location="cpu"))
    global_model.eval()

    eval_X_global = scale_rows(eval_X_raw, centralized_splits.scaler_center, centralized_splits.scaler_scale)
    global_shap = np.load(SHAP_DIR / "global_shap.npz", allow_pickle=True)["shap_values"]
    feat_mean_global = centralized_splits.X_train.mean(axis=0)

    curve = deletion_curve_for_model(global_model, eval_X_global, eval_y, global_shap, feat_mean_global)
    curves["global"] = curve
    aucs["global"] = trapz_auc(curve)
    print(f"  deletion AUC: {aucs['global']:.4f}")

    # --- 3 silos ---
    for silo_id in SILO_IDS:
        print(f"Silo {silo_id} ...")
        splits = task.load_silo_for_client(silo_id, ALPHA, SEED, data_cfg, model_cfg, class_weights)
        model = task.build_model(model_cfg, seed=SEED, device="cpu")
        model.load_state_dict(torch.load(entry["silo_checkpoints"][silo_id], map_location="cpu"))
        model.eval()

        eval_X_silo = scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
        silo_shap = np.load(SHAP_DIR / f"silo_{silo_id}_shap.npz", allow_pickle=True)["shap_values"]
        feat_mean_silo = splits.X_train.mean(axis=0)

        curve = deletion_curve_for_model(model, eval_X_silo, eval_y, silo_shap, feat_mean_silo)
        curves[f"silo_{silo_id}"] = curve
        aucs[f"silo_{silo_id}"] = trapz_auc(curve)
        print(f"  deletion AUC: {aucs[f'silo_{silo_id}']:.4f}")

    # --- Plot ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    x_axis = np.arange(83) / 82 * 100  # % of features deleted

    for name, curve in curves.items():
        ax.plot(x_axis, curve, label=f"{name} (AUC={aucs[name]:.3f})", linewidth=2)

    ax.set_xlabel("% of features deleted (most important first, by |SHAP|)")
    ax.set_ylabel("Mean probability assigned to true class")
    ax.set_title(f"Deletion faithfulness curve\nfedavg_a{ALPHA}_s{SEED}, global + 3 silos")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path = OUT_DIR / "deletion_curve.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"\nSaved: {out_path}")

    auc_df = pd.DataFrame([{"model": k, "deletion_auc": v} for k, v in aucs.items()])
    auc_df.to_csv(CSV_OUT, index=False)
    print(f"Written: {CSV_OUT}")
    print("\nLower AUC = confidence collapses faster = more faithful explanation")
    print(auc_df.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
