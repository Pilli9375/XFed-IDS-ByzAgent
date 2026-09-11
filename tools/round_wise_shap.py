"""Compute SHAP values at rounds 5, 10, 15, 20 (not just the best-by-validation
round) so round_wise_agreement.py can measure whether explanation consistency
converges at the same rate as accuracy, or lags it.

REDUCED FIDELITY, THIS PASS ONLY: nsamples=1000 (headline pipeline uses 4000).
Approved 2026-08-24 in 01_Planning to keep runtime under ~4 hours while
covering all 9 configs x 4 rounds x 11 models (no coverage was cut -- same 14
fixed eval rows, same 9 configs, same background construction). Do not cite
these SHAP values or downstream jaccard/tau against the headline numbers in
results/shap/<tag>/*.npz -- those used nsamples=4000. This script writes to a
separate round_wise/ subfolder per tag and never touches the headline files.

Reuses (does not reimplement) tools/local_shap_pipeline.py: same fixed eval
set (EVAL_SEED=12345), same class-stratified background construction, same
GradientExplainer wrapper. Only the checkpoint loaded per model changes --
one checkpoint per round instead of the single best-round checkpoint.

Data loading (centralized split / each silo's split, scaler, background) is
round-invariant -- only model weights change across rounds -- so it happens
once per config, not once per (config, round).

Import-order note: importing torch directly before importing
local_shap_pipeline caused a native crash (0xC0000005) on this machine.
local_shap_pipeline.py's own import order (pyarrow -> shap -> torch) is
known-good, so it is imported first here and its already-imported `torch`/
`task` are reused rather than importing them again ourselves.

Run from project root: python tools/round_wise_shap.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "tools")
import local_shap_pipeline as lsp  # noqa: E402  (see import-order note above)

torch = lsp.torch
task = lsp.task
np = lsp.np

NSAMPLES_REDUCED = 1000
ROUNDS = [5, 10, 15, 20]

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")
OUT_ROOT = Path("results/shap")


def run_round(alpha: str, seed: int, round_num: int, model_cfg: dict,
              bg_global, bg_silos: dict,
              eval_X_global_scaled, eval_X_silo_scaled: dict,
              eval_y, eval_families, ckpt_dir: Path, out_dir: Path) -> None:
    round_dir = out_dir / f"round_{round_num:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)

    global_model = task.build_model(model_cfg, seed=seed, device="cpu")
    global_model.load_state_dict(
        torch.load(ckpt_dir / "round_checkpoints" / f"round_{round_num:03d}.pt", map_location="cpu")
    )
    global_model.eval()
    sv_global, diff_global, t_global = lsp.explain_one_model(global_model, bg_global, eval_X_global_scaled)
    np.savez(round_dir / "global_shap.npz", shap_values=sv_global, eval_y=eval_y,
             eval_families=eval_families, additivity_max_diff=diff_global,
             background_size=len(bg_global), nsamples=NSAMPLES_REDUCED)
    print(f"    global  additivity_diff={diff_global:.4f}  ({t_global:.1f}s)")

    for silo_id in range(10):
        model = task.build_model(model_cfg, seed=seed, device="cpu")
        state_dict = torch.load(
            ckpt_dir / "silo_checkpoints" / f"round_{round_num:03d}_silo_{silo_id}.pt", map_location="cpu"
        )
        model.load_state_dict(state_dict)
        model.eval()
        sv, diff, t_elapsed = lsp.explain_one_model(model, bg_silos[silo_id], eval_X_silo_scaled[silo_id])
        np.savez(round_dir / f"silo_{silo_id}_shap.npz", shap_values=sv, eval_y=eval_y,
                 eval_families=eval_families, additivity_max_diff=diff,
                 background_size=len(bg_silos[silo_id]), nsamples=NSAMPLES_REDUCED)
    print(f"    10 silos done")


def run_config(alpha: str, seed: int, model_cfg: dict, data_cfg: dict,
                eval_X_raw, eval_y, eval_families) -> None:
    tag = f"fedavg_a{alpha}_s{seed}"
    print(f"\n{'='*70}\n{tag}\n{'='*70}")
    ckpt_dir = Path(f"results/federated/{tag}")
    out_dir = OUT_ROOT / tag / "round_wise"

    class_weights = task.load_global_class_weights(model_cfg)

    # --- Round-invariant setup: scaler + background, once per config ---
    centralized_splits = task.load_centralized_for_server(data_cfg, model_cfg)
    eval_X_global_scaled = lsp.scale_rows(eval_X_raw, centralized_splits.scaler_center, centralized_splits.scaler_scale)
    bg_idx_global = lsp.build_stratified_background(
        centralized_splits.X_train, centralized_splits.y_train, lsp.BACKGROUND_TARGET, lsp.BACKGROUND_SEED_BASE
    )
    bg_global = centralized_splits.X_train[bg_idx_global]

    bg_silos = {}
    eval_X_silo_scaled = {}
    for silo_id in range(10):
        splits = task.load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)
        eval_X_silo_scaled[silo_id] = lsp.scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
        bg_idx = lsp.build_stratified_background(
            splits.X_train, splits.y_train, lsp.BACKGROUND_TARGET, lsp.BACKGROUND_SEED_BASE + silo_id + 1
        )
        bg_silos[silo_id] = splits.X_train[bg_idx]

    for round_num in ROUNDS:
        print(f"  round {round_num} ...")
        run_round(alpha, seed, round_num, model_cfg,
                   bg_global, bg_silos, eval_X_global_scaled, eval_X_silo_scaled,
                   eval_y, eval_families, ckpt_dir, out_dir)


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")

    n_per_class = max(1, lsp.N_EVAL_ROWS // len(model_cfg["labels"]["headline_classes"]))
    eval_X_raw, eval_y, eval_families, feature_cols = lsp.load_fixed_eval_rows(
        data_cfg, model_cfg, n_per_headline_class=n_per_class
    )

    manifest = json.loads(MANIFEST_PATH.read_text())
    configs = [(e["alpha"], e["seed"]) for e in manifest]

    overall_start = time.time()
    for alpha, seed in configs:
        run_config(alpha, seed, model_cfg, data_cfg, eval_X_raw, eval_y, eval_families)

    total_min = (time.time() - overall_start) / 60
    print(f"\nTotal time: {total_min:.1f} min ({total_min/60:.2f} hr)")
    print(f"nsamples used: {NSAMPLES_REDUCED} (reduced fidelity, headline pipeline uses 4000)")
    return 0


if __name__ == "__main__":
    lsp.NSAMPLES = NSAMPLES_REDUCED
    raise SystemExit(main())
