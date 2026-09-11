"""Follow-up to shap_probe.py: GradientExplainer doesn't self-check additivity
the way DeepExplainer does, so compute it ourselves before trusting the
'ran without raising' result as a pass.

Run from project root: python tools/shap_probe_additivity.py
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

    rng = np.random.default_rng(0)
    n_bg = min(50, len(splits.y_train))
    bg_idx = rng.choice(len(splits.y_train), size=n_bg, replace=False)
    background = torch.from_numpy(splits.X_train[bg_idx].copy())

    n_explain = 5
    ex_idx = rng.choice(len(splits.y_train), size=n_explain, replace=False)
    explain_X = torch.from_numpy(splits.X_train[ex_idx].copy())

    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explain_X)
    sv = np.array(shap_values)  # (n_explain, n_features, n_classes)

    with torch.no_grad():
        f_explain = model(explain_X).numpy()          # (n_explain, n_classes)
        f_bg_mean = model(background).numpy().mean(axis=0)  # (n_classes,)

    attribution_sum = sv.sum(axis=1)  # sum over features -> (n_explain, n_classes)
    expected = f_explain - f_bg_mean[None, :]
    diff = attribution_sum - expected

    print(f"shap_values shape: {sv.shape}")
    print(f"attribution_sum shape: {attribution_sum.shape}")
    print(f"\nPer-sample, per-class additivity diff (should be near 0):")
    print(f"  max abs diff : {np.abs(diff).max():.6f}")
    print(f"  mean abs diff: {np.abs(diff).max():.6f}")
    print(f"  per-sample max diff: {np.abs(diff).max(axis=1)}")

    tolerance = 0.05  # looser than DeepExplainer's 0.01 -- GradientExplainer
                       # is an expected-gradients approximation, not exact
    if np.abs(diff).max() < tolerance:
        print(f"\nPASS: max diff {np.abs(diff).max():.4f} < tolerance {tolerance}")
        print("GradientExplainer's attributions are consistent with the model's actual output change.")
        return 0
    else:
        print(f"\nFAIL: max diff {np.abs(diff).max():.4f} >= tolerance {tolerance}")
        print("GradientExplainer attributions do not reliably sum to the output change.")
        print("Report this back before proceeding -- may need more background samples "
              "or a different nsamples setting for the gradient estimate.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
