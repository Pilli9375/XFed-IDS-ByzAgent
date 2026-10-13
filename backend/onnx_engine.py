"""ONNX Runtime fp32 engine for POST /predict (efficiency Part B).

Default since 2026-10-13 (configs/efficiency.yaml serving.engine: onnx_fp32);
with `torch` the backend behaves exactly as before. With `onnx_fp32`, startup exports the
already-verified base model to ONNX in memory (so the graph can never drift
from the served weights), runs it over the full validation split, and refuses
to start unless every prediction matches the torch model and validation
macro-F1 is equal at serving.require_equal_decimals. Validation rows only;
test_global.parquet is never read.

Only the BASE model is served through ONNX. A hot-swapped model is a torch
module produced at run time and keeps the torch path.

Place at: backend/onnx_engine.py
"""
from __future__ import annotations

import io
import logging

import numpy as np
import pandas as pd
import torch

from backend.model_loader import PROJECT_ROOT, LoadedModel, load_backend_config, resolve_path
from src.data.schema import encode_families, load_label_vocabulary, load_yaml
from src.train.metrics import compute_metrics

log = logging.getLogger(__name__)

EFFICIENCY_CONFIG = PROJECT_ROOT / "configs/efficiency.yaml"


def load_serving_config() -> dict:
    return load_yaml(EFFICIENCY_CONFIG)["serving"]


def build_onnx_session(loaded: LoadedModel, serving_cfg: dict):
    import onnxruntime as ort

    model = loaded.model.cpu().eval()
    n_features = len(loaded.feature_cols)
    buf = io.BytesIO()
    torch.onnx.export(
        model, torch.zeros(2, n_features), buf,
        input_names=["x"], output_names=["logits"],
        dynamic_axes={"x": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=int(serving_cfg["onnx_opset"]), do_constant_folding=True, dynamo=False,
    )
    so = ort.SessionOptions()
    so.intra_op_num_threads = int(serving_cfg["intra_op_threads"])
    so.inter_op_num_threads = 1
    session = ort.InferenceSession(buf.getvalue(), so, providers=["CPUExecutionProvider"])

    # Validation gate: identical predictions to torch on every validation row.
    paths = load_backend_config()["paths"]
    pool = pd.read_parquet(resolve_path(paths, "train_pool"), columns=loaded.feature_cols + ["family"])
    mask = pd.read_parquet(resolve_path(paths, "val_mask"))["is_val"].to_numpy()
    X_val = loaded.scaler.transform(pool.loc[mask, loaded.feature_cols].to_numpy(np.float32)).astype(np.float32)
    y_val = encode_families(pool.loc[mask, "family"], load_label_vocabulary(loaded.model_cfg))
    del pool

    bs = int(serving_cfg["verify_batch_size"])
    with torch.no_grad():
        torch_pred = np.concatenate([model(torch.from_numpy(X_val[i:i + bs])).argmax(1).numpy()
                                     for i in range(0, len(X_val), bs)])
    onnx_pred = np.concatenate([session.run(None, {"x": X_val[i:i + bs]})[0].argmax(1)
                                for i in range(0, len(X_val), bs)])
    n_diff = int((torch_pred != onnx_pred).sum())

    n_classes = int(loaded.model_cfg["labels"]["n_classes"])
    f1_torch = compute_metrics(y_val, torch_pred, n_classes, loaded.class_names, loaded.headline_idx)["macro_f1_headline"]
    f1_onnx = compute_metrics(y_val, onnx_pred, n_classes, loaded.class_names, loaded.headline_idx)["macro_f1_headline"]
    dec = int(serving_cfg["require_equal_decimals"])
    if n_diff or round(f1_onnx, dec) != round(f1_torch, dec):
        raise RuntimeError(
            f"ONNX engine refused: {n_diff} of {len(X_val):,} validation predictions differ from torch; "
            f"val macro-F1 torch={f1_torch!r} onnx={f1_onnx!r}."
        )
    log.info("onnx_fp32 engine verified on %d validation rows: 0 prediction differences, "
             "val macro-F1 %.10f (torch %.10f)", len(X_val), f1_onnx, f1_torch)
    return session
