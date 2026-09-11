"""Centralized-seed instability floor -- pairwise SHAP agreement between the
3 centralized baseline models (seeds 42, 1337, 2024). No federation involved
at all here -- this is the null the federated agreement trend gets compared
against. If federated silo-vs-global agreement at some alpha sits at or
below this floor, the "federation effect" isn't distinguishable from plain
seed-to-seed noise.

Same fixed eval rows, same class-stratified 200-row background, same
GradientExplainer settings (nsamples=4000) as the federated pipeline, so the
comparison is fair -- only the scaler differs (centralized, not per-silo,
because these models never saw per-silo data).

Run from project root: python tools/centralized_shap_floor.py
"""
from __future__ import annotations

import sys
import time
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

NSAMPLES = 4000
BACKGROUND_TARGET = 200
BACKGROUND_SEED_BASE = 999
SEEDS = [42, 1337, 2024]
K_VALUES = (5, 10, 20)

CKPT_DIR = Path("results/centralized")
DATA_ROOT = Path("data/processed")
OUT_DIR = Path("results/shap/centralized")
INSTABILITY_OUT = Path("results/inspection/centralized_instability_floor.csv")


def build_stratified_background(X: np.ndarray, y: np.ndarray, target_total: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    classes = np.unique(y)
    class_idx = {c: np.where(y == c)[0] for c in classes}
    base = max(1, target_total // len(classes))
    chosen: dict[int, np.ndarray] = {}
    used = 0
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


def load_fixed_eval_rows(data_cfg: dict, model_cfg: dict, n_per_class: int = 2):
    """Same fixed rows the federated pipeline used -- same EVAL_SEED, same
    per-headline-class count -- so the eval set is identical across both.
    """
    test_path = DATA_ROOT / "test_global.parquet"
    columns = list(pq.ParquetFile(test_path).schema_arrow.names)
    feature_cols = derive_feature_cols(columns, data_cfg)
    df = pd.read_parquet(test_path, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)
    vocab = load_label_vocabulary(model_cfg)
    headline = model_cfg["labels"]["headline_classes"]

    picked_X, picked_fam = [], []
    for fam in headline:
        fam_df = df[df.family == fam]
        n = min(n_per_class, len(fam_df))
        s = fam_df.sample(n=n, random_state=EVAL_SEED)
        picked_X.append(s[feature_cols].to_numpy(np.float32))
        picked_fam.extend([fam] * n)

    X_raw = np.concatenate(picked_X, axis=0)
    y = np.array([vocab[f] for f in picked_fam], dtype=np.int64)
    print(f"Fixed eval set: {X_raw.shape[0]} rows across {len(headline)} headline families")
    return X_raw, y, picked_fam


def scale_rows(X_raw: np.ndarray, center: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return ((X_raw - center) / scale).astype(np.float32)


def explain(model, background_X: np.ndarray, eval_X_scaled: np.ndarray):
    bt = torch.from_numpy(background_X.copy())
    et = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, bt)
    sv = np.array(explainer.shap_values(et, nsamples=NSAMPLES))
    with torch.no_grad():
        f_eval = model(et).numpy()
        f_bg = model(bt).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_eval - f_bg[None, :])
    return sv, float(np.abs(diff).max())


def load_checkpoint(model: torch.nn.Module, path: Path) -> torch.nn.Module:
    """Tries plain state_dict first, then common wrapper patterns. Fails
    loudly with the actual keys found, rather than guessing silently.
    """
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and all(isinstance(v, torch.Tensor) for v in obj.values()):
        model.load_state_dict(obj)
        return model
    if isinstance(obj, dict) and "state_dict" in obj:
        model.load_state_dict(obj["state_dict"])
        return model
    if isinstance(obj, dict) and "model_state_dict" in obj:
        model.load_state_dict(obj["model_state_dict"])
        return model
    keys = list(obj.keys()) if isinstance(obj, dict) else type(obj)
    raise ValueError(f"Unrecognized checkpoint format at {path}: {keys}")


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")

    splits = task.load_centralized_for_server(data_cfg, model_cfg)
    n_per_class = max(1, N_EVAL_ROWS // len(model_cfg["labels"]["headline_classes"]))
    eval_X_raw, eval_y, eval_families = load_fixed_eval_rows(data_cfg, model_cfg, n_per_class=n_per_class)
    eval_X_scaled = scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    seed_svs: dict[int, np.ndarray] = {}
    for seed in SEEDS:
        ckpt_path = CKPT_DIR / f"baseline_s{seed}" / "model.pt"
        print(f"\nExplaining centralized seed {seed} (checkpoint: {ckpt_path}) ...")
        model = task.build_model(model_cfg, seed=seed, device="cpu")
        model = load_checkpoint(model, ckpt_path)
        model.eval()

        bg_idx = build_stratified_background(
            splits.X_train, splits.y_train, BACKGROUND_TARGET, BACKGROUND_SEED_BASE + seed
        )
        bg = splits.X_train[bg_idx]

        t0 = time.time()
        sv, diff = explain(model, bg, eval_X_scaled)
        print(f"  additivity max diff: {diff:.4f}  ({time.time()-t0:.1f}s)  bg_size={len(bg_idx)}")

        np.savez(OUT_DIR / f"seed_{seed}_shap.npz", shap_values=sv, eval_y=eval_y,
                 eval_families=eval_families, additivity_max_diff=diff)
        seed_svs[seed] = sv

    print("\n" + "=" * 70)
    print("PAIRWISE CENTRALIZED-SEED AGREEMENT (the instability floor)")
    print("=" * 70)
    pairs = [(42, 1337), (42, 2024), (1337, 2024)]
    rows = []
    for s1, s2 in pairs:
        sv1, sv2 = seed_svs[s1], seed_svs[s2]
        for i in range(len(eval_y)):
            true_class = int(eval_y[i])
            a = sv1[i, :, true_class]
            b = sv2[i, :, true_class]
            try:
                tau, _ = weightedtau(a, b)
            except Exception:  # noqa: BLE001
                tau = float("nan")
            row = {"seed_pair": f"{s1}-{s2}", "sample_idx": i,
                   "family": eval_families[i], "kendall_weighted_tau": tau}
            for k in K_VALUES:
                top_a = set(np.argsort(-np.abs(a))[:k])
                top_b = set(np.argsort(-np.abs(b))[:k])
                union = top_a | top_b
                row[f"jaccard_at_{k}"] = len(top_a & top_b) / len(union) if union else float("nan")
            rows.append(row)

    df = pd.DataFrame(rows)
    INSTABILITY_OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(INSTABILITY_OUT, index=False)

    print("\nMedian across all seed-pairs (the floor to compare federated agreement against):")
    print(df[[f"jaccard_at_{k}" for k in K_VALUES] + ["kendall_weighted_tau"]].median().to_string())
    print("\nPer seed-pair median:")
    print(df.groupby("seed_pair")[[f"jaccard_at_{k}" for k in K_VALUES] + ["kendall_weighted_tau"]].median().to_string())
    print(f"\nWritten: {INSTABILITY_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
