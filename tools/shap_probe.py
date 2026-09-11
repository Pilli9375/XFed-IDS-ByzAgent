"""SHAP explainer probe -- verify DeepExplainer handles this model's LayerNorm
layers before building the full local-SHAP pipeline on top of it.

This has been flagged as unverified since the start of Chat 04. Check now,
on a real checkpoint and real silo data, rather than assuming and finding
out after more code depends on it.

Run from project root: python tools/shap_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "federated")  # xfed_federated lives under federated/

import numpy as np
import torch

from xfed_federated import task  # noqa: E402

# A well-behaved config for the probe -- not the point of interest itself,
# just needs to be a real trained checkpoint.
PROBE_ALPHA = "0.5"
PROBE_SEED = 42
PROBE_SILO = 0

MANIFEST_PATH = Path("results/inspection/best_rounds_manifest.json")


def check_additivity(model, background: torch.Tensor, explain_X: torch.Tensor, shap_values) -> None:
    """shap_values should sum (per class, per sample) to f(x) - E[f(background)].
    Print shapes and both sides rather than assume a layout -- shap's return
    shape varies by version and by single-output vs multi-output models.
    """
    with torch.no_grad():
        f_explain = model(explain_X).numpy()
        f_background_mean = model(background).numpy().mean(axis=0)

    sv = np.array(shap_values)
    print(f"\nshap_values array shape: {sv.shape}")
    print(f"f(explain) shape: {f_explain.shape}, sample[0][:3]: {f_explain[0][:3]}")
    print(f"E[f(background)] shape: {f_background_mean.shape}, [:3]: {f_background_mean[:3]}")
    print("(Compare these by eye for now -- exact axis alignment gets nailed "
          "down once we know which explainer we're using and its real shap version.)")


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    print(f"Loading silo {PROBE_SILO} data for alpha={PROBE_ALPHA}, seed={PROBE_SEED} ...")
    splits = task.load_silo_for_client(
        PROBE_SILO, PROBE_ALPHA, PROBE_SEED, data_cfg, model_cfg, class_weights
    )
    print(splits.summary())

    tag = f"fedavg_a{PROBE_ALPHA}_s{PROBE_SEED}"
    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = next((e for e in manifest if e["tag"] == tag), None)
    if entry is None:
        print(f"Tag {tag} not found in manifest. Something drifted -- stop and check.")
        return 1

    ckpt_path = entry["silo_checkpoints"][PROBE_SILO]
    print(f"R* = {entry['best_round']}, loading checkpoint: {ckpt_path}")

    model = task.build_model(model_cfg, seed=PROBE_SEED, device="cpu")
    state_dict = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    print("Checkpoint loaded into fresh model -- state_dict keys matched cleanly.")

    rng = np.random.default_rng(0)
    n_bg = min(50, len(splits.y_train))
    bg_idx = rng.choice(len(splits.y_train), size=n_bg, replace=False)
    background = torch.from_numpy(splits.X_train[bg_idx].copy())

    n_explain = 5
    ex_idx = rng.choice(len(splits.y_train), size=n_explain, replace=False)
    explain_X = torch.from_numpy(splits.X_train[ex_idx].copy())

    print(f"\nBackground: {tuple(background.shape)}, explain set: {tuple(explain_X.shape)}")

    try:
        import shap
    except ImportError:
        print("\nshap is not installed in this environment.")
        print("Run: pip install shap")
        print("Then re-run this script.")
        return 1
    print(f"shap version: {shap.__version__}")

    print("\n--- Attempting shap.DeepExplainer ---")
    try:
        explainer = shap.DeepExplainer(model, background)
        shap_values = explainer.shap_values(explain_X)
        print("DeepExplainer ran without raising.")
        check_additivity(model, background, explain_X, shap_values)
        print("\nVERDICT: DeepExplainer works on this model. Use it as primary.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"DeepExplainer FAILED: {type(e).__name__}: {e}")

    print("\n--- Falling back: attempting shap.GradientExplainer ---")
    try:
        explainer = shap.GradientExplainer(model, background)
        shap_values = explainer.shap_values(explain_X)
        print("GradientExplainer ran without raising.")
        check_additivity(model, background, explain_X, shap_values)
        print("\nVERDICT: DeepExplainer failed, GradientExplainer works. Use GradientExplainer as primary.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"GradientExplainer ALSO FAILED: {type(e).__name__}: {e}")
        print("\nVERDICT: Neither fast explainer works out of the box.")
        print("Paste this full output back -- do not fall through to KernelExplainer "
              "as primary without discussing the timeline cost first.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
