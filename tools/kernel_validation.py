"""KernelExplainer spot-check: does the fast approximate explainer
(GradientExplainer, already used for all 90 config-silo pairs) agree in
RANKING with a slow, closer-to-exact Shapley method, on the same model and
the same rows?

One silo only (alpha=0.5, seed=42, silo 0 -- already explained via
GradientExplainer, output on disk). KernelExplainer is model-agnostic and
does not touch LayerNorm at all -- no op-coverage risk -- but it is far
slower, so background is summarized via shap.kmeans (SHAP's own recommended
approach for KernelExplainer) rather than using the full 200-row background.

Run from project root: python tools/kernel_validation.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "federated")

import numpy as np
import shap
import torch
from scipy.stats import weightedtau

from xfed_federated import task  # noqa: E402

from eval_set_config import N_EVAL_ROWS, EVAL_SEED  # noqa: E402

PROBE_ALPHA = "0.5"
PROBE_SEED = 42
PROBE_SILO = 0
K_VALUES = (5, 10, 20)
KMEANS_K = 25       # background summarized to 25 representative points
KERNEL_NSAMPLES = 500

SHAP_DIR = Path(f"results/shap/fedavg_a{PROBE_ALPHA}_s{PROBE_SEED}")


def jaccard_topk(a: np.ndarray, b: np.ndarray, k: int) -> float:
    top_a = set(np.argsort(-np.abs(a))[:k])
    top_b = set(np.argsort(-np.abs(b))[:k])
    union = top_a | top_b
    return len(top_a & top_b) / len(union) if union else float("nan")


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    splits = task.load_silo_for_client(
        PROBE_SILO, PROBE_ALPHA, PROBE_SEED, data_cfg, model_cfg, class_weights
    )

    import json
    manifest = json.loads(Path("results/inspection/best_rounds_manifest.json").read_text())
    tag = f"fedavg_a{PROBE_ALPHA}_s{PROBE_SEED}"
    entry = next(e for e in manifest if e["tag"] == tag)

    model = task.build_model(model_cfg, seed=PROBE_SEED, device="cpu")
    model.load_state_dict(torch.load(entry["silo_checkpoints"][PROBE_SILO], map_location="cpu"))
    model.eval()

    # Load the already-computed GradientExplainer output for this exact silo
    gexp = np.load(SHAP_DIR / f"silo_{PROBE_SILO}_shap.npz", allow_pickle=True)
    grad_sv = gexp["shap_values"]          # (n_eval, 82, 9)
    eval_y = gexp["eval_y"]
    eval_families = list(gexp["eval_families"])
    n_eval = grad_sv.shape[0]
    print(f"Loaded existing GradientExplainer output: {n_eval} eval rows")

    # Rebuild the SAME fixed eval set + apply THIS silo's scaler, to get the
    # scaled inputs KernelExplainer needs (not saved earlier, only shap_values were)
    import pandas as pd
    import pyarrow.parquet as pq
    from xfed_federated._vendored.schema import derive_feature_cols, load_label_vocabulary

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
    eval_X_raw = np.concatenate(picked_X, axis=0)
    assert picked_fam == eval_families, "Eval set reconstruction mismatch -- stop and report this."

    eval_X_scaled = ((eval_X_raw - splits.scaler_center) / splits.scaler_scale).astype(np.float32)

    # Summarize background for KernelExplainer (full 200 rows would be far too slow)
    print(f"Summarizing background to {KMEANS_K} points via shap.kmeans ...")
    background_summary = shap.kmeans(splits.X_train, KMEANS_K)

    def f(x_np):
        with torch.no_grad():
            return model(torch.from_numpy(x_np.astype(np.float32))).numpy()

    print(f"Running KernelExplainer (nsamples={KERNEL_NSAMPLES}) on {n_eval} rows ...")
    print("This is the slow one -- expect several minutes.")
    t0 = time.time()
    explainer = shap.KernelExplainer(f, background_summary)
    kernel_sv = explainer.shap_values(eval_X_scaled, nsamples=KERNEL_NSAMPLES, silent=True)
    kernel_sv = np.array(kernel_sv)
    # shap.KernelExplainer multi-output shape can be (n_classes, n, features) or (n, features, n_classes)
    if kernel_sv.shape[0] == 9:  # (n_classes, n, features) -> transpose to (n, features, n_classes)
        kernel_sv = np.transpose(kernel_sv, (1, 2, 0))
    elapsed = time.time() - t0
    print(f"KernelExplainer finished in {elapsed:.1f}s ({elapsed/n_eval:.1f} sec/row)")
    print(f"kernel_sv shape (normalized to n_eval, 82, 9): {kernel_sv.shape}")

    print("\n" + "=" * 70)
    print("RANKING AGREEMENT: GradientExplainer vs KernelExplainer (same model, same rows)")
    print("=" * 70)
    rows = []
    for i in range(n_eval):
        true_class = int(eval_y[i])
        g_vec = grad_sv[i, :, true_class]
        k_vec = kernel_sv[i, :, true_class]
        try:
            tau, _ = weightedtau(g_vec, k_vec)
        except Exception:  # noqa: BLE001
            tau = float("nan")
        row = {"sample_idx": i, "family": eval_families[i], "kendall_weighted_tau": tau}
        for k in K_VALUES:
            row[f"jaccard_at_{k}"] = jaccard_topk(g_vec, k_vec, k)
        rows.append(row)

    import pandas as pd
    df_out = pd.DataFrame(rows)
    print(df_out.to_string(index=False))
    print("\nMedian across all rows:")
    print(df_out[[f"jaccard_at_{k}" for k in K_VALUES] + ["kendall_weighted_tau"]].median().to_string())

    out_path = Path("results/inspection/kernel_vs_gradient_validation.csv")
    df_out.to_csv(out_path, index=False)
    print(f"\nWritten: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
