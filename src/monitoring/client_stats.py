"""Per-client behavioral statistics. ByzAgent trust check, Phase 1.

Five stats, computed server-side once per round, before aggregation
discards each client's individual reply:

  update_norm          L2 distance between a client's post-training weights
                        and the previous-round global weights.
  cosine_to_global      cos(client update, this round's actual FedAvg
                        aggregate update) -- computed AFTER aggregation, so
                        it needs the aggregated arrays as well as the
                        pre-aggregation per-client ones.
  cosine_to_peer_mean   cos(client update, the UNWEIGHTED mean of every
                        client's update this round). Deliberately unweighted,
                        not sample-count weighted like FedAvg's own
                        aggregation -- see the note on PEER_MEAN_IS_UNWEIGHTED
                        below. Do not change this to a weighted mean.
  train_loss            Last-epoch local training loss. Passed straight
                        through from the client's own MetricRecord --
                        computed here for nothing, just recorded alongside
                        the other four so a downstream reader has one row
                        with all five stats instead of joining two files.
  val_accuracy          The client's post-training model evaluated against
                        the CENTRALIZED clean validation set (val_mask.parquet
                        via load_centralized_for_server), NOT the client's own
                        local data and NOT a client-local split. Computed by
                        the caller (server_app.py already holds build_model /
                        predict / X_val / y_val in scope) and passed in as a
                        plain float -- this module has no opinion on model
                        architecture or inference batching, see
                        "architecture-agnostic" below.

PEER_MEAN_IS_UNWEIGHTED -- locked, do not drift this to sample-weighting:
  This stat's job is to detect deviation from what the fleet is doing. If the
  reference mean were sample-weighted, a large malicious silo would partially
  define its own baseline -- at f=3 with a full-knowledge adversary (see
  results/attacks/PHASE0_SUMMARY.md) this could materially shrink the very
  deviation the stat exists to catch, not just let the big one "hide a
  little". This is deliberately NOT consistent with FedAvg's own aggregation
  weighting -- that is the point, not an oversight to reconcile later.

Architecture-agnostic / shape-agnostic, on purpose: nothing here reads
input_dim, hidden_dims, n_classes, or the number of silos. Every function
operates on plain dict[str, torch.Tensor] state_dicts and flattens whatever
keys happen to be present, in sorted order, so two independently-loaded
state_dicts flatten identically regardless of dict insertion order. If the
model architecture or n_silos ever changes, nothing in this file needs to.

CANONICAL SOURCE. federated/xfed_federated/ runs inside Flower's isolated
simulation runtime, which cannot see this src/ tree -- same reason
src/data/loaders.py, src/models/mlp.py, src/train/metrics.py, and
src/attacks/label_flip.py are vendored there. This file is therefore
vendored too, at federated/xfed_federated/_vendored/client_stats.py --
edit HERE, then re-copy before your next `flwr run`.

Place at: src/monitoring/client_stats.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch

STAT_FIELDS = (
    "round", "silo_id", "num_examples",
    "update_norm", "cosine_to_global", "cosine_to_peer_mean",
    "train_loss", "val_accuracy",
)


# ---------------------------------------------------------------------------
# pure vector math -- no flwr, no model-building, no I/O
# ---------------------------------------------------------------------------

def flatten_state_dict(state_dict: dict[str, torch.Tensor]) -> np.ndarray:
    """Concatenate every tensor into one 1D float64 vector, sorted by
    parameter name. Sorted (not insertion) order is deliberate: two
    state_dicts built from independently-deserialized ArrayRecords must
    flatten identically even if key insertion order ever differed, and
    sorting removes that as a possible silent bug.
    """
    if not state_dict:
        raise ValueError("state_dict is empty -- nothing to flatten")
    parts = [
        state_dict[key].detach().cpu().numpy().astype(np.float64).ravel()
        for key in sorted(state_dict.keys())
    ]
    return np.concatenate(parts)


def state_dict_delta(a: dict[str, torch.Tensor], b: dict[str, torch.Tensor]) -> np.ndarray:
    """flatten(a) - flatten(b), key sets asserted equal first.

    A silent shape mismatch here (e.g. one side missing a layer) would
    produce a numpy broadcast error or, worse, a wrong-length concatenation
    that happens to be comparable -- fail loudly on key mismatch instead of
    letting numpy's own error (or lack of one) decide what happens.
    """
    ka, kb = set(a.keys()), set(b.keys())
    if ka != kb:
        raise ValueError(f"state_dict key mismatch, cannot diff: {ka ^ kb}")
    return flatten_state_dict(a) - flatten_state_dict(b)


def l2_norm(vec: np.ndarray) -> float:
    return float(np.linalg.norm(vec))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Returns NaN, not 0.0, when either vector has zero norm.

    A zero update (a client whose weights did not move at all) has no
    defined direction. Reporting cos=0.0 in that case would read as
    "orthogonal / maximally different direction", which is a real and
    interpretable detection signal -- exactly the wrong thing to conflate
    with "undefined because there was nothing to compare".
    """
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# per-round accumulation + history buffer
# ---------------------------------------------------------------------------

