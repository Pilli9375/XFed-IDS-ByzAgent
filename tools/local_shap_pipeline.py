"""Local SHAP pipeline -- one config at a time, all 10 silos + global model.

Implements two locked requirements the probes skipped:
  1. Class-stratified background (decision 4), not uniform random.
  2. A FIXED shared eval row set, explained by every silo's model AND the
     global model, each with its own scaler applied to the same raw rows.
     This controls the confound: differences in explanations must reflect
     differences in the MODELS, not differences in which rows got explained.

Usage:
  python tools/local_shap_pipeline.py --alpha 0.5 --seed 42
  python tools/local_shap_pipeline.py --all     # all 9 configs, ~3.7hr total

For a non-FedAvg sweep (e.g. FedProx) sharing the same alpha/seed grid
but a different result-dir prefix and manifest, pass --tag-prefix and
--manifest -- output naturally lands under results/shap/<tag>/ so it
never collides with the FedAvg output:
  python tools/local_shap_pipeline.py --all --tag-prefix fedprox_mu0.0005 \\
      --manifest results/inspection/best_rounds_manifest_fedprox_mu0.0005.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "federated")

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shap
import torch

from xfed_federated import task  # noqa: E402
from xfed_federated._vendored.schema import derive_feature_cols, encode_families, load_label_vocabulary  # noqa: E402

from eval_set_config import N_EVAL_ROWS, EVAL_SEED  # noqa: E402

NSAMPLES = 4000
BACKGROUND_TARGET = 200
BACKGROUND_SEED_BASE = 777

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
DATA_ROOT = Path("data/processed")
OUT_ROOT = Path("results/shap")


def build_stratified_background(X: np.ndarray, y: np.ndarray, target_total: int, seed: int) -> np.ndarray:
    """Balanced-with-floor stratified sample. Each present class gets an equal
    share of the budget where available; leftover budget (from classes with
    fewer rows than their share) is redistributed round-robin to classes that
    still have spare rows, until target_total is hit or everyone's exhausted.
    """
    rng = np.random.default_rng(seed)
    classes = np.unique(y)
    class_idx = {c: np.where(y == c)[0] for c in classes}
    base = max(1, target_total // len(classes))

    chosen: dict[int, np.ndarray] = {}
    used = 0
    for c in classes:
        avail = class_idx[c]
        take = min(base, len(avail))
        pick = rng.choice(avail, size=take, replace=False)
        chosen[c] = pick
        used += take

    remaining = target_total - used
    if remaining > 0:
        classes_with_room = [c for c in classes if len(class_idx[c]) > len(chosen[c])]
        while remaining > 0 and classes_with_room:
            for c in list(classes_with_room):
                if remaining <= 0:
                    break
                avail = class_idx[c]
                already = set(chosen[c].tolist())
                pool = np.array([i for i in avail if i not in already])
                if len(pool) == 0:
                    classes_with_room.remove(c)
                    continue
                extra = rng.choice(pool, size=1, replace=False)
                chosen[c] = np.concatenate([chosen[c], extra])
                remaining -= 1
                if len(pool) == 1:
                    classes_with_room.remove(c)

    all_idx = np.concatenate(list(chosen.values()))
    rng.shuffle(all_idx)
    return all_idx


def load_fixed_eval_rows(data_cfg: dict, model_cfg: dict, n_per_headline_class: int = 3):
    """One fixed set of RAW (unscaled) rows from the centralized test set,
    stratified across the 7 headline families, seeded once and reused for
    every config -- the same physical rows, every time.
    """
    test_path = DATA_ROOT / "test_global.parquet"
    columns = list(pq.ParquetFile(test_path).schema_arrow.names)
    feature_cols = derive_feature_cols(columns, data_cfg)
    df = pd.read_parquet(test_path, columns=feature_cols + ["family"])
    df[feature_cols] = df[feature_cols].astype(np.float32)

    vocab = load_label_vocabulary(model_cfg)
    headline_families = model_cfg["labels"]["headline_classes"]

    rng = np.random.default_rng(EVAL_SEED)
    picked_rows = []
    picked_families = []
    for fam in headline_families:
        fam_df = df[df["family"] == fam]
        n = min(n_per_headline_class, len(fam_df))
        sample = fam_df.sample(n=n, random_state=EVAL_SEED)
        picked_rows.append(sample[feature_cols].to_numpy(np.float32))
        picked_families.extend([fam] * n)

    X_raw = np.concatenate(picked_rows, axis=0)
    y_encoded = np.array([vocab[f] for f in picked_families], dtype=np.int64)
    print(f"Fixed eval set: {X_raw.shape[0]} rows across {len(headline_families)} "
          f"headline families (target {n_per_headline_class}/class)")
    return X_raw, y_encoded, picked_families, feature_cols


def scale_rows(X_raw: np.ndarray, center: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return ((X_raw - center) / scale).astype(np.float32)


def explain_one_model(model, background_X: np.ndarray, eval_X_scaled: np.ndarray):
    background_t = torch.from_numpy(background_X.copy())
    eval_t = torch.from_numpy(eval_X_scaled.copy())

    t0 = time.time()
    explainer = shap.GradientExplainer(model, background_t)
    shap_values = explainer.shap_values(eval_t, nsamples=NSAMPLES)
    elapsed = time.time() - t0

    sv = np.array(shap_values)
    with torch.no_grad():
        f_eval = model(eval_t).numpy()
        f_bg_mean = model(background_t).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_eval - f_bg_mean[None, :])
    max_additivity_diff = float(np.abs(diff).max())

    return sv, max_additivity_diff, elapsed


def run_config(alpha: str, seed: int, model_cfg: dict, data_cfg: dict,
                eval_X_raw: np.ndarray, eval_y: np.ndarray, eval_families: list,
                tag_prefix: str, manifest_path: Path):
    tag = f"{tag_prefix}_a{alpha}_s{seed}"
    print(f"\n{'='*70}\n{tag}\n{'='*70}")

    manifest = json.loads(manifest_path.read_text())
    entry = next(e for e in manifest if e["tag"] == tag)
    r_star = entry["best_round"]

    out_dir = OUT_ROOT / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    class_weights = task.load_global_class_weights(model_cfg)

    # --- Global model ---
    print(f"Global model (R*={r_star}) ...")
    centralized_splits = task.load_centralized_for_server(data_cfg, model_cfg)
    global_model = task.build_model(model_cfg, seed=seed, device="cpu")
    global_model.load_state_dict(torch.load(entry["global_checkpoint"], map_location="cpu"))
    global_model.eval()

    eval_X_global_scaled = scale_rows(eval_X_raw, centralized_splits.scaler_center, centralized_splits.scaler_scale)
    bg_idx_global = build_stratified_background(
        centralized_splits.X_train, centralized_splits.y_train, BACKGROUND_TARGET, BACKGROUND_SEED_BASE
    )
    bg_global = centralized_splits.X_train[bg_idx_global]

    sv_global, diff_global, t_global = explain_one_model(global_model, bg_global, eval_X_global_scaled)
    print(f"  additivity max diff: {diff_global:.4f}  ({t_global:.1f}s)")
    np.savez(out_dir / "global_shap.npz", shap_values=sv_global, eval_y=eval_y,
             eval_families=eval_families, additivity_max_diff=diff_global,
             background_size=len(bg_idx_global))

    # --- Each silo ---
    for silo_id in range(10):
        print(f"Silo {silo_id} ...", end=" ", flush=True)
        splits = task.load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)

        model = task.build_model(model_cfg, seed=seed, device="cpu")
        state_dict = torch.load(entry["silo_checkpoints"][silo_id], map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()

        eval_X_scaled = scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
        bg_idx = build_stratified_background(
            splits.X_train, splits.y_train, BACKGROUND_TARGET, BACKGROUND_SEED_BASE + silo_id + 1
        )
        bg = splits.X_train[bg_idx]

        sv, diff, t_elapsed = explain_one_model(model, bg, eval_X_scaled)
        print(f"additivity max diff: {diff:.4f}  ({t_elapsed:.1f}s)  bg_size={len(bg_idx)}")

        np.savez(out_dir / f"silo_{silo_id}_shap.npz", shap_values=sv, eval_y=eval_y,
                 eval_families=eval_families, additivity_max_diff=diff,
                 background_size=len(bg_idx))

    print(f"Done: {tag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=str, help="e.g. 0.5")
    ap.add_argument("--seed", type=int, help="e.g. 42")
    ap.add_argument("--all", action="store_true", help="run all 9 configs")
    ap.add_argument("--tag-prefix", default="fedavg",
                     help="result-dir tag prefix, e.g. 'fedavg' or 'fedprox_mu0.0005' (default: fedavg)")
    ap.add_argument("--manifest", type=Path, default=MANIFEST_PATH,
                     help="best-rounds manifest to read (default: results/inspection/best_rounds_manifest.json)")
    args = ap.parse_args()

    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")

    n_per_class = max(1, N_EVAL_ROWS // len(model_cfg["labels"]["headline_classes"]))
    eval_X_raw, eval_y, eval_families, feature_cols = load_fixed_eval_rows(
        data_cfg, model_cfg, n_per_headline_class=n_per_class
    )

    if args.all:
        configs = [("0.1", 42), ("0.1", 1337), ("0.1", 2024),
                   ("0.5", 42), ("0.5", 1337), ("0.5", 2024),
                   ("5.0", 42), ("5.0", 1337), ("5.0", 2024)]
    elif args.alpha and args.seed:
        configs = [(args.alpha, args.seed)]
    else:
        print("Specify --alpha X --seed Y for one config, or --all for the full sweep.")
        return 1

    overall_start = time.time()
    for alpha, seed in configs:
        run_config(alpha, seed, model_cfg, data_cfg, eval_X_raw, eval_y, eval_families,
                   tag_prefix=args.tag_prefix, manifest_path=args.manifest)

    total_min = (time.time() - overall_start) / 60
    print(f"\nTotal time: {total_min:.1f} min ({total_min/60:.2f} hr)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
