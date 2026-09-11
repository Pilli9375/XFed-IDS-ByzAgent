"""Patch server_app.py and client_app.py for per-silo, per-round logging.

Chat 04: cross-silo explanation agreement needs each silo's own post-local-
training model at the analysis round, plus per-silo eval metrics per round.
Plain FedAvg.aggregate_train/aggregate_evaluate only ever return the
fleet-wide aggregate -- individual client replies are gone once those
functions return. This patch:

  client_app.py -- stamps silo_id into the MetricRecord each client already
    returns (Message.metadata.src_node_id is Flower's internal node id, NOT
    the silo_id 0-9 this project uses -- do not use it for silo identity).

  server_app.py -- adds LoggingFedAvg(FedAvg), which captures each reply's
    arrays + metrics on the way through aggregate_train/aggregate_evaluate,
    then calls super() unchanged. The federated result itself is byte-for-
    byte identical to plain FedAvg; only a side channel is added.

Verified against the installed flwr.serverapp.strategy.FedAvg source
(pasted back by the user) before writing this -- not guessed.

Run from project root: python tools/apply_silo_logging_patch.py
Requires: apply_checkpoint_patch.py must have already been run once
(this patch does not depend on it, but assumes the strategy-construction
line is still untouched, which it is).
"""
from __future__ import annotations
from pathlib import Path
import shutil

SERVER_TARGET = Path("federated/xfed_federated/server_app.py")
CLIENT_TARGET = Path("federated/xfed_federated/client_app.py")


def patch_file(target: Path, replacements: list[tuple[str, str]]) -> bool:
    if not target.exists():
        print(f"NOT FOUND: {target.resolve()}")
        return False
    text = target.read_text()

    for old, _ in replacements:
        if old not in text:
            print(f"PATTERN NOT FOUND in {target.name} -- file may already be "
                  f"patched, or has drifted. No changes made to this file.")
            print(f"  missing pattern (first 80 chars): {old[:80]!r}")
            return False

    backup = target.with_suffix(".py.bak2")
    shutil.copy(target, backup)
    for old, new in replacements:
        text = text.replace(old, new, 1)
    target.write_text(text)
    print(f"Patched: {target}")
    print(f"Backup saved: {backup}")
    return True


# ---------------------------------------------------------------------------
# server_app.py
# ---------------------------------------------------------------------------

SERVER_LOGGING_FEDAVG_CLASS = '''
class LoggingFedAvg(FedAvg):
    """FedAvg that also persists per-silo local weights and metrics every
    round, before aggregation discards them.

    Chat 04 (Pre-check A/B/C): cross-silo explanation agreement needs each
    silo's own post-local-training model at a chosen round, and plain
    FedAvg.aggregate_train/aggregate_evaluate only ever return the
    fleet-wide aggregate -- individual replies are gone once those
    functions return. This subclass captures each reply on the way
    through, then calls super().aggregate_train/aggregate_evaluate()
    unchanged, so the actual federated result is byte-for-byte identical
    to plain FedAvg -- only a side channel is added.

    Verified against the installed flwr.serverapp.strategy.FedAvg source:
    aggregate_train(server_round, replies: Iterable[Message]) receives raw
    per-client Messages before averaging; each Message.content is a
    RecordDict with "arrays" (train phase only) and "metrics" keys,
    matching what client_app.py's train()/evaluate() construct. Messages
    can carry an error instead of content (msg.has_error()) -- skipped
    here exactly as FedAvg's own _check_and_log_replies does.

    silo_id is read from the client's own MetricRecord, NOT from
    Message.metadata.src_node_id -- the latter is Flower's internal node
    id, not the partition-id (0-9) this project's silo identity is
    defined by. client_app.py stamps "silo_id" into every MetricRecord it
    returns for exactly this reason.
    """

    def __init__(self, *args, silo_ckpt_dir: Path, silo_metrics_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.silo_ckpt_dir = silo_ckpt_dir
        self.silo_metrics_path = silo_metrics_path
        self.silo_ckpt_dir.mkdir(parents=True, exist_ok=True)
        self.silo_metrics_path.parent.mkdir(parents=True, exist_ok=True)

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
                f.write(json.dumps(row) + "\\n")

    def aggregate_train(self, server_round: int, replies):
        replies = list(replies)  # materialize -- consumed twice (log, then super())
        self._log_replies(server_round, replies, phase="train")
        return super().aggregate_train(server_round, replies)

    def aggregate_evaluate(self, server_round: int, replies):
        replies = list(replies)
        self._log_replies(server_round, replies, phase="evaluate")
        return super().aggregate_evaluate(server_round, replies)


'''

server_replacements = [
    (
        "from __future__ import annotations\n\nimport json\n",
        "from __future__ import annotations\n\nfrom collections.abc import Iterable\nimport json\n",
    ),
    (
        "from flwr.app import ArrayRecord, ConfigRecord, Context\n",
        "from flwr.app import ArrayRecord, ConfigRecord, Context, Message\n",
    ),
    (
        "app = ServerApp()\n",
        SERVER_LOGGING_FEDAVG_CLASS.lstrip("\n") + "\napp = ServerApp()\n",
    ),
    (
        "    strategy = FedAvg(fraction_train=fraction_train, fraction_evaluate=fraction_evaluate)\n",
        (
            "    strategy = LoggingFedAvg(\n"
            "        fraction_train=fraction_train,\n"
            "        fraction_evaluate=fraction_evaluate,\n"
            "        silo_ckpt_dir=out_dir / \"silo_checkpoints\",\n"
            "        silo_metrics_path=out_dir / \"silo_metrics.jsonl\",\n"
            "    )\n"
        ),
    ),
]

# ---------------------------------------------------------------------------
# client_app.py
# ---------------------------------------------------------------------------

client_replacements = [
    (
        '    metric_record = MetricRecord({\n'
        '        "train_loss": train_loss,\n'
        '        "num-examples": len(splits.y_train),\n'
        '    })\n',
        '    metric_record = MetricRecord({\n'
        '        "train_loss": train_loss,\n'
        '        "num-examples": len(splits.y_train),\n'
        '        "silo_id": int(silo_id),\n'
        '    })\n',
    ),
    (
        '    metric_record = MetricRecord({\n'
        '        "num-examples": len(splits.y_test),\n'
        '        "macro_f1_headline": m["macro_f1_headline"],\n'
        '        "false_positive_rate": m["false_positive_rate"],\n'
        '    })\n',
        '    metric_record = MetricRecord({\n'
        '        "num-examples": len(splits.y_test),\n'
        '        "macro_f1_headline": m["macro_f1_headline"],\n'
        '        "false_positive_rate": m["false_positive_rate"],\n'
        '        "silo_id": int(silo_id),\n'
        '    })\n',
    ),
]


def main() -> int:
    ok1 = patch_file(SERVER_TARGET, server_replacements)
    ok2 = patch_file(CLIENT_TARGET, client_replacements)
    if ok1 and ok2:
        print("\nBoth files patched successfully.")
        return 0
    print("\nOne or both files were NOT patched. Do not re-run the sweep yet"
          " -- paste the printed message back before doing anything else.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