@dataclass
class _PendingClient:
    silo_id: int
    num_examples: int
    train_loss: float
    val_accuracy: float
    update_vec: np.ndarray


@dataclass
class ClientStatsRecorder:
    """Accumulates one round's per-client stats and appends them to a JSONL
    history buffer -- one row per (round, silo_id), mirroring the existing
    silo_metrics.jsonl convention (LoggingFedAvg in server_app.py) so Phase 4's
    rolling-history read is a plain groupby/filter over rows already on disk,
    no new storage technology to learn.

    Call order per round, enforced by the guards below (fail loudly, never
    silently compute against missing/stale state -- same posture as Phase 0's
    hard test-guard):
      1. start_round(prev_global_state)   -- once, before any client is seen
      2. record_client(...)               -- once per client reply
      3. finalize_round(agg_state)        -- once, after FedAvg's own
                                              aggregate_train has produced
                                              this round's new global weights
    """

    out_path: Path
    _prev_global_state: dict[str, torch.Tensor] | None = field(default=None, init=False)
    _round: int | None = field(default=None, init=False)
    _pending: list[_PendingClient] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.out_path = Path(self.out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)

    def start_round(self, server_round: int, prev_global_state: dict[str, torch.Tensor]) -> None:
        """Cache the previous round's global weights. Called from
        LoggingFedAvg.configure_train, which is the only point in Flower's
        strategy.start() loop where the pre-this-round global ArrayRecord is
        available (verified against the installed flwr.serverapp.strategy
        source: aggregate_train's caller no longer has it once configure_train
        returns) -- see server_app.py for the call site.
        """
        self._round = server_round
        self._prev_global_state = {
            k: v.detach().cpu().clone() for k, v in prev_global_state.items()
        }
        self._pending = []

    def record_client(
        self,
        silo_id: int,
        client_state: dict[str, torch.Tensor],
        num_examples: int,
        train_loss: float,
        val_accuracy: float,
    ) -> None:
        if self._prev_global_state is None:
            raise RuntimeError(
                "ClientStatsRecorder.record_client called with no cached "
                "previous-round global weights -- start_round() must be "
                "called first, every round, with a non-None state. Refusing "
                "to silently compute update_norm/cosine against None, zero, "
                "or stale weights."
            )
        update_vec = state_dict_delta(client_state, self._prev_global_state)
        self._pending.append(_PendingClient(
            silo_id=int(silo_id),
            num_examples=int(num_examples),
            train_loss=float(train_loss),
            val_accuracy=float(val_accuracy),
            update_vec=update_vec,
        ))

    def finalize_round(self, agg_global_state: dict[str, torch.Tensor]) -> list[dict]:
        """Compute the two aggregate-dependent stats (cosine_to_global,
        cosine_to_peer_mean) now that every client has been recorded and
        FedAvg's own aggregate_train has produced this round's new global
        weights, then append one JSONL row per client and reset for the
        next round.

        Returns the list of row dicts just written (ByzAgent, Phase 3,
        consumes these directly to build its per-round prompt rather than
        re-reading them back off disk -- purely additive: existing callers
        that ignore the return value are unaffected).
        """
        if self._prev_global_state is None or self._round is None:
            raise RuntimeError(
                "ClientStatsRecorder.finalize_round called without a "
                "preceding start_round -- nothing to finalize."
            )
        if not self._pending:
            raise RuntimeError(
                "ClientStatsRecorder.finalize_round called with zero "
                "recorded clients this round -- record_client was never "
                "called, or all replies errored. Either way there is "
                "nothing to write, and writing an empty round silently "
                "would hide that from a downstream reader."
            )

        global_update_vec = state_dict_delta(agg_global_state, self._prev_global_state)

        # PEER_MEAN_IS_UNWEIGHTED -- locked, see module docstring. Plain
        # arithmetic mean across clients, NOT weighted by num_examples.
        peer_mean_vec = np.mean(
            np.stack([p.update_vec for p in self._pending], axis=0), axis=0
        )

        rows = []
        for p in self._pending:
            rows.append({
                "round": self._round,
                "silo_id": p.silo_id,
                "num_examples": p.num_examples,
                "update_norm": l2_norm(p.update_vec),
                "cosine_to_global": cosine_similarity(p.update_vec, global_update_vec),
                "cosine_to_peer_mean": cosine_similarity(p.update_vec, peer_mean_vec),
                "train_loss": p.train_loss,
                "val_accuracy": p.val_accuracy,
            })

        with open(self.out_path, "a") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

        self._prev_global_state = None
        self._round = None
        self._pending = []
        return rows


__all__ = [
    "STAT_FIELDS",
    "flatten_state_dict",
    "state_dict_delta",
    "l2_norm",
    "cosine_similarity",
    "ClientStatsRecorder",
]
