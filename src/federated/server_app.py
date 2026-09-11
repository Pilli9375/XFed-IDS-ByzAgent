"""Flower ServerApp for XFed-IDS. Orchestrates FedAvg/FedProx across 10 silos.

All 10 silos participate every round (locked decision 5: no minimum silo size,
no exclusion from training). fraction_train=1.0 and min_available_nodes equal
to the full cohort enforce this rather than leaving it to Flower's sampling.

Two evaluations happen after strategy.start() completes, and they answer
different questions:
  - global_test: the final model evaluated ONCE on pooled test_global.parquet,
    via the exact same compute_metrics() call the MLP/XGBoost baselines use.
    THIS is the number comparable to the centralized 0.9900 +/- 0.0022.
  - per_silo: the same final model evaluated separately on each silo's own
    test partition. A finding (per xfed-code: client-level divergence is a
    finding, not noise), not a substitute for global_test.

Place at: src/federated/server_app.py
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import torch
from flwr.app import ArrayRecord, Context
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg, FedProx

from ..data.loaders import load_centralized, load_silo, to_device_tensors
from ..data.schema import headline_class_indices, load_yaml
from ..models.mlp import build_model
from ..train.metrics import compute_metrics, confusion, format_per_class

app = ServerApp()


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


@app.main()
def main(grid: Grid, context: Context) -> None:
    rc = context.run_config
    data_cfg = load_yaml("configs/data.yaml")
    model_cfg = load_yaml("configs/model.yaml")

    alpha = str(rc["alpha"])
    seed = int(rc["seed"])
    strategy_name = str(rc.get("strategy", "fedavg")).lower()
    num_rounds = int(rc["num-rounds"])
    n_silos = int(rc.get("n-silos", 10))
    tag = str(rc.get("tag", f"{strategy_name}_a{alpha}_s{seed}"))

    print(f"\n[{tag}] alpha={alpha} seed={seed} strategy={strategy_name} "
          f"rounds={num_rounds} n_silos={n_silos} git={git_hash()}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(model_cfg, seed=seed, device=device)
    arrays = ArrayRecord(model.state_dict())
    print(f"  initial model: {model.n_parameters():,} parameters")

    common = dict(
        fraction_train=1.0,
        fraction_evaluate=1.0,
        min_train_nodes=n_silos,
        min_evaluate_nodes=n_silos,
        min_available_nodes=n_silos,
    )
    if strategy_name == "fedavg":
        strategy = FedAvg(**common)
    elif strategy_name == "fedprox":
        strategy = FedProx(proximal_mu=float(rc.get("proximal-mu", 0.1)), **common)
    else:
        raise ValueError(f"unknown strategy {strategy_name!r}")

    print(f"\nTraining {num_rounds} rounds, all {n_silos} silos every round ...\n")
    t0 = time.time()
    result = strategy.start(grid=grid, initial_arrays=arrays, num_rounds=num_rounds)
    elapsed = time.time() - t0
    print(f"\n  federation finished in {elapsed:.0f}s")
    # Printed so we can see the Result object's actual shape if the
    # `result.metrics` access below needs adjusting.
    print(f"  result object: {result}")

    # ---- final global model: evaluate on the pooled centralized test set --
    final_model = build_model(model_cfg, seed=seed, device=device)
    final_model.load_state_dict(result.arrays.to_torch_state_dict())
    final_model.eval()

    centralized_splits = load_centralized(data_cfg, model_cfg)
    tensors = to_device_tensors(centralized_splits, device)
    X_te, y_te = tensors["test"]

    n_classes = int(model_cfg["labels"]["n_classes"])
    headline_idx = headline_class_indices(model_cfg)
    headline_names = list(model_cfg["labels"]["headline_classes"])

    with torch.no_grad():
        y_pred = final_model(X_te).argmax(dim=1).cpu().numpy()
    global_test_m = compute_metrics(
        y_te.cpu().numpy(), y_pred, n_classes, centralized_splits.class_names, headline_idx
    )
    print("\nFINAL GLOBAL MODEL on pooled centralized test set\n"
          + format_per_class(global_test_m, headline_names))

    # ---- per-silo evaluation of the SAME final global model ----------------
    per_silo = {}
    print("\nper-silo (same final global model):")
    for silo_id in range(n_silos):
        s = load_silo(silo_id, alpha, seed, data_cfg, model_cfg)
        t = to_device_tensors(s, device)
        X_s, y_s = t["test"]
        with torch.no_grad():
            yp = final_model(X_s).argmax(dim=1).cpu().numpy()
        sm = compute_metrics(y_s.cpu().numpy(), yp, n_classes, s.class_names, headline_idx)
        per_silo[silo_id] = {
            "macro_f1_headline": sm["macro_f1_headline"],
            "false_positive_rate": sm["false_positive_rate"],
            "n_test": int(len(y_s)),
            "portscan_recall": sm["per_class"].get("PortScan", {}).get("recall"),
        }
        print(f"  silo {silo_id}: macro-F1 {sm['macro_f1_headline']:.4f}  "
              f"n={len(y_s):>7,}  PortScan recall {per_silo[silo_id]['portscan_recall']}")

    # ---- artifacts -----------------------------------------------------------
    out_dir = Path(model_cfg["output"]["results_dir"]) / "federated" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "config.json").write_text(json.dumps({
        "tag": tag, "alpha": alpha, "seed": seed, "strategy": strategy_name,
        "num_rounds": num_rounds, "n_silos": n_silos, "git_commit": git_hash(),
        "elapsed_seconds": round(elapsed, 1),
    }, indent=2))

    (out_dir / "metrics.json").write_text(json.dumps({
        "global_test": global_test_m,
        "global_test_confusion_matrix": confusion(y_te.cpu().numpy(), y_pred, n_classes),
        "per_silo": per_silo,
    }, indent=2, default=str))

    torch.save(final_model.state_dict(), out_dir / "model.pt")
    print(f"\n  written: {out_dir}")
