"""Common-background ablation, alpha=0.5, seed=42: give the global model and
3 silos the SAME fixed background rows (scaled by each model's own scaler,
since that part must stay correct), instead of each independently drawing
its own background from its own training partition.

This bounds a real confound: locked decision 4 requires per-silo
backgrounds (a real privacy/methodology constraint, not a mistake), but
that also means differing backgrounds are baked into every agreement
number reported so far. This ablation asks: if we hold the background
constant, how much of the measured divergence survives? If most of it
survives, the divergence is genuinely about the models, not the backgrounds.

Run from project root: python tools/common_background_ablation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "federated")

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shap
import torch
from scipy.stats import weightedtau

from xfed_federated import task  # noqa: E402
from xfed_federated._vendored.schema import derive_feature_cols, load_label_vocabulary  # noqa: E402

from eval_set_config import N_EVAL_ROWS, EVAL_SEED  # noqa: E402

ALPHA, SEED = "0.5", 42
SILO_IDS = [0, 1, 2]
BACKGROUND_SEED = 55555
NSAMPLES = 4000
BACKGROUND_TARGET = 200
K_VALUES = (5, 10, 20)

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
AGREEMENT_PATH = Path("results/inspection/agreement_metrics.csv")
OUT_PATH = Path("results/inspection/common_background_ablation.csv")


def build_stratified_background(X, y, target_total, seed):
    rng = np.random.default_rng(seed)
    classes = np.unique(y)
    class_idx = {c: np.where(y == c)[0] for c in classes}
    base = max(1, target_total // len(classes))
    chosen, used = {}, 0
    for c in classes:
        avail = class_idx[c]
        take = min(base, len(avail))
        chosen[c] = rng.choice(avail, size=take, replace=False)
        used += take
    remaining = target_total - used
    if remaining > 0:
        room = [c for c in classes if len(class_idx[c]) > len(chosen[c])]
        while remaining > 0 and room:
            for c in list(room):
                if remaining <= 0:
                    break
                avail = class_idx[c]
                already = set(chosen[c].tolist())
                pool = np.array([i for i in avail if i not in already])
                if len(pool) == 0:
                    room.remove(c)
                    continue
                extra = rng.choice(pool, size=1, replace=False)
                chosen[c] = np.concatenate([chosen[c], extra])
                remaining -= 1
                if len(pool) == 1:
                    room.remove(c)
    idx = np.concatenate(list(chosen.values()))
    rng.shuffle(idx)
    return idx


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


def explain(model, background_X, eval_X_scaled):
    bt = torch.from_numpy(background_X.copy())
    et = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, bt)
    sv = np.array(explainer.shap_values(et, nsamples=NSAMPLES))
    with torch.no_grad():
        f_eval = model(et).numpy()
        f_bg = model(bt).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_eval - f_bg[None, :])
    return sv, float(np.abs(diff).max())


def jaccard_topk(a, b, k):
    top_a, top_b = set(np.argsort(-np.abs(a))[:k]), set(np.argsort(-np.abs(b))[:k])
    union = top_a | top_b
    return len(top_a & top_b) / len(union) if union else float("nan")


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    manifest = json.loads(MANIFEST_PATH.read_text())
    tag = f"fedavg_a{ALPHA}_s{SEED}"
    entry = next(e for e in manifest if e["tag"] == tag)

    eval_X_raw, eval_y, eval_families = rebuild_eval_rows(data_cfg, model_cfg)

    # Fixed COMMON raw background rows -- drawn once from the centralized
    # pooled train split, reused (with per-model scaling) for every model.
    centralized_splits = task.load_centralized_for_server(data_cfg, model_cfg)
    common_bg_idx = build_stratified_background(
        centralized_splits.X_train, centralized_splits.y_train, BACKGROUND_TARGET, BACKGROUND_SEED
    )
    # centralized_splits.X_train is already SCALED by the centralized scaler.
    # To get raw values usable with each model's own scaler, invert that scaling.
    common_bg_raw = (centralized_splits.X_train[common_bg_idx] * centralized_splits.scaler_scale
                      + centralized_splits.scaler_center)

    print(f"Common background: {common_bg_raw.shape[0]} fixed rows, reused across all models")

    svs = {}

    print("\nGlobal model ...")
    global_model = task.build_model(model_cfg, seed=SEED, device="cpu")
    global_model.load_state_dict(torch.load(entry["global_checkpoint"], map_location="cpu"))
    global_model.eval()
    eval_X_g = scale_rows(eval_X_raw, centralized_splits.scaler_center, centralized_splits.scaler_scale)
    bg_g = scale_rows(common_bg_raw, centralized_splits.scaler_center, centralized_splits.scaler_scale)
    sv, diff = explain(global_model, bg_g, eval_X_g)
    print(f"  additivity max diff: {diff:.4f}")
    svs["global"] = sv

    for silo_id in SILO_IDS:
        print(f"Silo {silo_id} ...")
        splits = task.load_silo_for_client(silo_id, ALPHA, SEED, data_cfg, model_cfg, class_weights)
        model = task.build_model(model_cfg, seed=SEED, device="cpu")
        model.load_state_dict(torch.load(entry["silo_checkpoints"][silo_id], map_location="cpu"))
        model.eval()
        eval_X_s = scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
        bg_s = scale_rows(common_bg_raw, splits.scaler_center, splits.scaler_scale)
        sv, diff = explain(model, bg_s, eval_X_s)
        print(f"  additivity max diff: {diff:.4f}")
        svs[f"silo_{silo_id}"] = sv

    print("\n" + "=" * 70)
    print("COMMON-BACKGROUND agreement (global vs each silo)")
    print("=" * 70)
    rows = []
    for silo_id in SILO_IDS:
        for i in range(len(eval_y)):
            true_class = int(eval_y[i])
            g = svs["global"][i, :, true_class]
            s = svs[f"silo_{silo_id}"][i, :, true_class]
            try:
                tau, _ = weightedtau(g, s)
            except Exception:
                tau = float("nan")
            row = {"silo": silo_id, "sample_idx": i, "family": eval_families[i],
                   "kendall_weighted_tau": tau}
            for k in K_VALUES:
                row[f"jaccard_at_{k}"] = jaccard_topk(g, s, k)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False)

    print("\nMedian, common background:")
    print(df[[f"jaccard_at_{k}" for k in K_VALUES] + ["kendall_weighted_tau"]].median().to_string())

    # Compare against the ORIGINAL (per-model own background) numbers for these same 3 silos
    orig = pd.read_csv(AGREEMENT_PATH)
    orig_subset = orig[(orig.alpha.astype(str) == ALPHA) & (orig.seed == SEED) & (orig.silo.isin(SILO_IDS))]
    print("\nMedian, ORIGINAL per-model background (same alpha/seed/silos, for comparison):")
    print(orig_subset[[f"jaccard_at_{k}" for k in K_VALUES] + ["kendall_weighted_tau"]].median().to_string())

    print(f"\nWritten: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
