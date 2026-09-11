"""Flower ServerApp -- orchestrates FedAvg/Krum/trimmed-mean and evaluates the
global model.

Server-side evaluation runs the aggregated global model against the SAME
centralized test set (test_global.parquet) the MLP baseline used. This is the
number that goes in the federated-vs-centralized comparison table -- it is not
an average of the 10 silos' own test performance, which would answer a
different question (how good is each local view) rather than the one that
matters (how good is the thing federation actually produced).
"""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path

import numpy as np
import torch

from flwr.app import ArrayRecord, ConfigRecord, Context, Message
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg, Krum, MultiKrum, FedTrimmedAvg
from flwr.serverapp.strategy.multikrum import compute_distances

from xfed_federated.task import (
    DEVICE,
    _PROJECT_ROOT,
    AgentConfig,
    ClientStatsRecorder,
    build_client_history,
    build_model,
    class_names,
    compute_metrics,
    decide_round,
    decide_round_history,
    decisions_to_weights,
    format_per_class,
    headline_class_indices,
    load_centralized_for_server,
    load_yaml,
    log_decisions,
    predict,
    resolve_malicious_silos,
)


class LoggingMixin:
    """Side-channel logging shared by every ByzAgent-instrumented strategy
    (FedAvg, MultiKrum, classical Krum, FedTrimmedAvg).

    Chat 04 (Pre-check A/B/C): cross-silo explanation agreement needs each
    silo's own post-local-training model at a chosen round, and plain
    aggregate_train/aggregate_evaluate only ever return the fleet-wide
    aggregate -- individual replies are gone once those functions return.
    This mixin captures each reply on the way through, then calls
    super().aggregate_train/aggregate_evaluate() unchanged, so the actual
    federated result is byte-for-byte identical to the strategy it's mixed
    with -- only a side channel is added.

    silo_id is read from the client's own MetricRecord, NOT from
    Message.metadata.src_node_id -- the latter is Flower's internal node
    id, not the partition-id (0-9) this project's silo identity is
    defined by. client_app.py stamps "silo_id" into every MetricRecord it
    returns for exactly this reason.

    ByzAgent Phase 1 addition: also computes and persists the 5 per-client
    behavioral stats (src/monitoring/client_stats.py) every train round, via
    the injected `stats_recorder`.

    ByzAgent Phase 2 (this refactor): originally this logic lived directly
    on a single `LoggingFedAvg(FedAvg)` class. It's pulled out into a mixin
    here so the SAME side channel (checkpoints, silo_metrics.jsonl, Phase 1
    stats) attaches to Krum/MultiKrum/FedTrimmedAvg without duplicating the
    code three times. Mechanism-specific logging (which silo Krum kept/
    excluded, which silo's coordinates trimmed-mean cut) is NOT here -- it
    lives in `_log_mechanism`, a no-op hook on this class, overridden per
    concrete strategy below.

    MRO note: concrete classes are `class LoggingX(..., X)` where X is a
    flwr Strategy (FedAvg, MultiKrum, Krum, FedTrimmedAvg). Every __init__
    in this mixin chain pops its own kwargs then calls
    super().__init__(*args, **kwargs), which Python's MRO resolves onward
    to X's own constructor -- so X's own constructor behavior is completely
    unchanged. Verified against the installed flwr 1.33.0 source for every
    X used here: none of FedAvg/MultiKrum/Krum/FedTrimmedAvg override
    configure_train, aggregate_evaluate, or configure_evaluate, so this
    mixin's versions of those (below) are the only ones that ever run,
    regardless of which strategy it's mixed with. All four DO override
    aggregate_train (that's the whole point of each strategy), which is why
    aggregate_train here is a template method that defers the actual
    aggregation to super().aggregate_train() after logging.

    configure_train is overridden ONLY to capture the previous-round global
    ArrayRecord: verified against the installed flwr.serverapp.strategy
    source (strategy.py's Strategy.start() loop) that `arrays` is passed
    into configure_train BEFORE being reassigned to this round's aggregate --
    aggregate_train's own caller no longer has access to it once
    configure_train returns, so there is no other point to cache it from
    without adding cross-call state here.
    """

    def __init__(
        self, *args, silo_ckpt_dir: Path, silo_metrics_path: Path,
        stats_recorder: ClientStatsRecorder, build_model_fn, X_val_tensor, y_val: np.ndarray,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.silo_ckpt_dir = silo_ckpt_dir
        self.silo_metrics_path = silo_metrics_path
        self.silo_ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.silo_metrics_path.parent.mkdir(parents=True, exist_ok=True)

        self.stats_recorder = stats_recorder
        self.build_model_fn = build_model_fn
        self.X_val_tensor = X_val_tensor
        self.y_val = y_val

    def _log_replies(self, server_round: int, replies: list, phase: str) -> None:
        for msg in replies:
            if msg.has_error():
                continue
            content = msg.content
            metrics = content["metrics"]
            silo_id = int(metrics["silo_id"])

            if phase == "train":
                arrays = content[self.arrayrecord_key]
                state_dict = arrays.to_torch_state_dict()
                ckpt_path = (self.silo_ckpt_dir
                             / f"round_{server_round:03d}_silo_{silo_id}.pt")
                torch.save(state_dict, ckpt_path)

            row = {"round": server_round, "phase": phase, "silo_id": silo_id}
            if phase == "train":
                row["train_loss"] = float(metrics["train_loss"])
                row["num_examples"] = int(metrics["num-examples"])
            else:
                row["num_examples"] = int(metrics["num-examples"])
                row["macro_f1_headline"] = float(metrics["macro_f1_headline"])
                row["false_positive_rate"] = float(metrics["false_positive_rate"])

            with open(self.silo_metrics_path, "a") as f:
                f.write(json.dumps(row) + "\n")

    def configure_train(self, server_round: int, arrays: ArrayRecord, config, grid):
        """Cache this round's pre-training global weights before the base
        strategy's own configure_train sends them out -- see the class
        docstring for why this is the only point they're available from.
        """
        self.stats_recorder.start_round(server_round, arrays.to_torch_state_dict())
        return super().configure_train(server_round, arrays, config, grid)

    def _record_client_stats(self, server_round: int, replies: list) -> None:
        """One call per client reply: builds that client's post-training
        model from its own reply (never a client's own local data -- the
        centralized val split cached on self), evaluates it against the
        centralized clean validation set, and hands everything to the
        recorder. cosine_to_global / cosine_to_peer_mean are computed later,
        in finalize_round, once every client this round has been seen and
        the base strategy's own aggregate is available.
        """
        for msg in replies:
            if msg.has_error():
                continue
            content = msg.content
            metrics = content["metrics"]
            silo_id = int(metrics["silo_id"])
            client_state = content[self.arrayrecord_key].to_torch_state_dict()

            model = self.build_model_fn()
            model.load_state_dict(client_state)
            y_pred = predict(model, self.X_val_tensor).cpu().numpy()
            val_accuracy = float((y_pred == self.y_val).mean())

            self.stats_recorder.record_client(
                silo_id=silo_id,
                client_state=client_state,
                num_examples=int(metrics["num-examples"]),
                train_loss=float(metrics["train_loss"]),
                val_accuracy=val_accuracy,
            )

    def _pre_aggregate_train_logging(self, server_round: int, replies) -> list:
        """Materialize replies (consumed multiple times downstream: this
        logging pass, the mechanism hook, and the base strategy's own
        aggregate_train), then run the strategy-agnostic side channel
        (checkpoints, silo_metrics.jsonl row, Phase 1 behavioral stats).
        """
        replies = list(replies)
        self._log_replies(server_round, replies, phase="train")
        self._record_client_stats(server_round, replies)
        return replies

    def _log_mechanism(self, server_round: int, replies: list) -> None:
        """Hook for mechanism-level logging specific to a robust-aggregation
        strategy (Krum's kept/excluded silos, trimmed-mean's per-silo trim
        rate). No-op for plain FedAvg -- overridden by the Krum/TrimmedAvg
        subclasses below.
        """
        return

    def aggregate_train(self, server_round: int, replies):
        replies = self._pre_aggregate_train_logging(server_round, replies)
        self._log_mechanism(server_round, replies)
        agg_arrays, agg_metrics = super().aggregate_train(server_round, replies)
        if agg_arrays is not None:
            self.stats_recorder.finalize_round(agg_arrays.to_torch_state_dict())
        return agg_arrays, agg_metrics

    def aggregate_evaluate(self, server_round: int, replies):
        replies = list(replies)
        self._log_replies(server_round, replies, phase="evaluate")
        return super().aggregate_evaluate(server_round, replies)


class LoggingFedAvg(LoggingMixin, FedAvg):
    """Plain FedAvg with the ByzAgent side channel attached. Behaviorally
    identical to the original single-class LoggingFedAvg this was refactored
    out of -- verified by a byte-for-byte regression re-run of the locked
    clean baseline (fedavg_a0.5_s42) against this refactored code; see
    PHASE2_SUMMARY.md for the diff result.
    """


class _KrumMechanismLogging:
    """Krum/Multi-Krum mechanism-level logging: per round, which silo(s)
    were selected vs. excluded and their Krum score.

    Reimplements the SAME scoring logic as
    flwr.serverapp.strategy.multikrum.select_multikrum (num_closest = n -
    num_malicious_nodes - 2, sum of distances to the num_closest nearest
    neighbors, lowest `num_nodes_to_select` scores selected) -- using the
    library's own `compute_distances` for the actual distance math, not a
    re-derivation of it. This is deliberately a duplicate computation, not a
    call into the library's internal select_multikrum, so this side channel
    cannot mutate what super().aggregate_train() actually selects; run
    before super() is called, on the same materialized replies list, with
    no randomness anywhere in the computation, so it cannot diverge from
    what super().aggregate_train() computes internally moments later.
    Empirically verified to match `select_multikrum`'s output exactly on
    synthetic data before being wired in here (see PHASE2_SUMMARY.md).

    Sibling of LoggingMixin in the MRO (not a subclass of it) so that both
    LoggingMultiKrum(_KrumMechanismLogging, LoggingMixin, MultiKrum) and
    LoggingKrum(_KrumMechanismLogging, LoggingMixin, Krum) can share this
    logic without a diamond inheritance between the two concrete classes.
    """

    def __init__(self, *args, krum_log_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.krum_log_path = krum_log_path
        self.krum_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_mechanism(self, server_round: int, replies: list) -> None:
        valid_replies = [m for m in replies if not m.has_error()]
        if not valid_replies:
            return
        reply_contents = [msg.content for msg in valid_replies]
        silo_ids = [int(c["metrics"]["silo_id"]) for c in reply_contents]

        array_records = [c[self.arrayrecord_key] for c in reply_contents]
        distance_matrix = compute_distances(array_records)
        num_closest = max(1, len(array_records) - self.num_malicious_nodes - 2)

        scores = []
        for i, distance in enumerate(distance_matrix):
            closest = np.argsort(distance)[1:num_closest + 1]
            scores.append(float(np.sum(distance_matrix[i, closest])))

        order = np.argsort(scores)
        selected_positions = set(order[: self.num_nodes_to_select].tolist())

        for pos, silo_id in enumerate(silo_ids):
            row = {
                "round": server_round,
                "silo_id": silo_id,
                "krum_score": scores[pos],
                "selected": pos in selected_positions,
                "num_malicious_nodes_assumed": self.num_malicious_nodes,
                "num_nodes_to_select": self.num_nodes_to_select,
            }
            with open(self.krum_log_path, "a") as f:
                f.write(json.dumps(row) + "\n")


class LoggingMultiKrum(_KrumMechanismLogging, LoggingMixin, MultiKrum):
    """PRIMARY Krum-family headline comparison (01_Planning, Phase 2
    go-ahead): num_nodes_to_select = n_silos - num_malicious_nodes,
    aggregating the top (n-f) least-anomalous clients' updates by weighted
    mean. Never the single-client classical Krum below.
    """


class LoggingKrum(_KrumMechanismLogging, LoggingMixin, Krum):
    """Classical Krum (selects exactly 1 client's raw update as the next
    global model). SECONDARY SANITY CHECK ONLY, per 01_Planning's explicit
    Phase 2 decision -- never plotted or reported as a standalone baseline
    comparable to ByzAgent or to Multi-Krum. Its purpose is solely to check
    whether raw single-client selection agrees with Multi-Krum's selection
    direction; deploying one client's raw local model as the global model
    discards 90% of the fleet's data and introduces a large variance
    confound unrelated to attack detection, which would contaminate any
    later ByzAgent comparison if treated as a full baseline.
    """


class LoggingFedTrimmedAvg(LoggingMixin, FedTrimmedAvg):
    """Coordinate-wise trimmed mean with the ByzAgent side channel and
    per-round, per-silo trim-rate logging attached.

    Mechanism-level logging reimplements the same per-coordinate ranking
    flwr.serverapp.strategy.fedtrimmedavg.trim_mean uses internally (via
    np.partition), but with np.argsort instead so client INDICES are
    recoverable, not just the trimmed VALUES that np.partition/trim_mean
    exposes. Run before super().aggregate_train() (which performs the real,
    destructive ArrayRecord.pop()-based trimming) using only non-destructive
    reads (`record[array_key]`, never `.pop()`), so this side channel cannot
    starve the real aggregation of any layer. No randomness anywhere in the
    computation (a plain per-coordinate rank), so it cannot diverge from
    what trim_mean computes internally moments later -- empirically verified
    to select the identical trimmed-value set as trim_mean on synthetic data
    before being wired in here (see PHASE2_SUMMARY.md). Ties at the trim
    boundary (argsort vs. partition could in principle disagree on which of
    two EXACTLY equal values is "the" boundary one) are a measure-zero event
    for continuous float32 weights and not expected to occur in practice.

    Logs a per-round, per-silo trim COUNT/RATE summary (not raw per-
    coordinate identity), per 01_Planning's Phase 2 decision -- finer
    granularity is regenerable later from round_checkpoints/silo_checkpoints
    if ever needed, same pattern as Phase 0/1's checkpoint-then-replay.
    """

    def __init__(self, *args, trim_log_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.trim_log_path = trim_log_path
        self.trim_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_mechanism(self, server_round: int, replies: list) -> None:
        valid_replies = [m for m in replies if not m.has_error()]
        if not valid_replies:
            return
        reply_contents = [msg.content for msg in valid_replies]
        silo_ids = [int(c["metrics"]["silo_id"]) for c in reply_contents]
        n = len(reply_contents)

        array_keys = list(reply_contents[0][self.arrayrecord_key].keys())
        lowercut = int(self.beta * n)
        uppercut = n - lowercut

        trim_counts = np.zeros(n, dtype=np.int64)
        total_coords = 0

        for array_key in array_keys:
            layers = np.stack([
                reply_contents[i][self.arrayrecord_key][array_key].numpy()
                for i in range(n)
            ])  # (n_clients, *layer_shape) -- non-destructive read, no .pop()
            flat = layers.reshape(n, -1)
            order = np.argsort(flat, axis=0)  # ascending rank per coordinate
            trimmed_positions = np.concatenate([order[:lowercut], order[uppercut:]], axis=0)
            trim_counts += np.bincount(trimmed_positions.ravel(), minlength=n)
            total_coords += flat.shape[1]

        for pos, silo_id in enumerate(silo_ids):
            row = {
                "round": server_round,
                "silo_id": silo_id,
                "trim_count": int(trim_counts[pos]),
                "total_coords": int(total_coords),
                "trim_rate": float(trim_counts[pos] / total_coords) if total_coords else 0.0,
                "beta": self.beta,
            }
            with open(self.trim_log_path, "a") as f:
                f.write(json.dumps(row) + "\n")


class LoggingByzAgent(LoggingMixin, FedAvg):
    """ByzAgent (Phase 3): LLM-based per-round trust decisions over Phase 1's
    5 behavioral stats, via ONE batched Ollama call per round
    (src/agents/byz_agent.py).

    Structural note on cosine_to_global -- read before changing this class.
    Phase 1 defines cosine_to_global as cos(client update, THIS ROUND'S
    ACTUAL AGGREGATED UPDATE) (src/monitoring/client_stats.py). That
    definition is inherently circular for a strategy whose entire point is
    to decide aggregation weights BEFORE the aggregate exists. This class
    resolves the circularity by computing a DIAGNOSTIC PROBE aggregate --
    a plain, un-adjusted FedAvg weighted mean, via FedAvg.aggregate_train()
    directly (NOT super().aggregate_train(), which would re-enter
    LoggingMixin's own aggregate_train and double-log/double-finalize) --
    purely to feed ClientStatsRecorder.finalize_round() the same
    cosine_to_global definition Phase 1 used, so client_stats.jsonl stays
    semantically continuous with the Phase 0-2 runs already on disk (Phase
    4's rolling-history read must not silently start reading two different
    quantities under one column name). The probe aggregate is NEVER shipped
    as the round's actual global model -- once ByzAgent's decisions come
    back, a SEPARATE weighted mean (decisions_to_weights) is computed from
    the same materialized replies and returned instead. This is a Step 2
    implementation choice made to reconcile two already-locked specs
    (Phase 1's stat definition vs. Phase 3's "before aggregation" wiring
    requirement) -- flagged explicitly in the Phase 3 build report, not
    silently decided.

    NO ORACLE. Unlike LoggingMultiKrum/LoggingKrum/LoggingFedTrimmedAvg,
    this class never reads configs/defense.yaml's num_malicious_nodes --
    ByzAgent infers trust purely from the 5 behavioral stats it is handed,
    same asymmetry documented in configs/agent.yaml.

    Zero-weight edge case: if ByzAgent quarantines/zero-weights every
    client in a round, this raises RuntimeError rather than silently
    falling back to an unweighted average of everyone (which would include
    whichever clients were just quarantined) or silently reusing the
    previous round's global model. Not expected to occur in practice with
    a 10-silo fleet; flagged as an open edge case, not resolved by
    assumption -- report to 01_Planning if it ever fires.

    Phase 4 -- rolling history: self._history_rows accumulates every
    finalize_round() row this run has produced so far (in-memory, this
    strategy instance's own lifetime -- one `flwr run` = one instance).
    When agent_cfg.history_mode == "rolling_history", build_client_history()
    slices that accumulated list down to each client's own last
    agent_cfg.history_window rounds and decide_round_history() is called
    instead of decide_round(). When agent_cfg.history_mode ==
    "current_round" (default), this buffer is still accumulated (cheap --
    it's already been returned by finalize_round() either way) but never
    read, so the current-round-only path is byte-for-byte Phase 3's
    behavior. This in-memory list is the live-run counterpart to reading
    client_stats.jsonl off disk in a retrospective replay -- both feed the
    same build_client_history() pure function the same row shape, so the
    two never diverge in what "the last N rounds" means.
    """

    def __init__(self, *args, agent_cfg: AgentConfig, agent_decisions_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_cfg = agent_cfg
        self.agent_decisions_path = agent_decisions_path
        self.agent_decisions_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_rows: list[dict] = []

    def aggregate_train(self, server_round: int, replies):
        replies = self._pre_aggregate_train_logging(server_round, replies)

        probe_arrays, probe_metrics = FedAvg.aggregate_train(self, server_round, replies)
        if probe_arrays is None:
            # No successful replies this round -- nothing to decide on,
            # nothing to aggregate. Matches the base strategy's own
            # behavior; ClientStatsRecorder.finalize_round is never called
            # for a round with zero results (its own guard would fire).
            return probe_arrays, probe_metrics

        stat_rows = self.stats_recorder.finalize_round(probe_arrays.to_torch_state_dict())
        stats_by_silo = {int(row["silo_id"]): row for row in stat_rows}
        # Accumulated regardless of history_mode -- see class docstring.
        # Cheap (stat_rows already exists) and keeps the current-round-only
        # path free of any dependence on this list ever being read.
        self._history_rows.extend(stat_rows)

        valid_replies = [m for m in replies if not m.has_error()]
        num_examples: dict[str, int] = {}
        client_states: dict[str, dict] = {}
        client_stats_for_prompt = []
        for msg in valid_replies:
            silo_id = int(msg.content["metrics"]["silo_id"])
            client_id = f"silo_{silo_id}"
            row = stats_by_silo[silo_id]
            num_examples[client_id] = int(msg.content["metrics"]["num-examples"])
            client_states[client_id] = msg.content[self.arrayrecord_key].to_torch_state_dict()
            client_stats_for_prompt.append({
                "client_id": client_id,
                "update_norm": row["update_norm"],
                "cosine_to_global": row["cosine_to_global"],
                "cosine_to_peer_mean": row["cosine_to_peer_mean"],
                "train_loss": row["train_loss"],
                "val_accuracy": row["val_accuracy"],
            })

        # Phase 4: current_round (Phase 3 baseline, byte-for-byte unchanged)
        # vs rolling_history (build_client_history slices self._history_rows,
        # which by construction already includes this round's just-appended
        # stat_rows, down to each client's own last history_window rounds).
        if self.agent_cfg.history_mode == "rolling_history":
            client_history_for_prompt = build_client_history(
                self._history_rows, current_round=server_round, window=self.agent_cfg.history_window,
            )
            decisions, _prompt, _raw_response = decide_round_history(
                server_round, client_history_for_prompt, cfg=self.agent_cfg,
            )
            raw_stats_by_client = {c["client_id"]: c for c in client_history_for_prompt}
        else:
            decisions, _prompt, _raw_response = decide_round(
                server_round, client_stats_for_prompt, cfg=self.agent_cfg,
            )
            raw_stats_by_client = {c["client_id"]: c for c in client_stats_for_prompt}
        log_decisions(self.agent_decisions_path, server_round, decisions, raw_stats_by_client)

        weights = decisions_to_weights(
            decisions, num_examples, downweight_multiplier=self.agent_cfg.downweight_multiplier,
        )
        total_weight = sum(weights.values())
        if total_weight <= 0.0:
            raise RuntimeError(
                f"ByzAgent quarantined/zero-weighted every client in round "
                f"{server_round} (weights={weights}) -- refusing to silently "
                f"fall back to an unweighted average or reuse the previous "
                f"round's global model. This is an unresolved edge case; "
                f"flag to 01_Planning rather than working around it here."
            )

        # Actual weighted-mean aggregation using ByzAgent's decisions -- THIS
        # ships as the round's real global model, not the probe aggregate
        # above. float64 accumulation, cast back to each tensor's original
        # dtype at the end (state_dicts are float32 in this project).
        orig_dtypes = {k: v.dtype for k, v in next(iter(client_states.values())).items()}
        agg_state: dict | None = None
        for client_id, state in client_states.items():
            w = weights[client_id] / total_weight
            if w == 0.0:
                continue
            if agg_state is None:
                agg_state = {k: v.detach().to(torch.float64) * w for k, v in state.items()}
            else:
                for k, v in state.items():
                    agg_state[k] += v.detach().to(torch.float64) * w
        agg_state = {k: v.to(orig_dtypes[k]) for k, v in agg_state.items()}

        return ArrayRecord(agg_state), probe_metrics


app = ServerApp()


@app.main()
def main(grid: Grid, context: Context) -> None:
    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")

    alpha = str(context.run_config["alpha"])
    seed = int(context.run_config["seed"])
    num_rounds = int(context.run_config["num-server-rounds"])
    local_epochs = int(context.run_config["local-epochs"])
    mu = float(context.run_config.get("mu", 0.0))
    fraction_train = float(context.run_config["fraction-train"])
    fraction_evaluate = float(context.run_config["fraction-evaluate"])

    n_silos = int(data_cfg["federation"]["n_silos"])

    # ByzAgent Phase 0: if configs/attack.yaml has attack.enabled: true, this
    # run is a poisoned experiment. Two consequences enforced below:
    #   1. its results land in a directory that can never collide with a
    #      clean run's (same alpha/seed can be both attacked and clean);
    #   2. it must never evaluate against test_global.parquet -- the test
    #      set has already been spent producing the locked baseline numbers
    #      in results/aggregated/, and a Phase 0 attack sanity check does not
    #      justify spending it again. See the hard guard below, right before
    #      the test-evaluation block. This guard is unconditional on
    #      attack_enabled alone -- it does not look at which Strategy is
    #      constructed further down, so it fires identically regardless of
    #      whether this run uses LoggingFedAvg, LoggingMultiKrum,
    #      LoggingKrum, or LoggingFedTrimmedAvg.
    attack_full_cfg = load_yaml("configs/attack.yaml")
    attack_cfg = attack_full_cfg["attack"]
    attack_enabled = bool(attack_cfg.get("enabled", False))

    # ByzAgent Phase 2: robust-aggregation strategy selection.
    # configs/defense.yaml, separate file, mirrors configs/attack.yaml's
    # convention -- Contribution B stays visibly distinct from Contribution
    # A (plain FedAvg with defense.strategy left at "fedavg").
    defense_full_cfg = load_yaml("configs/defense.yaml")
    defense_cfg = defense_full_cfg["defense"]
    strategy_name = str(defense_cfg.get("strategy", "fedavg"))
    num_malicious_nodes = int(defense_cfg.get("num_malicious_nodes", 0))

    # ByzAgent (Phase 3): separate config file, same convention as
    # configs/attack.yaml / configs/defense.yaml. Loaded unconditionally
    # (cheap, inert unless strategy_name == "byzagent") so agent_cfg is
    # always available below without a second load call inside the branch.
    agent_full_cfg = load_yaml("configs/agent.yaml")
    agent_yaml_cfg = agent_full_cfg["agent"]
    agent_cfg = AgentConfig.from_yaml_dict(agent_yaml_cfg)

    if strategy_name == "fedavg":
        algo = "fedavg" if mu == 0.0 else f"fedprox_mu{mu}"
    elif strategy_name == "multikrum":
        algo = f"multikrum_f{num_malicious_nodes}"
    elif strategy_name == "krum":
        algo = f"krumclassical_f{num_malicious_nodes}"
    elif strategy_name == "trimmed_mean":
        algo = f"trimmedmean_f{num_malicious_nodes}"
    elif strategy_name == "byzagent":
        # NO oracle f suffix -- unlike multikrum/krum/trimmed_mean, ByzAgent
        # is never given num_malicious_nodes (see configs/agent.yaml).
        algo = "byzagent"
    else:
        raise ValueError(
            f"Unknown configs/defense.yaml defense.strategy {strategy_name!r}. "
            f"Expected one of: fedavg, multikrum, krum, trimmed_mean, byzagent."
        )

    tag = f"{algo}_a{alpha}_s{seed}"
    if attack_enabled:
        malicious_silos_for_tag = resolve_malicious_silos(attack_cfg, n_silos)
        silos_suffix = "-".join(str(s) for s in malicious_silos_for_tag)
        # Malicious-silo IDENTITY is part of the tag -- two different triples
        # at the same (alpha, seed, f, mode) must never collide on the same
        # results/federated/{tag}/ directory, or a later poisoned experiment
        # would silently overwrite an earlier one's model_best.pt /
        # round_history.json / attack_val_summary.json.
        tag += f"_poisoned_f{attack_cfg['f']}_{attack_cfg['mode']}_silos{silos_suffix}"
    # ABSOLUTE, never relative -- Flower's simulation backend pins the server
    # thread's cwd to the app source directory (federated/) regardless of
    # where `flwr run` itself was invoked from, so a bare relative
    # model_cfg["output"]["results_dir"] ("results/") silently resolves
    # against the wrong directory (federated/results/...) rather than the
    # project root. load_yaml() above already avoids this exact trap for
    # config loading via _PROJECT_ROOT; this is the same fix applied to the
    # results output path. See MULTISEED_VALIDATION_SUMMARY.md's "output-path
    # bug fix" section for the diagnosis (two separate sessions hit this
    # silently before it was traced here) and the orphaned
    # federated/results/ directories it left behind, deliberately not
    # cleaned up by that fix.
    out_dir = _PROJECT_ROOT / model_cfg["output"]["results_dir"] / "federated" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    # Written unconditionally, before training starts, so the defense
    # configuration survives on disk even for attack_enabled runs that stop
    # at the hard test-guard below (same reasoning as attack_val_summary.json).
    (out_dir / "defense_config.json").write_text(json.dumps({
        "strategy": strategy_name,
        "num_malicious_nodes_oracle": num_malicious_nodes,
        "n_silos": n_silos,
        "note": (
            "num_malicious_nodes is the TRUE f from configs/attack.yaml for "
            "the condition under test -- an ORACLE given to this defense, "
            "not inferred or estimated. Documented advantage, not an "
            "oversight; disclose explicitly wherever this run's results are "
            "shown. multikrum.num_nodes_to_select = n_silos - "
            "num_malicious_nodes; trimmed_mean.beta = num_malicious_nodes / "
            "n_silos. Classical 'krum' (select=1) is a secondary sanity "
            "check only, never a standalone baseline."
        ),
    }, indent=2))

    # ByzAgent provenance, written unconditionally alongside defense_config.json
    # (same "survives even a hard-guard stop" reasoning) whenever this run
    # actually uses byzagent -- inert/absent otherwise.
    if strategy_name == "byzagent":
        (out_dir / "agent_config.json").write_text(json.dumps({
            "provider": agent_yaml_cfg.get("provider", "ollama"),
            "model": agent_cfg.model,
            "host": agent_cfg.host,
            "keep_alive": agent_cfg.keep_alive,
            "temperature": agent_cfg.temperature,
            "max_retries": agent_cfg.max_retries,
            "downweight_multiplier": agent_cfg.downweight_multiplier,
            "history_mode": agent_cfg.history_mode,
            "history_window": agent_cfg.history_window,
            "note": (
                "ByzAgent receives NO oracle f and NO ground-truth malicious-"
                "silo identity, in any form -- unlike multikrum/krum/"
                "trimmed_mean (see defense_config.json's own note), which are "
                "given the TRUE num_malicious_nodes as a documented advantage. "
                "ByzAgent infers trust decisions purely from the behavioral "
                "stats in src/monitoring/client_stats.py -- either this "
                "round's scalar values only (history_mode=current_round, "
                "Phase 3) or each client's own last history_window rounds as "
                "a sequence (history_mode=rolling_history, Phase 4). This "
                "asymmetry is intentional and must be disclosed explicitly "
                "wherever this run's results are shown."
            ),
        }, indent=2))

    # Chat 04 Pre-check A: only best/last were saved previously, so
    # intermediate global checkpoints did not exist and silo-local
    # reconstruction was impossible. Every round now lands on disk.
    round_ckpt_dir = out_dir / "round_checkpoints"
    round_ckpt_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{tag}] rounds={num_rounds} local_epochs={local_epochs} mu={mu} "
          f"fraction_train={fraction_train} fraction_evaluate={fraction_evaluate} "
          f"defense_strategy={strategy_name} num_malicious_nodes_oracle={num_malicious_nodes}")

    # Loaded ONCE here, reused every round via closure. Both val and test come
    # from the identical centralized split the MLP baseline used, so the
    # federated-vs-centralized comparison is apples-to-apples.
    print("\nLoading centralized split for server-side evaluation ...")
    centralized = load_centralized_for_server(data_cfg, model_cfg)
    X_val, y_val = centralized.X_val, centralized.y_val
    X_test, y_test = centralized.X_test, centralized.y_test
    cnames = class_names(model_cfg)
    headline_idx = headline_class_indices(model_cfg)
    headline_names = list(model_cfg["labels"]["headline_classes"])
    n_classes = int(model_cfg["labels"]["n_classes"])
    print(f"  {centralized.summary()}")

    global_model = build_model(model_cfg, seed=seed, device="cpu")
    initial_arrays = ArrayRecord(global_model.state_dict())

    round_history: list[dict] = []
    best = {"round": -1, "val_macro_f1_headline": -1.0, "state": None}

    def global_evaluate(server_round: int, arrays: ArrayRecord, config: dict | None = None):
        """Round-by-round evaluation on the VALIDATION set.

        Deliberately not the test set. FedAvg's global macro-F1 oscillates
        substantially between rounds under non-IID partitioning -- at alpha=0.5
        it swung between 0.86 and 0.97 across consecutive late rounds -- so
        whichever round the budget happens to end on decides the headline
        number. Selecting the best round fixes that, but selecting it on test
        would make every reported test number optimistically biased. Validation
        selection here mirrors the centralized baseline exactly: best checkpoint
        chosen on val macro-F1 over the 7 headline families, test touched once.

        Confirmed against flwr 1.33: called as evaluate_fn(server_round, arrays)
        -- two positional args, no config -- and must return a plain dict.
        """
        model = build_model(model_cfg, seed=seed, device=DEVICE)
        model.load_state_dict(arrays.to_torch_state_dict())
        torch.save(model.state_dict(),
                   round_ckpt_dir / f"round_{server_round:03d}.pt")
        Xv = torch.from_numpy(X_val.copy()).to(DEVICE)
        y_pred = predict(model, Xv).cpu().numpy()
        m = compute_metrics(y_val, y_pred, n_classes, cnames, headline_idx)

        score = m["macro_f1_headline"]
        flag = ""
        if score > best["val_macro_f1_headline"]:
            best["val_macro_f1_headline"] = score
            best["round"] = server_round
            best["state"] = {k: v.detach().cpu().clone()
                             for k, v in model.state_dict().items()}
            flag = "  *"

        round_history.append({
            "round": server_round,
            "val_macro_f1_headline": score,
            "val_macro_f1_all": m["macro_f1_all"],
            "val_false_positive_rate": m["false_positive_rate"],
            "val_attack_recall": m["attack_recall"],
            # ADDITIVE (2026-08-26): full per-class breakdown, so per-family
            # recall and the Benign false-negative rate (1 - attack_recall)
            # are recoverable per round without re-running inference. The 4
            # fields above are unchanged -- nothing downstream that reads
            # only those needs to change.
            "per_class": m["per_class"],
        })
        print(f"  round {server_round:>3}/{num_rounds}  "
              f"val macro-F1 {score:.4f}  FPR {m['false_positive_rate']:.5f}{flag}")

        return {
            "val_macro_f1_headline": score,
            "val_macro_f1_all": m["macro_f1_all"],
            "val_false_positive_rate": m["false_positive_rate"],
            "val_attack_recall": m["attack_recall"],
        }

    # ByzAgent Phase 1: per-client behavioral stats (src/monitoring/client_stats.py).
    # X_val_for_stats is a single persistent DEVICE tensor, built once and reused
    # every round for every client's val_accuracy eval -- separate from
    # global_evaluate's own per-round Xv above so this addition never touches
    # the existing clean-run evaluation path.
    stats_recorder = ClientStatsRecorder(out_path=out_dir / "client_stats.jsonl")
    X_val_for_stats = torch.from_numpy(X_val.copy()).to(DEVICE)

    common_kwargs = dict(
        fraction_train=fraction_train,
        fraction_evaluate=fraction_evaluate,
        silo_ckpt_dir=out_dir / "silo_checkpoints",
        silo_metrics_path=out_dir / "silo_metrics.jsonl",
        stats_recorder=stats_recorder,
        build_model_fn=lambda: build_model(model_cfg, seed=seed, device=DEVICE),
        X_val_tensor=X_val_for_stats,
        y_val=y_val,
    )

    if strategy_name == "fedavg":
        strategy = LoggingFedAvg(**common_kwargs)
    elif strategy_name == "multikrum":
        # PRIMARY headline Krum-family comparison (01_Planning, Phase 2):
        # select n_silos - f least-anomalous clients, weighted-mean them.
        num_to_select = n_silos - num_malicious_nodes
        strategy = LoggingMultiKrum(
            **common_kwargs,
            num_malicious_nodes=num_malicious_nodes,
            num_nodes_to_select=num_to_select,
            krum_log_path=out_dir / "krum_selection.jsonl",
        )
    elif strategy_name == "krum":
        # SECONDARY SANITY CHECK ONLY -- see LoggingKrum's docstring.
        strategy = LoggingKrum(
            **common_kwargs,
            num_malicious_nodes=num_malicious_nodes,
            krum_log_path=out_dir / "krum_selection.jsonl",
        )
    elif strategy_name == "trimmed_mean":
        # beta = f / n_silos, oracle-sized to the true attack strength
        # (01_Planning, Phase 2) -- NOT the library default of 0.2.
        beta = num_malicious_nodes / n_silos
        strategy = LoggingFedTrimmedAvg(
            **common_kwargs,
            beta=beta,
            trim_log_path=out_dir / "trim_rate.jsonl",
        )
    elif strategy_name == "byzagent":
        # NO oracle f passed -- see LoggingByzAgent's docstring and
        # configs/agent.yaml.
        strategy = LoggingByzAgent(
            **common_kwargs,
            agent_cfg=agent_cfg,
            agent_decisions_path=out_dir / "agent_decisions.jsonl",
        )
    else:  # pragma: no cover -- already validated above
        raise ValueError(f"Unknown defense.strategy {strategy_name!r}")

    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays,
        train_config=ConfigRecord({"local-epochs": local_epochs}),
        num_rounds=num_rounds,
        evaluate_fn=global_evaluate,
    )

    print(f"\n  best val macro-F1 {best['val_macro_f1_headline']:.4f} "
          f"at round {best['round']}")

    # Validation-only artifacts, written BEFORE the test-touch guard below so
    # a poisoned run still leaves a usable result on disk even though it
    # stops here. model_best.pt / model_last.pt / round_history.json depend
    # only on training + per-round validation -- test_global.parquet is not
    # involved in producing any of them.
    torch.save(best["state"], out_dir / "model_best.pt")
    torch.save(result.arrays.to_torch_state_dict(), out_dir / "model_last.pt")
    (out_dir / "round_history.json").write_text(json.dumps(round_history, indent=2))

    if attack_enabled:
        (out_dir / "attack_val_summary.json").write_text(json.dumps({
            "tag": tag, "alpha": alpha, "seed": seed, "num_rounds": num_rounds,
            "local_epochs": local_epochs, "mu": mu,
            "attack": {"f": attack_cfg["f"], "mode": attack_cfg["mode"],
                       "strategy": attack_cfg["strategy"]},
            "defense": {"strategy": strategy_name,
                        "num_malicious_nodes_oracle": num_malicious_nodes},
            "best_round": best["round"],
            "best_val_macro_f1_headline": best["val_macro_f1_headline"],
        }, indent=2))
        print(f"\n  written (validation-only): {out_dir}")
        raise RuntimeError(
            f"HARD STOP: configs/attack.yaml has attack.enabled: true "
            f"(f={attack_cfg['f']}, mode={attack_cfg['mode']!r}). Refusing to "
            f"evaluate this poisoned run against test_global.parquet -- the "
            f"test set is already spent on the locked baseline numbers in "
            f"results/aggregated/, and a Phase 0 attack sanity check does "
            f"not justify a second touch. This is a deliberate stop, not a "
            f"crash: validation-only artifacts (model_best.pt, model_last.pt, "
            f"round_history.json, attack_val_summary.json) were already "
            f"written to {out_dir}. Use "
            f"attack_val_summary.json['best_val_macro_f1_headline'] for the "
            f"verification-gate comparison."
        )

    # ---- test evaluated ONCE, on the best-by-validation model (clean runs
    # only -- attack_enabled runs never reach this line, see the guard above) --
    best_model = build_model(model_cfg, seed=seed, device=DEVICE)
    best_model.load_state_dict(best["state"])
    Xt = torch.from_numpy(X_test.copy()).to(DEVICE)
    y_pred = predict(best_model, Xt).cpu().numpy()
    best_m = compute_metrics(y_test, y_pred, n_classes, cnames, headline_idx)

    print("\nBEST-BY-VALIDATION GLOBAL MODEL, centralized test set\n"
          + format_per_class(best_m, headline_names))

    # The last round is also reported, separately. The gap between the two is
    # the size of the round-lottery effect and belongs in the paper as a
    # stability observation, not hidden behind the selected number.
    last_model = build_model(model_cfg, seed=seed, device=DEVICE)
    last_model.load_state_dict(result.arrays.to_torch_state_dict())
    y_pred_last = predict(last_model, Xt).cpu().numpy()
    last_m = compute_metrics(y_test, y_pred_last, n_classes, cnames, headline_idx)
    print(f"  final-round test macro-F1 (not selected): "
          f"{last_m['macro_f1_headline']:.4f}")

    (out_dir / "final_metrics.json").write_text(json.dumps({
        "alpha": alpha, "seed": seed, "num_rounds": num_rounds,
        "local_epochs": local_epochs, "mu": mu,
        "best_round": best["round"],
        "best_val_macro_f1_headline": best["val_macro_f1_headline"],
        "test": best_m,
        "test_final_round_unselected": last_m,
        "class_names": cnames,
        "headline_classes": headline_names,
    }, indent=2))
    (out_dir / "config.json").write_text(json.dumps({
        "alpha": alpha, "seed": seed, "num_rounds": num_rounds,
        "local_epochs": local_epochs, "mu": mu, "fraction_train": fraction_train,
        "fraction_evaluate": fraction_evaluate,
        "defense_strategy": strategy_name,
        "num_malicious_nodes_oracle": num_malicious_nodes,
    }, indent=2))

    print(f"\n  written: {out_dir}")
