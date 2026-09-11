#!/usr/bin/env python
"""Hyperparameter search for the XGBoost baseline.

Early-stops on val macro-F1 over the 7 headline families -- the identical
criterion the MLP uses -- not on mlogloss. "Tuned" means this ran and won on
that criterion, not that a reasonable-looking config was assumed.

Uses a stratified subsample during search for speed. This is a search-time
convenience only; the final run (xgboost_baseline.py) always uses full data
and is the only source of reportable numbers.

Usage:
    python scripts/tune_xgboost.py
    python scripts/tune_xgboost.py --n-trials 50 --subsample 400000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import optuna
import xgboost as xgb

from src.data.loaders import load_centralized
from src.data.schema import headline_class_indices, load_yaml
from src.train.centralized import stratified_subsample
from src.train.metrics import compute_metrics

optuna.logging.set_verbosity(optuna.logging.WARNING)


def make_feval(n_classes: int, class_names: list[str], headline_idx: np.ndarray):
    """Custom eval metric: val macro-F1 over the 7 headline families.

    Defensive reshape: for multi:softprob with a non-custom objective, preds
    arrive already shaped (n, n_classes) in current xgboost. Reshaping only if
    flat guards against the older-API behaviour some versions still exhibit.
    """
    def feval(preds: np.ndarray, dtrain: xgb.DMatrix):
        if preds.ndim == 1:
            preds = preds.reshape(-1, n_classes)
        y_true = dtrain.get_label().astype(np.int64)
        y_pred = preds.argmax(axis=1)
        m = compute_metrics(y_true, y_pred, n_classes, class_names, headline_idx)
        return "val_macro_f1_headline", m["macro_f1_headline"]
    return feval


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-config", type=Path, default=Path("configs/data.yaml"))
    p.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    p.add_argument("--data-root", type=Path, default=Path("data/processed"))
    p.add_argument("--n-trials", type=int, default=40)
    p.add_argument("--subsample", type=int, default=300_000,
                   help="Search-time only. The final run always uses full data.")
    p.add_argument("--num-boost-round", type=int, default=500)
    p.add_argument("--early-stopping-rounds", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("configs/xgboost_tuned.json"))
    args = p.parse_args()

    data_cfg = load_yaml(args.data_config)
    model_cfg = load_yaml(args.model_config)
    device = "cuda"

    print("Loading ...")
    s = load_centralized(data_cfg, model_cfg, args.data_root)
    print(f"  {s.summary()}")

    keep = stratified_subsample(s.y_train, args.subsample, args.seed)
    print(f"  search subsample: {len(keep):,} rows (final run uses all {len(s.y_train):,})")

    n_classes = int(model_cfg["labels"]["n_classes"])
    class_names = s.class_names
    headline_idx = headline_class_indices(model_cfg)
    w_train = s.class_weights[s.y_train[keep]]

    dtrain = xgb.DMatrix(s.X_train[keep], label=s.y_train[keep], weight=w_train,
                         feature_names=s.feature_names)
    dval = xgb.DMatrix(s.X_val, label=s.y_val, feature_names=s.feature_names)

    feval = make_feval(n_classes, class_names, headline_idx)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "multi:softprob",
            "num_class": n_classes,
            "tree_method": "hist",
            "device": device,
            "disable_default_eval_metric": 1,
            "seed": args.seed,
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        }
        bst = xgb.train(
            params, dtrain, num_boost_round=args.num_boost_round,
            evals=[(dval, "val")], custom_metric=feval, maximize=True,
            early_stopping_rounds=args.early_stopping_rounds, verbose_eval=False,
        )
        return float(bst.best_score)

    print(f"\nSearching {args.n_trials} trials ...\n")
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=args.seed))
    study.optimize(objective, n_trials=args.n_trials, show_progress_bar=True)

    print(f"\nBest val macro-F1 (headline, search subsample): {study.best_value:.4f}")
    print(f"Best params: {json.dumps(study.best_params, indent=2)}")

    fixed = {
        "objective": "multi:softprob", "num_class": n_classes,
        "tree_method": "hist", "device": device,
        "disable_default_eval_metric": 1,
    }
    out_params = {**fixed, **study.best_params}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "params": out_params,
        "search_val_macro_f1_headline": study.best_value,
        "n_trials": args.n_trials,
        "search_subsample": args.subsample,
        "seed": args.seed,
        "note": "Selected on a subsample for search speed. Not a reportable "
                "number -- re-evaluated on full data by xgboost_baseline.py.",
    }, indent=2))
    print(f"\nwritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
