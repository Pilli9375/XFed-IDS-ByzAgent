"""Does GradientExplainer's additivity error shrink with more background rows
and more interpolation samples? If yes, it's a sampling-precision issue we can
just budget for. If no, it points to something structural about explaining
through LayerNorm, and DeepExplainer/GradientExplainer are both off the table
as-is -- a real decision point, not a tuning knob.

Run from project root: python tools/shap_probe_scaling.py
"""
from __future__ import annotations

import json
import sys
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


def run_one(model, splits, n_bg: int, nsamples: int, n_explain: int = 5) -> float:
    rng = np.random.default_rng(0)
    n_bg = min(n_bg, len(splits.y_train))
    bg_idx = rng.choice(len(splits.y_train), size=n_bg, replace=False)
    background = torch.from_numpy(splits.X_train[bg_idx].copy())

    ex_idx = rng.choice(len(splits.y_train), size=n_explain, replace=False)
    explain_X = torch.from_numpy(splits.X_train[ex_idx].copy())

    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explain_X, nsamples=nsamples)
    sv = np.array(shap_values)

    with torch.no_grad():
        f_explain = model(explain_X).numpy()
        f_bg_mean = model(background).numpy().mean(axis=0)

    diff = sv.sum(axis=1) - (f_explain - f_bg_mean[None, :])
    return float(np.abs(diff).max())


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

    configs = [
        (50, 200),    # what we already ran (default nsamples)
        (150, 200),   # more background, same interpolation
        (150, 1000),  # more background AND more interpolation
        (200, 2000),  # push hard -- max background per locked decision 4
    ]

    print(f"{'n_background':<14}{'nsamples':<10}{'max_abs_diff'}")
    print("-" * 40)
    results = []
    for n_bg, nsamples in configs:
        max_diff = run_one(model, splits, n_bg, nsamples)
        print(f"{n_bg:<14}{nsamples:<10}{max_diff:.4f}")
        results.append(max_diff)

    print()
    if results[-1] < 0.1 and results[-1] < results[0] * 0.3:
        print("Error shrinks substantially with more sampling -- this is a "
              "precision/budget issue, not a structural one. GradientExplainer "
              "with a larger nsamples is viable.")
    elif results[-1] < results[0] * 0.5:
        print("Error shrinks somewhat but doesn't converge cleanly -- ambiguous. "
              "Report these numbers back before deciding.")
    else:
        print("Error does NOT meaningfully shrink with more sampling -- this "
              "looks structural (likely LayerNorm), not a sampling budget "
              "problem. Report these numbers back -- this is the real decision "
              "point about whether KernelExplainer needs to be primary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
