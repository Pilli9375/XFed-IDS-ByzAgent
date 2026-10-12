"""Flower ClientApp -- one simulated organization's silo.

fit() and evaluate() are ephemeral: Flower instantiates a fresh execution of
this module per Message and discards it once the reply is sent. There is no
cross-round state kept here deliberately -- state that mattered (weights)
travels in the Message; state that shouldn't persist (optimizer momentum)
correctly doesn't.
"""

from __future__ import annotations

import os

# Per-silo scaler notes are informative once, but 10 silos x 2 phases x N
# rounds of them buries the results. Counts are still captured in
# Splits.degenerate_scale_features.
os.environ.setdefault("XFED_QUIET_SCALER", "1")

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from xfed_federated.task import (
    DEVICE,
    PoisonedClient,
    build_model,
    evaluate_arrays,
    get_method_name,
    get_server_round,
    headline_class_indices,
    load_global_class_weights,
    load_method,
    load_silo_for_client,
    load_yaml,
    local_train_epochs,
    resolve_malicious_silos,
)

app = ClientApp()


@app.train()
def train(msg: Message, context: Context) -> Message:
    silo_id = int(context.node_config["partition-id"])
    alpha = str(context.run_config["alpha"])
    seed = int(context.run_config["seed"])
    local_epochs = int(context.run_config["local-epochs"])
    mu = float(context.run_config.get("mu", 0.0))
    method_name = get_method_name(context.run_config)
    if method_name:
        # Optimizer-comparison run: mu comes from configs/federated_methods.yaml
        # only. A run-config mu alongside it would be two sources of truth.
        if mu != 0.0:
            raise ValueError(f"method={method_name!r} takes mu from YAML; got run-config mu={mu}")
        _, method = load_method(method_name)
        mu = float(method["client"]["mu"])
        if "local_epochs" in method and local_epochs != int(method["local_epochs"]):
            raise ValueError(f"{method_name}: run-config local-epochs {local_epochs} "
                             f"!= YAML {method['local_epochs']}")

    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")
    class_weights = load_global_class_weights(model_cfg)

    splits = load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)

    # Poisoning, if configured: touches splits.y_train ONLY, before local
    # training. Never val, never test. No-op end to end (including the
    # per-round log) when configs/attack.yaml has attack.enabled: false.
    attack_cfg = load_yaml("configs/attack.yaml")["attack"]
    if attack_cfg.get("enabled", False):
        n_silos = int(data_cfg["federation"]["n_silos"])
        server_round = get_server_round(msg)
        # Malicious-silo IDENTITY is part of the tag, not just f/mode -- two
        # different triples at the same (alpha, seed, f, mode) must never
        # share a results/attacks/{tag}/flip_log.csv, or a later experiment's
        # rows would silently mix into an earlier one's audit trail.
        malicious_silos = resolve_malicious_silos(attack_cfg, n_silos)
        silos_suffix = "-".join(str(s) for s in malicious_silos)
        attack_tag = f"a{alpha}_s{seed}_f{attack_cfg['f']}_{attack_cfg['mode']}_silos{silos_suffix}"
        poisoner = PoisonedClient(attack_cfg, model_cfg, n_silos, alpha, seed, attack_tag)
        splits = poisoner.poison_and_log(splits, silo_id, server_round)

    model = build_model(model_cfg, seed=seed, device=DEVICE)
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())

    train_loss = local_train_epochs(model, splits, local_epochs, model_cfg, mu=mu)

    metric_record = MetricRecord({
        "train_loss": train_loss,
        "num-examples": len(splits.y_train),
        "silo_id": int(silo_id),
    })
    content = RecordDict({
        "arrays": ArrayRecord(model.state_dict()),
        "metrics": metric_record,
    })
    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context) -> Message:
    silo_id = context.node_config["partition-id"]
    alpha = str(context.run_config["alpha"])
    seed = int(context.run_config["seed"])

    # Optimizer-comparison runs set fraction_evaluate = 0.0, so this is never
    # reached. If it were, it would score the candidate on this silo's TEST
    # rows -- refuse rather than rely on the server config alone.
    if get_method_name(context.run_config):
        raise RuntimeError(
            "client evaluate() called in a method run: it scores silo test rows. "
            "Method runs are validation-only; check fraction_evaluate."
        )
    if not bool(context.run_config.get("legacy-client-test-eval", False)):
        raise RuntimeError(
            "client evaluate() scores silo test rows and is off by default "
            "(legacy-client-test-eval=false in federated/pyproject.toml). Set it "
            "true only to reproduce a published run's silo_metrics.jsonl."
        )

    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")
    class_weights = load_global_class_weights(model_cfg)

    splits = load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)

    model = build_model(model_cfg, seed=seed, device=DEVICE)
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())

    headline_idx = headline_class_indices(model_cfg)
    # Evaluated on this silo's own test rows -- per-client divergence is a
    # finding, not noise (xfed-code skill), so this is logged even though the
    # server-side global evaluation on the centralized test set is the number
    # that goes in the headline comparison table.
    m = evaluate_arrays(model, splits.X_test, splits.y_test, model_cfg, headline_idx)

    metric_record = MetricRecord({
        "num-examples": len(splits.y_test),
        "macro_f1_headline": m["macro_f1_headline"],
        "false_positive_rate": m["false_positive_rate"],
        "silo_id": int(silo_id),
    })
    content = RecordDict({"metrics": metric_record})
    return Message(content=content, reply_to=msg)
