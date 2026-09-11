"""Single source of truth for the feature set and the label vocabulary.

Every other module imports from here. Nothing re-derives feature columns or
re-encodes labels on its own, because two copies of that logic can drift, and a
drifted feature list silently invalidates the val mask and the partitions --
both of which were built against the derivation in families.py.

Place at: src/data/schema.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# Bookkeeping columns written by the Chat 02 pipeline. Never features.
NON_FEATURE_COLS: tuple[str, ...] = ("family", "below_floor", "is_attempted", "__source_file")

EXPECTED_N_FEATURES = 82


def load_yaml(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def derive_feature_cols(columns: list[str], data_cfg: dict) -> list[str]:
    """Reproduce families.py's feature_cols derivation exactly, order included.

    Order matters: the group key used for both the train/test split and the val
    split is pd.util.hash_pandas_object over these columns, and that hash
    combines per-column hashes in column order.

    `columns` must be the full column list in the parquet's own order.
    """
    try:
        schema = data_cfg["schema"]
        label_col = schema["label_col"]
        attempted_col = schema["attempted_col"]
        identifier_cols = set(schema["identifier_cols"])
    except KeyError as e:
        raise ValueError(f"configs/data.yaml is missing schema key {e}") from e

    cols = [
        c for c in columns
        if c not in NON_FEATURE_COLS
        and c not in (label_col, attempted_col)
        and c not in identifier_cols
    ]

    if len(cols) != EXPECTED_N_FEATURES:
        raise ValueError(
            f"Expected {EXPECTED_N_FEATURES} features, derived {len(cols)}. "
            f"The schema has changed since Chat 02. A silent feature-count change "
            f"invalidates the val mask and every partition file. Resolve before training.\n"
            f"Derived: {cols}"
        )
    return cols


def load_label_vocabulary(model_cfg: dict) -> dict[str, int]:
    """The frozen family -> index map. Never derived from data.

    Deriving this per-silo is the failure that FedAvg cannot detect: two silos
    both produce a 9-wide output layer, shapes match, aggregation runs without
    error, and index 5 means DDoS on one silo and Bot on another.
    """
    vocab = dict(model_cfg["labels"]["vocabulary"])
    n_classes = int(model_cfg["labels"]["n_classes"])

    if len(vocab) != n_classes:
        raise ValueError(f"vocabulary has {len(vocab)} entries but n_classes is {n_classes}")
    if sorted(vocab.values()) != list(range(n_classes)):
        raise ValueError(f"vocabulary indices must be exactly 0..{n_classes - 1}, got {sorted(vocab.values())}")
    return vocab


def encode_families(families: pd.Series, vocab: dict[str, int]) -> np.ndarray:
    """Map family names to class indices using the frozen vocabulary."""
    unknown = set(families.unique()) - set(vocab)
    if unknown:
        raise ValueError(
            f"Families present in the data but absent from the frozen vocabulary: {sorted(unknown)}. "
            f"Add them to configs/model.yaml deliberately -- do not let the vocabulary follow the data."
        )
    return families.map(vocab).to_numpy(dtype=np.int64)


def headline_class_indices(model_cfg: dict) -> np.ndarray:
    """Indices of the 7 above-floor families. Headline macro-F1 covers only these."""
    vocab = load_label_vocabulary(model_cfg)
    return np.array([vocab[f] for f in model_cfg["labels"]["headline_classes"]], dtype=np.int64)


def class_names(model_cfg: dict) -> list[str]:
    """Family names ordered by class index, for metric tables and SHAP figures."""
    vocab = load_label_vocabulary(model_cfg)
    return [name for name, _ in sorted(vocab.items(), key=lambda kv: kv[1])]
