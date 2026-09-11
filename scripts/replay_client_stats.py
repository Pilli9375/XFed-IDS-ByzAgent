#!/usr/bin/env python
"""Retrospective replay of Phase 1 per-client behavioral stats.

ByzAgent Contribution B, Phase 1 verification-gate support. Computes
client_stats.jsonl (src/monitoring/client_stats.py) for a federated run that
already completed BEFORE client_stats.py existed -- using its saved
round_checkpoints/ (every round's post-aggregation global model) and
silo_checkpoints/ (every client's post-training model, every round) --
so nothing is retrained.

Same retrospective-replay pattern Phase 0 used for
results/inspection/retro_replay_val_metrics_a0.5_s42.json: those checkpoints
were already written by LoggingFedAvg (see federated/xfed_federated/
server_app.py) for every run in results/federated/, clean or poisoned, so
this script works unmodified on either.

Usage:
    python scripts/replay_client_stats.py --run-dir results/federated/fedavg_a0.5_s42
    python scripts/replay_client_stats.py --run-dir results/federated/fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# pyarrow MUST be imported before torch in this environment -- importing
# torch first and then touching pyarrow.parquet (as load_centralized() does
# internally) causes a native access violation (Windows DLL load-order
# conflict between torch's and pyarrow's bundled runtimes). This is a
# standalone-script-only concern: the actual `flwr run` harness never hit
# this because Flower's own bootstrapping imports arrow-adjacent deps first.
import pyarrow.parquet as _pq  # noqa: F401,E402

import torch  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import load_centralized  # noqa: E402
from src.data.schema import load_yaml  # noqa: E402
from src.models.mlp import build_model  # noqa: E402
from src.monitoring.client_stats import ClientStatsRecorder  # noqa: E402


def load_silo_metrics(run_dir: Path) -> dict[tuple[int, int], dict]:
    """(round, silo_id) -> {"train_loss", "num_examples"} from the
    train-phase rows already logged in silo_metrics.jsonl -- no need to
    recompute training loss, it was captured live."""
    out: dict[tuple[int, int], dict] = {}
    with open(run_dir / "silo_metrics.jsonl") as f:
        for line in f:
            row = json.loads(line)
            if row["phase"] != "train":
                continue
            out[(row["round"], row["silo_id"])] = {
                "train_loss": row["train_loss"],
                "num_examples": row["num_examples"],
            }
    return out


def resolve_seed(run_dir: Path) -> int:
    """config.json exists for clean runs; attack_val_summary.json for
    poisoned runs (attack_enabled runs stop before config.json is written --
    see the hard test-guard in server_app.py). Both carry "seed"."""
    for name in ("config.json", "attack_val_summary.json"):
        p = run_dir / name
        if p.exists():
            return int(json.loads(p.read_text())["seed"])
    raise FileNotFoundError(
        f"neither config.json nor attack_val_summary.json found in {run_dir} -- "
        f"cannot determine which seed built this run's model."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--data-config", default="configs/data.yaml")
    ap.add_argument("--model-config", default="configs/model.yaml")
    ap.add_argument("--n-silos", type=int, default=10)
    args = ap.parse_args()

    run_dir = args.run_dir
    data_cfg = load_yaml(PROJECT_ROOT / args.data_config)
    model_cfg = load_yaml(PROJECT_ROOT / args.model_config)
    seed = resolve_seed(run_dir)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[{run_dir.name}] seed={seed} device={device}")

    print("Loading centralized validation split (identical for clean and "
          "poisoned runs -- the attack never touches val/test) ...")
    centralized = load_centralized(data_cfg, model_cfg, root=PROJECT_ROOT / "data" / "processed")
    X_val = torch.from_numpy(centralized.X_val.copy()).to(device)
    y_val = centralized.y_val
    print(f"  val set: {len(y_val):,} rows")

    silo_metrics = load_silo_metrics(run_dir)

    round_ckpt_dir = run_dir / "round_checkpoints"
    silo_ckpt_dir = run_dir / "silo_checkpoints"
    round_numbers = sorted(
        int(p.stem.split("_")[1]) for p in round_ckpt_dir.glob("round_*.pt")
    )
    max_round = max(round_numbers)
    if round_numbers != list(range(0, max_round + 1)):
        raise ValueError(
            f"{round_ckpt_dir} is missing round checkpoints -- found {round_numbers}, "
            f"expected a contiguous 0..{max_round}. Refusing to replay against gaps."
        )

    out_path = run_dir / "client_stats.jsonl"
    if out_path.exists():
        out_path.unlink()  # fresh replay -- avoid appending duplicate rows on rerun
    recorder = ClientStatsRecorder(out_path=out_path)

    def build() -> torch.nn.Module:
        m = build_model(model_cfg, seed=seed, device=device)
        m.eval()
        return m

    for r in range(1, max_round + 1):
        prev_state = torch.load(round_ckpt_dir / f"round_{r - 1:03d}.pt", map_location=device)
        agg_state = torch.load(round_ckpt_dir / f"round_{r:03d}.pt", map_location=device)

        recorder.start_round(r, prev_state)
        n_seen = 0
        for s in range(args.n_silos):
            silo_path = silo_ckpt_dir / f"round_{r:03d}_silo_{s}.pt"
            if not silo_path.exists():
                # fraction_train=1.0 in every locked run -- a missing file here
                # would mean a silo dropped out, which changes what "10 silos"
                # means for this round and must be visible, not silently skipped.
                raise FileNotFoundError(
                    f"{silo_path} missing -- expected all {args.n_silos} silos "
                    f"to have trained this round (fraction_train=1.0)."
                )
            client_state = torch.load(silo_path, map_location=device)
            model = build()
            model.load_state_dict(client_state)
            with torch.no_grad():
                y_pred = model(X_val).argmax(dim=1).cpu().numpy()
            val_accuracy = float((y_pred == y_val).mean())

            meta = silo_metrics[(r, s)]
            recorder.record_client(
                silo_id=s,
                client_state=client_state,
                num_examples=meta["num_examples"],
                train_loss=meta["train_loss"],
                val_accuracy=val_accuracy,
            )
            n_seen += 1

        recorder.finalize_round(agg_state)
        print(f"  round {r:>3}/{max_round}  {n_seen} silos replayed")

    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
