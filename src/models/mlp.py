"""The MLP. Definition only -- no training logic, no data handling.

This exact class is used in both the centralized baseline and the federated
clients. If they differed, the "what does federation cost you" comparison would
be measuring an architecture change as well as federation.

Place at: src/models/mlp.py
"""

from __future__ import annotations

import torch
import torch.nn as nn

ACTIVATIONS: dict[str, type[nn.Module]] = {
    "relu": nn.ReLU,
    "gelu": nn.GELU,
    "silu": nn.SiLU,
}


class XFedMLP(nn.Module):
    """Feed-forward classifier over tabular network-flow features.

    Normalization is LayerNorm, not BatchNorm, and that is a federation
    constraint rather than a preference:

      - BatchNorm keeps running_mean and running_var in the state_dict. FedAvg
        averages every tensor in the state_dict, so those statistics get
        averaged across silos whose input distributions differ by construction
        (Dirichlet label skew, plus per-silo scalers). Averaging normalization
        constants computed on incompatible distributions is not meaningful.
      - At alpha=0.1 the smallest silo holds ~129 training rows. Batch
        statistics estimated from that are noise.

    LayerNorm normalizes per sample across features and carries no cross-batch
    state, so nothing distribution-dependent enters the aggregation.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int],
        n_classes: int,
        dropout: float = 0.2,
        norm: str = "layernorm",
        activation: str = "relu",
    ) -> None:
        super().__init__()

        if norm != "layernorm":
            raise ValueError(
                f"norm={norm!r} is not supported. LayerNorm is a locked decision for this "
                f"project -- BatchNorm running statistics are aggregation-unsafe under FedAvg."
            )
        if activation not in ACTIVATIONS:
            raise ValueError(f"activation must be one of {sorted(ACTIVATIONS)}, got {activation!r}")

        act_cls = ACTIVATIONS[activation]
        layers: list[nn.Module] = []
        prev = input_dim
        for width in hidden_dims:
            layers += [
                nn.Linear(prev, width),
                nn.LayerNorm(width),
                act_cls(),
                nn.Dropout(dropout),
            ]
            prev = width
        layers.append(nn.Linear(prev, n_classes))

        self.net = nn.Sequential(*layers)

        self.input_dim = input_dim
        self.hidden_dims = list(hidden_dims)
        self.n_classes = n_classes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns raw logits. Softmax is applied by the loss, not here."""
        return self.net(x)

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_model(model_cfg: dict, seed: int, device: str | torch.device = "cpu") -> XFedMLP:
    """Construct the model with reproducible initialization.

    Seeding immediately before construction means every silo in a federated run
    starts from identical weights when handed the same seed, which is what the
    server does in round 0.
    """
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    m = model_cfg["model"]
    model = XFedMLP(
        input_dim=int(m["input_dim"]),
        hidden_dims=list(m["hidden_dims"]),
        n_classes=int(model_cfg["labels"]["n_classes"]),
        dropout=float(m["dropout"]),
        norm=str(m["norm"]),
        activation=str(m["activation"]),
    )
    return model.to(device)
