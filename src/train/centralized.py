"""Centralized MLP baseline. One run = one artifact directory.

Every CLI override exists so the pilots and the architecture sweep are the same
training loop with different config, rather than three near-duplicate scripts.
The Flower client will later call the same build_model and the same loaders.

Place at: src/train/centralized.py
Run as:   python -m src.train.centralized --tag smoke --max-epochs 2

Artifacts written to results/centralized/<tag>/:
    config.json        exact resolved config, overrides included
    metrics.json       final val + test metrics, per-class
    history.csv        per-epoch train loss and val metrics
    model.pt           best weights by val headline macro-F1
    scaler.npz         center, scale, clip bounds, degenerate feature list
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from ..data.loaders import load_centralized, to_device_tensors
from ..data.schema import headline_class_indices, load_yaml
from ..models.mlp import build_model
from .metrics import compute_metrics, confusion, format_per_class


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def set_seed(seed: int) -> None:
    """Seeded everywhere, cuDNN pinned to deterministic kernels.

    benchmark=False costs some speed by disabling kernel autotuning. For a model
    this small the loss is negligible and re-runnability is worth more.
    """
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


@torch.no_grad()
def predict(model: nn.Module, X: torch.Tensor, batch_size: int = 8192) -> torch.Tensor:
    """Batched inference. The test split is 478k rows; a single forward pass
    would allocate a 478k x 256 activation tensor for no reason."""
    model.eval()
    out = []
    for i in range(0, len(X), batch_size):
        out.append(model(X[i:i + batch_size]).argmax(dim=1))
    return torch.cat(out)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data-config", type=Path, default=Path("configs/data.yaml"))
    p.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    p.add_argument("--data-root", type=Path, default=Path("data/processed"))
    p.add_argument("--tag", default="default", help="Artifact subdirectory name.")

    # Pilot / sweep axes. None means "use the config value".
    p.add_argument("--scaler", choices=["standard", "robust", "robust_clipped"], default=None)
    p.add_argument("--weight-scheme", choices=["none", "inverse_sqrt", "effective_number"], default=None)
    p.add_argument("--beta", type=float, default=None)
    p.add_argument("--hidden-dims", type=int, nargs="+", default=None)
    p.add_argument("--dropout", type=float, default=None)
    p.add_argument("--lr", type=float, default=None)
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--max-epochs", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)

    p.add_argument("--subsample", type=int, default=None,
                   help="Train on N stratified rows. For fast pilots only -- never for a reported number.")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def apply_overrides(model_cfg: dict, args: argparse.Namespace) -> dict:
    if args.scaler:        model_cfg["preprocessing"]["scaler"] = args.scaler
    if args.hidden_dims:   model_cfg["model"]["hidden_dims"] = args.hidden_dims
    if args.dropout is not None:   model_cfg["model"]["dropout"] = args.dropout
    if args.weight_scheme: model_cfg["training"]["class_weighting"]["scheme"] = args.weight_scheme
    if args.beta is not None:      model_cfg["training"]["class_weighting"]["beta"] = args.beta
    if args.lr is not None:        model_cfg["training"]["lr"] = args.lr
    if args.batch_size:    model_cfg["training"]["batch_size"] = args.batch_size
    if args.max_epochs:    model_cfg["training"]["max_epochs"] = args.max_epochs
    return model_cfg


def stratified_subsample(y: np.ndarray, n: int, seed: int) -> np.ndarray:
    """Proportional sample keeping at least one row of every present class."""
    rng = np.random.default_rng(seed)
    keep: list[np.ndarray] = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        take = max(1, int(round(len(idx) * n / len(y))))
        keep.append(rng.choice(idx, size=min(take, len(idx)), replace=False))
    out = np.concatenate(keep)
    rng.shuffle(out)
    return out


def main() -> int:
    args = parse_args()
    data_cfg = load_yaml(args.data_config)
    model_cfg = apply_overrides(load_yaml(args.model_config), args)

    seed = args.seed if args.seed is not None else int(model_cfg["training"]["seeds"][0])
    set_seed(seed)

    tr = model_cfg["training"]
    device = torch.device(args.device)
    out_dir = Path(model_cfg["output"]["results_dir"]) / "centralized" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{args.tag}] seed={seed} device={device} git={git_hash()}")

    # ---- data ------------------------------------------------------------
    print("\nLoading ...")
    splits = load_centralized(data_cfg, model_cfg, args.data_root)
    print(f"  {splits.summary()}")

    if args.subsample:
        keep = stratified_subsample(splits.y_train, args.subsample, seed)
        splits.X_train, splits.y_train = splits.X_train[keep], splits.y_train[keep]
        print(f"  SUBSAMPLED to {len(keep):,} train rows -- pilot only, not a reportable run")

    tensors = to_device_tensors(splits, device)
    X_tr, y_tr = tensors["train"]
    X_va, y_va = tensors["val"]
    X_te, y_te = tensors["test"]

    class_names = splits.class_names
    headline_idx = headline_class_indices(model_cfg)
    headline_names = list(model_cfg["labels"]["headline_classes"])
    n_classes = int(model_cfg["labels"]["n_classes"])

    weights = torch.from_numpy(splits.class_weights).to(device)
    print(f"  class weights: {dict(zip(class_names, splits.class_weights.round(4)))}")

    # ---- model -----------------------------------------------------------
    model = build_model(model_cfg, seed, device)
    print(f"\nModel: {model_cfg['model']['hidden_dims']} | {model.n_parameters():,} parameters")

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=float(tr["lr"]), weight_decay=float(tr["weight_decay"])
    )
    sched_cfg = tr["lr_schedule"]
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=float(sched_cfg["factor"]),
        patience=int(sched_cfg["patience"]),
    )

    batch_size = int(tr["batch_size"])
    max_epochs = int(tr["max_epochs"])
    patience = int(tr["early_stopping"]["patience"])

    # ---- train -----------------------------------------------------------
    best_score, best_epoch, best_state = -1.0, -1, None
    history: list[dict] = []
    n_train = len(y_tr)
    t0 = time.time()

    print(f"\nTraining up to {max_epochs} epochs, early stop patience {patience} "
          f"on val macro-F1 over the {len(headline_idx)} headline families\n")

    for epoch in range(1, max_epochs + 1):
        model.train()
        perm = torch.randperm(n_train, device=device)
        total_loss = 0.0

        for i in range(0, n_train, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(X_tr[idx]), y_tr[idx])
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)

        train_loss = total_loss / n_train
        val_m = compute_metrics(
            y_va.cpu().numpy(), predict(model, X_va).cpu().numpy(),
            n_classes, class_names, headline_idx,
        )
        score = val_m["macro_f1_headline"]
        scheduler.step(score)

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_macro_f1_headline": score,
            "val_macro_f1_all": val_m["macro_f1_all"],
            "val_false_positive_rate": val_m["false_positive_rate"],
            "lr": optimizer.param_groups[0]["lr"],
        })

        flag = ""
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            flag = "  *"
        print(f"  epoch {epoch:>3}  loss {train_loss:.4f}  val macro-F1 {score:.4f}"
              f"  FPR {val_m['false_positive_rate']:.5f}{flag}")

        if epoch - best_epoch >= patience:
            print(f"\n  early stop: no improvement in {patience} epochs")
            break

    elapsed = time.time() - t0
    print(f"\n  best val macro-F1 {best_score:.4f} at epoch {best_epoch}  ({elapsed:.0f}s)")

    # ---- evaluate the best checkpoint, once -------------------------------
    model.load_state_dict(best_state)
    y_true = y_te.cpu().numpy()
    y_pred = predict(model, X_te).cpu().numpy()
    test_m = compute_metrics(y_true, y_pred, n_classes, class_names, headline_idx)

    print("\nTEST\n" + format_per_class(test_m, headline_names))

    # ---- artifacts --------------------------------------------------------
    (out_dir / "config.json").write_text(json.dumps({
        "tag": args.tag, "seed": seed, "git_commit": git_hash(),
        "device": str(device), "elapsed_seconds": round(elapsed, 1),
        "subsampled_to": args.subsample,
        "model_config": model_cfg,
    }, indent=2, default=str))

    (out_dir / "metrics.json").write_text(json.dumps({
        "best_epoch": best_epoch,
        "best_val_macro_f1_headline": best_score,
        "test": test_m,
        "test_confusion_matrix": confusion(y_true, y_pred, n_classes),
        "class_names": class_names,
    }, indent=2))

    with (out_dir / "history.csv").open("w", newline="") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=list(history[0]))
        w.writeheader()
        w.writerows(history)

    torch.save(best_state, out_dir / "model.pt")
    np.savez(
        out_dir / "scaler.npz",
        kind=splits.scaler_kind, center=splits.scaler_center, scale=splits.scaler_scale,
        clip_lo=splits.clip_lo if splits.clip_lo is not None else np.array([]),
        clip_hi=splits.clip_hi if splits.clip_hi is not None else np.array([]),
        degenerate=np.array(splits.degenerate_scale_features),
        feature_names=np.array(splits.feature_names),
    )

    print(f"\n  written: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
