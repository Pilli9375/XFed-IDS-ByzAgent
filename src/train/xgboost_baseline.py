"""XGBoost baseline. Full data, tuned hyperparameters, one artifact dir per seed.

Reuses load_centralized, compute_metrics, and format_per_class from the MLP
pipeline so both baselines are scored identically -- same headline/all-9 split,
same false-positive-rate and attack-recall definitions. Early-stops on the same
criterion as the MLP (val macro-F1 over the 7 headline families), which is why
the two baselines' numbers can be compared in one sentence rather than two
different evaluation methodologies being reconciled after the fact.

Place at: src/train/xgboost_baseline.py
Run as:   python -m src.train.xgboost_baseline --tag xgb_s42 --seed 42
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import xgboost as xgb

from ..data.loaders import load_centralized
from ..data.schema import headline_class_indices, load_yaml
from .metrics import compute_metrics, confusion, format_per_class


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def make_feval(n_classes: int, class_names: list[str], headline_idx: np.ndarray):
    def feval(preds: np.ndarray, dtrain: xgb.DMatrix):
        if preds.ndim == 1:
            preds = preds.reshape(-1, n_classes)
        y_true = dtrain.get_label().astype(np.int64)
        y_pred = preds.argmax(axis=1)
        m = compute_metrics(y_true, y_pred, n_classes, class_names, headline_idx)
        return "val_macro_f1_headline", m["macro_f1_headline"]
    return feval


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data-config", type=Path, default=Path("configs/data.yaml"))
    p.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    p.add_argument("--data-root", type=Path, default=Path("data/processed"))
    p.add_argument("--params-file", type=Path, default=Path("configs/xgboost_tuned.json"))
    p.add_argument("--tag", default="xgb_default")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-boost-round", type=int, default=2000)
    p.add_argument("--early-stopping-rounds", type=int, default=30)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    data_cfg = load_yaml(args.data_config)
    model_cfg = load_yaml(args.model_config)
    out_dir = Path(model_cfg["output"]["results_dir"]) / "xgboost" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.params_file.exists():
        tuned = json.loads(args.params_file.read_text())
        params = dict(tuned["params"])
        print(f"\n[{args.tag}] seed={args.seed} git={git_hash()}")
        print(f"  using tuned params from {args.params_file} "
              f"(search val macro-F1: {tuned.get('search_val_macro_f1_headline', 'n/a')})")
    else:
        params = {
            "objective": "multi:softprob", "tree_method": "hist", "device": "cuda",
            "disable_default_eval_metric": 1,
            "max_depth": 6, "learning_rate": 0.1, "subsample": 0.8, "colsample_bytree": 0.8,
        }
        print(f"\n[{args.tag}] seed={args.seed} git={git_hash()}")
        print(f"  WARNING: {args.params_file} not found. Using untuned defaults. "
              f"This is NOT a reportable number -- run scripts/tune_xgboost.py first.")

    params["seed"] = args.seed

    print("\nLoading ...")
    s = load_centralized(data_cfg, model_cfg, args.data_root)
    print(f"  {s.summary()}")

    n_classes = int(model_cfg["labels"]["n_classes"])
    class_names = s.class_names
    headline_idx = headline_class_indices(model_cfg)
    headline_names = list(model_cfg["labels"]["headline_classes"])
    params["num_class"] = n_classes

    # Feature names kept on every DMatrix so importance and any later SHAP
    # cross-check come out indexed by name, not f0/f1/... -- required for a
    # usable paper figure.
    w_train = s.class_weights[s.y_train]
    dtrain = xgb.DMatrix(s.X_train, label=s.y_train, weight=w_train, feature_names=s.feature_names)
    dval = xgb.DMatrix(s.X_val, label=s.y_val, feature_names=s.feature_names)
    dtest = xgb.DMatrix(s.X_test, label=s.y_test, feature_names=s.feature_names)

    feval = make_feval(n_classes, class_names, headline_idx)

    print(f"\nTraining, up to {args.num_boost_round} rounds, "
          f"early stop patience {args.early_stopping_rounds} on val macro-F1 "
          f"over the {len(headline_idx)} headline families\n")

    evals_result: dict = {}
    bst = xgb.train(
        params, dtrain, num_boost_round=args.num_boost_round,
        evals=[(dval, "val")], custom_metric=feval, maximize=True,
        early_stopping_rounds=args.early_stopping_rounds,
        evals_result=evals_result, verbose_eval=50,
    )

    best_iter = bst.best_iteration
    print(f"\n  best val macro-F1 {bst.best_score:.4f} at round {best_iter}")

    y_true = s.y_test
    y_pred = bst.predict(dtest, iteration_range=(0, best_iter + 1)).argmax(axis=1)
    test_m = compute_metrics(y_true, y_pred, n_classes, class_names, headline_idx)
    print("\nTEST\n" + format_per_class(test_m, headline_names))

    importance = bst.get_score(importance_type="gain")
    top10 = sorted(importance.items(), key=lambda kv: -kv[1])[:10]
    print(f"\n  top 10 features by gain:")
    for name, gain in top10:
        print(f"    {name:<30}{gain:>10.1f}")

    (out_dir / "config.json").write_text(json.dumps({
        "tag": args.tag, "seed": args.seed, "git_commit": git_hash(),
        "params": params, "best_iteration": best_iter,
        "params_file": str(args.params_file) if args.params_file.exists() else None,
    }, indent=2, default=str))

    (out_dir / "metrics.json").write_text(json.dumps({
        "best_iteration": best_iter,
        "best_val_macro_f1_headline": float(bst.best_score),
        "test": test_m,
        "test_confusion_matrix": confusion(y_true, y_pred, n_classes),
        "class_names": class_names,
        "headline_classes": headline_names,
        "feature_importance_gain": importance,
    }, indent=2))

    bst.save_model(str(out_dir / "model.json"))
    print(f"\n  written: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
