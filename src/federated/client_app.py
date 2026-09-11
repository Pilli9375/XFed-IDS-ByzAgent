"""Flower ClientApp for XFed-IDS. One execution = one simulated silo, one round.

Reuses load_silo(), build_model(), compute_metrics() from the centralized
pipeline unchanged. This is the payoff of having kept the model and loaders
separate from any training-loop-specific code from the start of this chat.

ClientApp objects are stateless -- Flower recreates this module's functions'
execution context fresh for every Message. The model is therefore rebuilt and
immediately overwritten with the received global weights on every call; it is
never carried over between rounds by this process.

silo_id comes from Flower's partition-id (Context.node_config), assigned once
per simulated SuperNode by the simulation runtime. alpha/seed/local-epochs are
RUN-level config (identical for every silo in a given run), read from
Context.run_config.

The scaler is fit fresh inside load_silo() every call, on that silo's own
train rows only -- the loader already enforces this boundary; this wrapper
adds no new leakage surface, it just calls the existing loader once per round.

Place at: src/federated/client_app.py
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from ..data.loaders import load_silo, to_device_tensors
from ..data.schema import headline_class_indices, load_yaml
from ..models.mlp import build_model
from ..train.metrics import compute_metrics

app = ClientApp()


def _run_context(context: Context):
    rc = context.run_config
    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")
    silo_id = int(context.node_config["partition-id"])
    alpha = str(rc["alpha"])
    seed = int(rc["seed"])
    return data_cfg, model_cfg, silo_id, alpha, seed


@app.train()
def train(msg: Message, context: Context) -> Message:
    """One local training round on this silo's private partition."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_cfg, model_cfg, silo_id, alpha, seed = _run_context(context)
    local_epochs = int(context.run_config.get("local-epochs", 1))

    splits = load_silo(silo_id, alpha, seed, data_cfg, model_cfg)
    tensors = to_device_tensors(splits, device)
    X_tr, y_tr = tensors["train"]

    model = build_model(model_cfg, seed=seed, device=device)
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())

    weights = torch.from_numpy(splits.class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(model_cfg["training"]["lr"]),
        weight_decay=float(model_cfg["training"]["weight_decay"]),
    )

    batch_size = int(model_cfg["training"]["batch_size"])
    n = len(y_tr)
    model.train()
    total_loss = 0.0
    for _ in range(local_epochs):
        perm = torch.randperm(n, device=device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(X_tr[idx]), y_tr[idx])
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)

    reply = RecordDict({
        "arrays": ArrayRecord(model.state_dict()),
        "metrics": MetricRecord({
            "train_loss": total_loss / max(n * local_epochs, 1),
            "num-examples": n,        # FedAvg's default weighting key
            "silo_id": silo_id,
        }),
    })
    return Message(content=reply, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context) -> Message:
    """Evaluate the just-aggregated global model on this silo's local test rows.

    Per-round diagnostic, not the reportable number -- see server_app.py for
    the pooled centralized-test evaluation that IS comparable to the MLP/
    XGBoost baselines.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_cfg, model_cfg, silo_id, alpha, seed = _run_context(context)

    splits = load_silo(silo_id, alpha, seed, data_cfg, model_cfg)
    tensors = to_device_tensors(splits, device)
    X_te, y_te = tensors["test"]

    model = build_model(model_cfg, seed=seed, device=device)
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
    model.eval()

    n_classes = int(model_cfg["labels"]["n_classes"])
    headline_idx = headline_class_indices(model_cfg)
    with torch.no_grad():
        y_pred = model(X_te).argmax(dim=1).cpu().numpy()
    m = compute_metrics(y_te.cpu().numpy(), y_pred, n_classes, splits.class_names, headline_idx)

    fpr = m["false_positive_rate"]
    if fpr is None or (isinstance(fpr, float) and math.isnan(fpr)):
        fpr = 0.0  # guards a silo whose local test rows happen to have 0 Benign

    reply = RecordDict({
        "metrics": MetricRecord({
            "val_macro_f1_headline": m["macro_f1_headline"],
            "false_positive_rate": fpr,
            "num-examples": len(y_te),
            "silo_id": silo_id,
        }),
    })
    return Message(content=reply, reply_to=msg)
