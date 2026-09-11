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

# Override with:  $env:XFED_PROJECT_ROOT = "D:\some\other\path"
# before `flwr run`, if the project ever moves.
_PROJECT_ROOT = Path(os.environ.get("XFED_PROJECT_ROOT", r"C:\Pilli\Capstone\xfed-ids"))

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

__all__ = [
    "DEVICE", "load_yaml", "load_global_class_weights", "load_silo_for_client",
    "load_centralized_for_server", "local_train_epochs", "evaluate_arrays",
    "build_model", "headline_class_indices", "class_names", "predict",
    "compute_metrics", "format_per_class",
    "PoisonedClient", "get_server_round", "resolve_malicious_silos",
    "ClientStatsRecorder",
    "AgentConfig", "AgentResponseError", "decide_round", "decide_round_history",
    "build_client_history", "decisions_to_weights", "log_decisions",
]
