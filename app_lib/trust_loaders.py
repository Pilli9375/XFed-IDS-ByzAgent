"""Loaders for the Client Trust Monitor panel (Contribution B / ByzAgent).

Reads only pre-existing decision and behavioral-stat artifacts already on
disk under results/federated/ and results/attacks/ -- no retraining, no
live Ollama calls, nothing recomputed. Kept separate from loaders.py
because this panel's artifact family (agent decisions, client behavioral
stats, attack manifests) is unrelated to Phase 1-5's model/SHAP artifacts.

CONDITIONS below is the complete, hand-verified set of (seed, attack
condition) pairs that have BOTH a clean run and an attack run with agent
decisions AND client_stats on disk -- confirmed by direct directory
listing, not assumed. Every mode listed under a condition is confirmed
present in BOTH its clean_dir and attack_dir. Two things are deliberately
absent from this registry and must stay that way:
  - the retired {0,1,9} condition (fedavg_a0.5_s42_poisoned_f3_sudden),
    which has no agent_decisions.jsonl and no client_stats.jsonl at all;
  - any alpha other than 0.5, since no attack/agent data exists there.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT / "results"
FEDERATED_ROOT = RESULTS_ROOT / "federated"
ATTACKS_ROOT = RESULTS_ROOT / "attacks"

DECISION_SEVERITY = {"trust": 0, "downweight": 1, "quarantine": 2}
DECISION_NAMES = {v: k for k, v in DECISION_SEVERITY.items()}
FLAGGED_DECISIONS = {"downweight", "quarantine"}

STAT_COLS = ["update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy"]

# --- Condition registry ------------------------------------------------------

CONDITIONS: dict[str, dict] = {
    "s42_sudden_f3": {
        "seed": 42,
        "label": "Sudden onset, f=3, silos {0,3,5}",
        "clean_dir": "fedavg_a0.5_s42",
        "attack_dir": "fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5",
        "attacks_tag": "a0.5_s42_f3_sudden_silos0-3-5",
        "modes": {
            "current_phase3": {"label": "Current-round (Phase 3 replay)", "file": "agent_decisions.jsonl", "kind": "current"},
            "current_phase4": {"label": "Current-round (Phase 4 replay)", "file": "agent_decisions_phase4_current_round.jsonl", "kind": "current"},
            "rolling_phase4": {"label": "Rolling-history (Phase 4 replay, window=5)", "file": "agent_decisions_phase4_rolling_history.jsonl", "kind": "rolling"},
        },
    },
    "s42_sudden_f2": {
        "seed": 42,
        "label": "Sudden onset, f=2, silos {0,3}",
        "clean_dir": "fedavg_a0.5_s42",
        "attack_dir": "fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3",
        "attacks_tag": "a0.5_s42_f2_sudden_silos0-3",
        "modes": {
            "current_phase3": {"label": "Current-round (Phase 3 replay)", "file": "agent_decisions.jsonl", "kind": "current"},
        },
    },
    "s42_gradual_f3": {
        "seed": 42,
        "label": "Gradual onset, f=3, silos {0,3,5}",
        "clean_dir": "fedavg_a0.5_s42",
        "attack_dir": "fedavg_a0.5_s42_poisoned_f3_gradual_silos0-3-5",
        "attacks_tag": "a0.5_s42_f3_gradual_silos0-3-5",
        "modes": {
            "current_phase4": {"label": "Current-round (Phase 4 replay)", "file": "agent_decisions_phase4_current_round.jsonl", "kind": "current"},
            "rolling_phase4": {"label": "Rolling-history (Phase 4 replay, window=5)", "file": "agent_decisions_phase4_rolling_history.jsonl", "kind": "rolling"},
        },
    },
    "s1337_sudden_f3": {
        "seed": 1337,
        "label": "Sudden onset, f=3, silos {0,3,5}",
        "clean_dir": "fedavg_a0.5_s1337",
        "attack_dir": "fedavg_a0.5_s1337_poisoned_f3_sudden_silos0-3-5",
        "attacks_tag": "a0.5_s1337_f3_sudden_silos0-3-5",
        "modes": {
            "current_multiseed": {"label": "Current-round (multi-seed replay)", "file": "agent_decisions_multiseed.jsonl", "kind": "current"},
        },
    },
    "s2024_sudden_f3": {
        "seed": 2024,
        "label": "Sudden onset, f=3, silos {0,3,5}",
        "clean_dir": "fedavg_a0.5_s2024",
        "attack_dir": "fedavg_a0.5_s2024_poisoned_f3_sudden_silos0-3-5",
        "attacks_tag": "a0.5_s2024_f3_sudden_silos0-3-5",
        "modes": {
            "current_multiseed": {"label": "Current-round (multi-seed replay)", "file": "agent_decisions_multiseed.jsonl", "kind": "current"},
        },
    },
}

SEEDS = [42, 1337, 2024]


def conditions_for_seed(seed: int) -> dict[str, dict]:
    return {k: v for k, v in CONDITIONS.items() if v["seed"] == seed}


# --- Raw file access ----------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _silo_int(silo_id) -> int:
    """Normalize either the decision files' 'silo_0' string form or
    client_stats' plain int form to a plain int. This is the ONLY place
    in the panel this normalization happens -- every loader below routes
    through here rather than each call site re-deriving it."""
    if isinstance(silo_id, str):
        return int(silo_id.removeprefix("silo_"))
    return int(silo_id)


@st.cache_resource
def load_decisions(run_dir: str, filename: str) -> pd.DataFrame:
    """One row per (round, silo) decision, silo_id normalized to int."""
    path = FEDERATED_ROOT / run_dir / filename
    rows = _read_jsonl(path)
    df = pd.DataFrame(rows)
    df["silo"] = df["silo_id"].apply(_silo_int)
    df["severity"] = df["decision"].map(DECISION_SEVERITY)
    df["flagged"] = df["decision"].isin(FLAGGED_DECISIONS)
    return df


@st.cache_resource
def load_client_stats(run_dir: str) -> pd.DataFrame:
    path = FEDERATED_ROOT / run_dir / "client_stats.jsonl"
    rows = _read_jsonl(path)
    df = pd.DataFrame(rows)
    df["silo"] = df["silo_id"].apply(_silo_int)
    return df


@st.cache_resource
def load_attack_config(attacks_tag: str) -> dict:
    path = ATTACKS_ROOT / attacks_tag / "attack_config.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())


def get_malicious_silos(condition_key: str) -> list[int]:
    """Read straight from that condition's attack_config.json -- never
    hardcoded, per the panel's framing requirement."""
    cond = CONDITIONS[condition_key]
    cfg = load_attack_config(cond["attacks_tag"])
    return sorted(cfg["malicious_silos"])


