"""Extended convergence check -- push nsamples further and time each run, so
we know both (a) whether GradientExplainer actually converges toward zero
additivity error, and (b) what that costs in wall-clock, before deciding
anything for the full 90-(config,silo) pipeline.

Run from project root: python tools/shap_probe_scaling_extended.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "federated")

import numpy as np
import shap
import torch

from xfed_federated import task  # noqa: E402

PROBE_ALPHA = "0.5"
PROBE_SEED = 42
PROBE_SILO = 0
MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")


def run_one(model, splits, n_bg: int, nsamples: int, n_explain: int = 5, seed: int = 0):
    rng = np.random.default_rng(seed)
    n_bg = min(n_bg, len(splits.y_train))
    bg_idx = rng.choice(len(splits.y_train), size=n_bg, replace=False)
    background = torch.from_numpy(splits.X_train[bg_idx].copy())

    ex_idx = rng.choice(len(splits.y_train), size=n_explain, replace=False)
    explain_X = torch.from_numpy(splits.X_train[ex_idx].copy())

    t0 = time.time()
    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explain_X, nsamples=nsamples)
    elapsed = time.time() - t0

    sv = np.array(shap_values)
    with torch.no_grad():
        f_explain = model(explain_X).numpy()
        f_bg_mean = model(background).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_explain - f_bg_mean[None, :])
    return float(np.abs(diff).max()), elapsed


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    splits = task.load_silo_for_client(
        PROBE_SILO, PROBE_ALPHA, PROBE_SEED, data_cfg, model_cfg, class_weights
    )

    tag = f"fedavg_a{PROBE_ALPHA}_s{PROBE_SEED}"
    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = next(e for e in manifest if e["tag"] == tag)
    ckpt_path = entry["silo_checkpoints"][PROBE_SILO]

    model = task.build_model(model_cfg, seed=PROBE_SEED, device="cpu")
    model.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
    model.eval()

    # Push well past where the previous probe stopped. 200 background is the
    # locked ceiling (decision 4) -- fixed here, only nsamples increases.
    configs = [2000, 4000, 8000, 16000]

    print(f"{'nsamples':<10}{'max_abs_diff':<15}{'seconds_for_5_samples'}")
    print("-" * 50)
    results = []
    for nsamples in configs:
        max_diff, elapsed = run_one(model, splits, n_bg=200, nsamples=nsamples)
        print(f"{nsamples:<10}{max_diff:<15.4f}{elapsed:.1f}")
        results.append((nsamples, max_diff, elapsed))

    print()
    # Check convergence shape: does halving-the-gap-per-doubling hold?
    print("Ratio check (expected ~0.71 per doubling if pure sqrt(n) sampling noise):")
    for i in range(1, len(results)):
        prev_diff = results[i - 1][1]
        curr_diff = results[i][1]
        ratio = curr_diff / prev_diff if prev_diff > 0 else float("nan")
        print(f"  {results[i-1][0]} -> {results[i][0]}: ratio = {ratio:.3f}")

    final_diff = results[-1][1]
    final_time = results[-1][2]
    per_row_cost = final_time / 5  # seconds per explained row at nsamples=16000

    print(f"\nFinal max diff at nsamples={configs[-1]}: {final_diff:.4f}")
    print(f"Cost: ~{per_row_cost:.2f} sec/explained-row at nsamples={configs[-1]}")
    # Rough full-pipeline cost estimate: 9 configs x 10 silos x however many
    # rows you explain per silo. Print at a couple of candidate row counts.
    for n_rows in (50, 100, 200):
        total_sec = per_row_cost * n_rows * 10 * 9
        print(f"  Full pipeline estimate at {n_rows} explained rows/silo, "
              f"90 (config,silo) pairs: ~{total_sec/60:.1f} minutes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
