"""Shared data/model helpers for the Flower client and server apps.

Flower's Simulation Runtime copies this whole app (everything under
federated/) into an isolated environment with its own fresh dependency
install (you saw this happen: "Installing application dependencies... via uv
sync"). It never touches the project's real src/ tree or working directory.
Two consequences, both handled here:

  1. Code:   import from xfed_federated._vendored.* (copies of the four
     modules actually needed), not from src.*. Vendored, not linked, because
     the isolated env cannot see a sibling folder outside federated/.
  2. Data:   every path to configs/ or data/ is absolute, built from
     _PROJECT_ROOT below -- never relative, because the isolated run's
     working directory is not the project root.

If you change src/data/loaders.py, src/data/schema.py, src/models/mlp.py, or
src/train/metrics.py, re-copy the changed file into
federated/xfed_federated/_vendored/ before your next `flwr run`, or the
federated code will silently run against stale logic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

def _find_project_root() -> Path:
    """Repo root: $XFED_PROJECT_ROOT if set, else the nearest ancestor of this
    file or of the working directory that holds configs/data.yaml. Flower may
    run the app from a copy, so __file__ alone is not trusted."""
    env = os.environ.get("XFED_PROJECT_ROOT")
    if env:
        return Path(env)
    for start in (Path(__file__).resolve(), Path.cwd().resolve()):
        for cand in (start, *start.parents):
            if (cand / "configs" / "data.yaml").is_file() and (cand / "src").is_dir():
                return cand
    raise RuntimeError(
        "Could not locate the xfed-ids repo root (no ancestor holds configs/data.yaml). "
        "Set the XFED_PROJECT_ROOT environment variable to the repo path."
    )


_PROJECT_ROOT = _find_project_root()

from xfed_federated._vendored.loaders import load_silo, load_centralized, Splits
from xfed_federated._vendored.schema import (
    class_names as _class_names,
    headline_class_indices,
    load_label_vocabulary,
    load_yaml as _load_yaml,
)
from xfed_federated._vendored.mlp import build_model
from xfed_federated._vendored.metrics import compute_metrics, format_per_class
from xfed_federated._vendored.label_flip import PoisonedClient, get_server_round, resolve_malicious_silos
from xfed_federated._vendored.client_stats import ClientStatsRecorder
from xfed_federated._vendored.byz_agent import (
    AgentConfig,
    AgentResponseError,
    build_client_history,
    decide_round,
    decide_round_history,
    decisions_to_weights,
    log_decisions,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_yaml(rel_path: str) -> dict:
    """rel_path is relative to the real project root, e.g. 'configs/data.yaml'."""
    return _load_yaml(_PROJECT_ROOT / rel_path)


def load_global_class_weights(model_cfg: dict) -> np.ndarray:
    """The frozen, shared class weights every silo must use identically.

    Raises rather than silently falling back to per-silo weights -- a silent
    fallback here is exactly the bug this file exists to prevent.
    """
    path = _PROJECT_ROOT / "configs" / "global_class_weights.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/export_class_weights.py` "
            f"from the project root once before any federated run."
        )
    data = json.loads(path.read_text())
    vocab = load_label_vocabulary(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])
    arr = np.zeros(n_classes, dtype=np.float32)
    for name, idx in vocab.items():
        if name not in data["weights"]:
            raise KeyError(f"{name} missing from {path}. Re-run the export script.")
        arr[idx] = data["weights"][name]
    return arr


def load_silo_for_client(
    silo_id: int, alpha: str, seed: int, data_cfg: dict, model_cfg: dict,
    class_weights: np.ndarray,
) -> Splits:
    return load_silo(
        silo_id, alpha, seed, data_cfg, model_cfg,
        root=_PROJECT_ROOT / "data" / "processed",
        class_weights_override=class_weights,
    )


def load_centralized_for_server(data_cfg: dict, model_cfg: dict) -> Splits:
    """Used only by server_app.py, for the centralized test-set comparison."""
    return load_centralized(data_cfg, model_cfg, root=_PROJECT_ROOT / "data" / "processed")


def local_train_epochs(
    model: nn.Module, splits: Splits, epochs: int, model_cfg: dict, mu: float = 0.0,
) -> float:
    """One client's local training. No persistent optimizer state across
    rounds, matching plain FedAvg (McMahan et al., 2017).

    mu > 0 activates FedProx (Li et al., 2020): adds (mu/2) * ||w - w_global||^2
    to the loss, penalizing drift away from the model this client just received.
    FedProx changes ONLY the client-side objective -- server-side aggregation
    is identical weighted averaging, so FedAvg is exactly the mu=0 case of this
    same function. global_params is captured here, at the top, because the
    caller has already loaded the received global weights into `model` before
    calling this -- so the parameters at this exact point ARE w_global.
    """
    X = torch.from_numpy(splits.X_train.copy()).to(DEVICE)
    y = torch.from_numpy(splits.y_train.copy()).to(DEVICE)
    weights = torch.from_numpy(splits.class_weights.copy()).to(DEVICE)

    global_params = [p.detach().clone() for p in model.parameters()] if mu > 0 else None

    tr = model_cfg["training"]
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=float(tr["lr"]), weight_decay=float(tr["weight_decay"])
    )
    batch_size = int(tr["batch_size"])
    n = len(y)

    model.train()
    epoch_loss = 0.0
    for _ in range(epochs):
        perm = torch.randperm(n, device=DEVICE)
        total = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(X[idx]), y[idx])
            if mu > 0:
                prox = sum(((p - gp) ** 2).sum() for p, gp in zip(model.parameters(), global_params))
                loss = loss + (mu / 2.0) * prox
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        epoch_loss = total / n
    return epoch_loss


@torch.no_grad()
def predict(model: nn.Module, X: torch.Tensor, batch_size: int = 8192) -> torch.Tensor:
    """Batched inference. Duplicated from src/train/centralized.py (8 lines --
    not worth a fifth vendored module)."""
    model.eval()
    out = []
    for i in range(0, len(X), batch_size):
        out.append(model(X[i:i + batch_size]).argmax(dim=1))
    return torch.cat(out)


def evaluate_arrays(
    model: nn.Module, X_np: np.ndarray, y_np: np.ndarray,
    model_cfg: dict, headline_idx: np.ndarray,
) -> dict:
    X = torch.from_numpy(X_np.copy()).to(DEVICE)
    y_pred = predict(model, X).cpu().numpy()
    n_classes = int(model_cfg["labels"]["n_classes"])
    return compute_metrics(y_np, y_pred, n_classes, _class_names(model_cfg), headline_idx)


class_names = _class_names


# ---------------------------------------------------------------------------
# Preregistered federated optimizer comparison (2026-10-12).
# configs/federated_methods.yaml holds every method parameter; a run selects
# one by name via --run-config "method='<name>'". An empty method name means
# the legacy path (FedAvg/FedProx via run-config mu, defense.yaml strategies),
# which is left exactly as it was.
# ---------------------------------------------------------------------------

def get_method_name(run_config) -> str:
    return str(run_config.get("method", "")).strip()


def load_method(method_name: str) -> tuple[dict, dict]:
    """(full federated_methods.yaml, that method's entry). Raises on an
    unknown name rather than falling back to FedAvg."""
    cfg = load_yaml("configs/federated_methods.yaml")
    if method_name not in cfg["methods"]:
        raise KeyError(
            f"method {method_name!r} not in configs/federated_methods.yaml. "
            f"Known: {sorted(cfg['methods'])}"
        )
    return cfg, cfg["methods"][method_name]


def verify_partition_manifest(alpha: str, seed: int) -> dict:
    """SHA256 of the on-disk train/test silo assignments against
    data/processed/partitions/manifest.json, computed exactly as
    src/data/partition.py does (int16 assignment bytes). Raises on mismatch.
    Reads only the row->silo assignment files, never test features or labels.
    """
    import hashlib
    import pandas as pd

    part_dir = _PROJECT_ROOT / "data" / "processed" / "partitions"
    manifest = json.loads((part_dir / "manifest.json").read_text())
    tag = f"a{alpha}_s{seed}"
    entry = manifest["configs"][tag]
    out = {"tag": tag}
    for split in ("train", "test"):
        assign = pd.read_parquet(part_dir / f"assign_{tag}_{split}.parquet")["silo"].to_numpy(np.int16)
        got = hashlib.sha256(assign.tobytes()).hexdigest()
        if got != entry[f"hash_{split}"]:
            raise RuntimeError(
                f"MANIFEST MISMATCH for {tag} ({split}): disk {got} != manifest "
                f"{entry[f'hash_{split}']}. Stop: do not train on this partition."
            )
        out[f"hash_{split}"] = got
    return out


# ---------------------------------------------------------------------------
# Efficiency Part C: client->server update compression (configs/efficiency.yaml
# compression). Off unless --run-config sets upload-compression; method path
# only. The client sends a quantized delta against the global weights it
# received; the server adds the dequantized delta back to the same global
# weights before the unchanged library aggregation.
# ---------------------------------------------------------------------------

def get_upload_compression(run_config) -> str:
    return str(run_config.get("upload-compression", "")).strip()


def load_compression_scheme(name: str) -> dict:
    schemes = load_yaml("configs/efficiency.yaml")["compression"]["schemes"]
    if name not in schemes:
        raise KeyError(f"upload-compression {name!r} not in configs/efficiency.yaml. Known: {sorted(schemes)}")
    return schemes[name]


def compress_update(local_sd: dict, global_sd: dict, scheme: dict) -> dict:
    from collections import OrderedDict

    out = OrderedDict()
    for k, w in local_sd.items():
        if not torch.is_floating_point(w):
            raise TypeError(f"{k} is {w.dtype}; update compression expects float tensors only")
        delta = w.detach().cpu().float() - global_sd[k].detach().cpu().float()
        if scheme["kind"] == "fp16":
            out[k] = delta.to(torch.float16)
        elif scheme["kind"] == "int8_per_tensor":
            if scheme["scale"] != "absmax":
                raise ValueError(f"int8 scale {scheme['scale']!r} not implemented")
            qmax = int(scheme["qmax"])
            amax = float(delta.abs().max())
            scale = amax / qmax if amax > 0 else 1.0
            out[k + ".q"] = torch.clamp(torch.round(delta / scale), -qmax, qmax).to(torch.int8)
            out[k + ".scale"] = torch.tensor([scale], dtype=torch.float32)
        else:
            raise ValueError(f"compression kind {scheme['kind']!r} not implemented")
    return out


def decompress_update(received: dict, global_sd: dict, scheme: dict) -> dict:
    from collections import OrderedDict

    out = OrderedDict()
    for k, g in global_sd.items():
        g = g.detach().cpu().float()
        if scheme["kind"] == "fp16":
            delta = received[k].float()
        elif scheme["kind"] == "int8_per_tensor":
            delta = received[k + ".q"].float() * received[k + ".scale"].float()
        else:
            raise ValueError(f"compression kind {scheme['kind']!r} not implemented")
        out[k] = g + delta
    return out


def arrayrecord_nbytes(record) -> int:
    """Payload bytes of an ArrayRecord: tensor data only, no message framing."""
    return int(sum(arr.numpy().nbytes for arr in record.values()))


def state_dict_sha256(state_dict: dict) -> str:
    """Content hash of a state_dict: sorted keys + raw tensor bytes. Same
    construction as src/hotswap/retrain.py's _state_dict_sha256, so it does
    not depend on torch.save's pickle bytes."""
    import hashlib

    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode("utf-8"))
        h.update(state_dict[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


__all__ = [
    "DEVICE", "load_yaml", "load_global_class_weights", "load_silo_for_client",
    "load_centralized_for_server", "local_train_epochs", "evaluate_arrays",
    "build_model", "headline_class_indices", "class_names", "predict",
    "compute_metrics", "format_per_class",
    "PoisonedClient", "get_server_round", "resolve_malicious_silos",
    "ClientStatsRecorder",
    "AgentConfig", "AgentResponseError", "decide_round", "decide_round_history",
    "build_client_history", "decisions_to_weights", "log_decisions",
    "get_method_name", "load_method", "verify_partition_manifest",
    "arrayrecord_nbytes", "state_dict_sha256",
    "get_upload_compression", "load_compression_scheme", "compress_update", "decompress_update",
]