def _assert_silo_alignment(decisions: pd.DataFrame, stats: pd.DataFrame, context: str) -> None:
    """Fail loudly if the decision-file silo set and the client_stats silo
    set don't match exactly, rather than silently dropping or
    mis-joining rows on a partial join."""
    d_silos = set(decisions["silo"].unique())
    s_silos = set(stats["silo"].unique())
    if d_silos != s_silos:
        raise ValueError(
            f"Silo-id mismatch between decisions and client_stats for {context}: "
            f"decisions has silos {sorted(d_silos)}, client_stats has "
            f"{sorted(s_silos)}. Refusing to join -- this would silently "
            "drop or misalign rows."
        )


@st.cache_resource
def load_condition_bundle(condition_key: str, mode_key: str) -> dict:
    """Everything one (condition, agent-mode) selection needs: clean
    decisions, attack decisions, clean stats, attack stats, and the
    malicious-silo list for that condition -- joined and alignment-checked
    once here, so section code never re-derives it or risks showing one
    side without the other."""
    cond = CONDITIONS[condition_key]
    mode = cond["modes"][mode_key]

    clean_decisions = load_decisions(cond["clean_dir"], mode["file"])
    attack_decisions = load_decisions(cond["attack_dir"], mode["file"])
    clean_stats = load_client_stats(cond["clean_dir"])
    attack_stats = load_client_stats(cond["attack_dir"])

    _assert_silo_alignment(clean_decisions, clean_stats, f"{cond['clean_dir']}/{mode['file']}")
    _assert_silo_alignment(attack_decisions, attack_stats, f"{cond['attack_dir']}/{mode['file']}")

    return {
        "clean_decisions": clean_decisions,
        "attack_decisions": attack_decisions,
        "clean_stats": clean_stats,
        "attack_stats": attack_stats,
        "malicious_silos": get_malicious_silos(condition_key),
        "n_silos": 10,
        "n_rounds": int(attack_decisions["round"].max()),
        "mode_kind": mode["kind"],
    }


# --- Derived views ------------------------------------------------------------

def flag_rate_by_silo(decisions: pd.DataFrame) -> pd.Series:
    """Fraction of rounds each silo was flagged (downweight|quarantine)."""
    return decisions.groupby("silo")["flagged"].mean()


def clean_vs_attack_table(bundle: dict) -> pd.DataFrame:
    """One row per silo: clean flag rate, attack flag rate, and lift
    (attack - clean) computed explicitly, never one side alone."""
    clean_rate = flag_rate_by_silo(bundle["clean_decisions"])
    attack_rate = flag_rate_by_silo(bundle["attack_decisions"])
    df = pd.DataFrame({"clean_flag_rate": clean_rate, "attack_flag_rate": attack_rate}).fillna(0.0)
    df.index.name = "silo"
    df["lift"] = df["attack_flag_rate"] - df["clean_flag_rate"]
    df["malicious"] = df.index.isin(bundle["malicious_silos"])
    return df.reset_index().sort_values("silo").reset_index(drop=True)


def decision_grid(decisions: pd.DataFrame, n_rounds: int, n_silos: int = 10) -> pd.DataFrame:
    """Silo x round grid of severity ints (0=trust/1=downweight/
    2=quarantine), silo rows 0..n_silos-1, round columns 1..n_rounds --
    reindexed so a missing (silo, round) shows as a gap, never silently
    shifted into the wrong cell."""
    pivot = decisions.pivot(index="silo", columns="round", values="severity")
    return pivot.reindex(index=range(n_silos), columns=range(1, n_rounds + 1))


def get_explanation(decisions: pd.DataFrame, silo: int, round_: int) -> dict | None:
    row = decisions[(decisions["silo"] == silo) & (decisions["round"] == round_)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def silo_stat_trend(stats: pd.DataFrame, silo: int) -> pd.DataFrame:
    sub = stats[stats["silo"] == silo].sort_values("round")
    return sub[["round"] + STAT_COLS]
