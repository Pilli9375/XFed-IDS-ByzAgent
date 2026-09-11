"""Builds the GET /trust snapshot (ByzAgent trust panel) once at startup.

Contribution B (defenses/ByzAgent), kept visibly separate from Contribution
A's /agreement and /parity: different response shape (a list of clean/attack
condition pairs plus a decision-variance section, not a bag of CSV-shaped
row arrays) and none of Contribution A's metric field names
(kendall_weighted_tau, jaccard_at_*, tau_w, fleet_parity, silo_deviation,
flagged, family_eligible) appear anywhere here.

STRUCTURAL RULE, enforced here, not just in the frontend: a condition can
only ever be reported as a clean+attack PAIR. Both TrustConditionPair.clean
and .attack are required, non-Optional -- there is no code path in this
module that can construct one without the other. A condition whose
artifacts don't support pairing (missing agent-decision log, missing
client_stats.jsonl, or a decision log that fails to pivot into a grid, on
either side) is dropped from `conditions` and moved to `excluded_conditions`
with a reason -- never emitted as a half pair.

Reuses app_lib/trust_loaders.py's decision_grid() (the Streamlit panel's
canonical silo x round pivot+reindex) rather than reimplementing the pivot,
and its DECISION_SEVERITY / FLAGGED_DECISIONS constants rather than
re-declaring the trust/downweight/quarantine taxonomy a second time. Does
NOT reuse that module's load_decisions()/load_client_stats() (Streamlit
@st.cache_resource-wrapped; this module already has its own tested jsonl
reading below, and calling the decorated loaders outside a real Streamlit
script prints a "missing ScriptRunContext" warning per call -- harmless in
the Streamlit app, just noise in a FastAPI startup log).

Place at: backend/trust.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from statistics import mean

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app_lib.trust_loaders import (  # noqa: E402
    DECISION_SEVERITY,
    FLAGGED_DECISIONS,
    decision_grid as _canonical_decision_grid,
)

log = logging.getLogger(__name__)

# Priority order for "the" current-round decision log in a run directory.
# All three share the identical current-round schema (scalar raw_stats_given
# per round/silo) -- confirmed by inspection, not assumed -- so any one of
# them is a valid source; this is a documented tie-break, not an arbitrary
# pick, for the one directory (fedavg_a0.5_s42) that has more than one.
# Rolling-history is deliberately never in this list -- per-round grids and
# per-silo flag rates are both a current-round-mode view.
_DECISION_LOG_PRIORITY = (
    "agent_decisions_phase4_current_round.jsonl",
    "agent_decisions.jsonl",
    "agent_decisions_multiseed.jsonl",
)

_SILO_ID_RE = re.compile(r"(\d+)$")


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _silo_int(silo_id) -> int:
    """Decision logs use 'silo_3'; client_stats.jsonl uses the int 3
    directly. Normalize both to int so the two sources join correctly."""
    if isinstance(silo_id, int):
        return silo_id
    match = _SILO_ID_RE.search(str(silo_id))
    if not match:
        raise ValueError(f"cannot parse a silo index out of silo_id={silo_id!r}")
    return int(match.group(1))


def _select_decision_log(run_dir: Path) -> Path | None:
    for name in _DECISION_LOG_PRIORITY:
        candidate = run_dir / name
        if candidate.exists():
            return candidate
    return None


def _flag_rates(decision_rows: list[dict]) -> dict[int, dict]:
    """{silo_id: {n_rounds, n_flagged, flag_rate}}. 'Flagged' = decision in
    FLAGGED_DECISIONS (app_lib.trust_loaders' taxonomy, reused rather than
    re-declared); matches the trust/flagged boundary definition used
    throughout results/agents/PHASE4_SUMMARY.md."""
    per_silo: dict[int, list[str]] = {}
    for row in decision_rows:
        silo = _silo_int(row["silo_id"])
        per_silo.setdefault(silo, []).append(row["decision"])

    out = {}
    for silo, decisions in per_silo.items():
        n_flagged = sum(1 for d in decisions if d in FLAGGED_DECISIONS)
        out[silo] = {
            "n_rounds": len(decisions),
            "n_flagged": n_flagged,
            "flag_rate": n_flagged / len(decisions) if decisions else None,
        }
    return out


def _decision_grid_json(decision_rows: list[dict]) -> dict:
    """The frontend's decision_grid_heatmap shape: {rounds:[...],
    silos:[{silo_id, severities:[...]}]}. severities is 0/1/2/null, aligned
    1:1 with `rounds`. Built by handing the SAME rows _flag_rates saw to
    app_lib.trust_loaders.decision_grid() -- the canonical pivot+reindex --
    then reshaping its DataFrame output into this JSON shape; the pivot
    logic itself is not reimplemented here."""
    df = pd.DataFrame(decision_rows)
    df["silo"] = df["silo_id"].apply(_silo_int)
    df["round"] = df["round"].astype(int)
    df["severity"] = df["decision"].map(DECISION_SEVERITY)
    unmapped = df[df["severity"].isna() & df["decision"].notna()]
    if not unmapped.empty:
        bad = sorted(unmapped["decision"].unique())
        raise ValueError(f"decision value(s) {bad} not in DECISION_SEVERITY {DECISION_SEVERITY}")

    n_rounds = int(df["round"].max())
    # decision_grid()'s reindex assumes rounds 1..n_rounds and silos
    # 0..n_silos-1 -- verified true for every decision log this module
    # actually reads (min round 1, contiguous, silos 0-9) before relying on
    # it; a genuine gap still reindexes correctly to null, just the round
    # *numbering* itself is assumed to start at 1.
    n_silos = int(df["silo"].max()) + 1
    grid = _canonical_decision_grid(df, n_rounds=n_rounds, n_silos=n_silos)

    rounds = list(range(1, n_rounds + 1))
    silos = []
    for silo_id, row in grid.iterrows():
        severities = [None if pd.isna(v) else int(v) for v in row.tolist()]
        silos.append({"silo_id": int(silo_id), "severities": severities})

    return {"rounds": rounds, "silos": silos}


def _client_stats_means(client_stats_path: Path) -> dict[int, dict]:
    """{silo_id: mean update_norm/cosine_to_global/train_loss/val_accuracy
    across all rounds in the file}. Read directly from client_stats.jsonl,
    not from the decision log's embedded raw_stats_given -- an explicit,
    separate use of the file the task named as a required source."""
    per_silo: dict[int, dict[str, list[float]]] = {}
    fields = ("update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy")
    for row in _read_jsonl(client_stats_path):
        silo = _silo_int(row["silo_id"])
        bucket = per_silo.setdefault(silo, {f: [] for f in fields})
        for f in fields:
            if f in row:
                bucket[f].append(row[f])

    out = {}
    for silo, values in per_silo.items():
        out[silo] = {f"mean_{f}": (mean(v) if v else None) for f, v in values.items()}
    return out


def _build_run_summary(run_dir: Path, run_tag: str) -> tuple[dict | None, str | None]:
    """Returns (summary, failure_reason). summary is None iff any required
    artifact is missing, or the decision log fails to produce a grid (e.g.
    a duplicate (silo, round) pair the pivot rejects) -- the caller must
    not construct a pair from a None summary."""
    if not run_dir.exists():
        return None, f"run directory {run_dir} does not exist"

    decision_log = _select_decision_log(run_dir)
    if decision_log is None:
        return None, f"no agent-decision log ({'/'.join(_DECISION_LOG_PRIORITY)}) in {run_dir}"

    client_stats_path = run_dir / "client_stats.jsonl"
    if not client_stats_path.exists():
        return None, f"no client_stats.jsonl in {run_dir}"

    decision_rows = _read_jsonl(decision_log)
    flag_rates = _flag_rates(decision_rows)
    try:
        decision_grid = _decision_grid_json(decision_rows)
    except Exception as e:  # e.g. pandas pivot on a duplicate (silo, round)
        return None, f"{decision_log} could not be pivoted into a decision grid: {e}"

    stats_means = _client_stats_means(client_stats_path)

    per_silo = []
    for silo in sorted(set(flag_rates) | set(stats_means)):
        entry = {"silo_id": silo}
        entry.update(flag_rates.get(silo, {"n_rounds": 0, "n_flagged": 0, "flag_rate": None}))
        entry.update(stats_means.get(silo, {}))
        per_silo.append(entry)

    summary = {
        "run_tag": run_tag,
        "decision_log": decision_log.name,
        "per_silo": per_silo,
        "decision_grid": decision_grid,
    }
    return summary, None


def _federated_dir_name(attack_tag: str, f: int) -> str:
    """attack_config.json's own tag, e.g. 'a0.5_s42_f3_sudden_silos0-3-5',
    maps to the federated run directory 'fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5'
    by inserting 'poisoned_' immediately before the '_f{f}_' segment.
    Verified against every attack_config.json on disk before writing this,
    including the one retired condition (a0.5_s42_f3_sudden) whose derived
    directory exists but has no agent-decision data -- exactly the
    don't-render case this module handles."""
    marker = f"_f{f}_"
    if marker not in attack_tag:
        raise ValueError(f"attack tag {attack_tag!r} does not contain expected marker {marker!r}")
    idx = attack_tag.index(marker)
    return "fedavg_" + attack_tag[:idx] + "_poisoned" + attack_tag[idx:]


def _clean_dir_name(alpha: str, seed: int) -> str:
    return f"fedavg_a{alpha}_s{seed}"


def _load_attack_conditions(attacks_dir: Path) -> list[dict]:
    conditions = []
    for child in sorted(attacks_dir.iterdir()):
        config_path = child / "attack_config.json"
        if config_path.exists():
            conditions.append(json.loads(config_path.read_text()))
    return conditions


def _decision_variance_phase3(path: Path) -> list[dict]:
    dv = json.loads(path.read_text())["decision_variance"]
    cells = []
    for condition, data in dv["by_condition"].items():
        # Phase 3 predates rolling-history mode -- current-round only. The
        # published boundary-stability number (30/30 = 100%, PHASE3_SUMMARY.md)
        # is derived here, not re-typed from the doc: same trust-vs-flagged
        # rule _flag_rates() uses above, applied to each silo's 3 repeated
        # decisions instead of its 20 per-round ones.
        boundary_labels = {
            silo: {"flagged" if d in FLAGGED_DECISIONS else "trust" for d in info["decisions"]}
            for silo, info in data["per_silo"].items()
        }
        n_boundary_stable = sum(1 for labels in boundary_labels.values() if len(labels) == 1)
        cells.append({
            "phase": "3",
            "mode": "current_round",
            "condition": condition,
            "round": dv["round"],
            "repeats": dv["repeats"],
            "n_silos": data["n_silos"],
            "n_exact_stable": data["n_stable"],
            "exact_stability_rate": data["stability_rate"],
            "n_boundary_stable": n_boundary_stable,
            "boundary_stability_rate": n_boundary_stable / data["n_silos"],
            "source": str(path),
        })
    return cells


def _decision_variance_phase4(path: Path) -> list[dict]:
    dv = json.loads(path.read_text())["decision_variance"]
    cells = []
    for condition_mode, data in dv["by_condition_mode"].items():
        condition, mode = condition_mode.split("__", 1)
        cells.append({
            "phase": "4",
            "mode": mode,
            "condition": condition,
            "round": dv["round"],
            "repeats": dv["repeats"],
            "n_silos": data["n_silos"],
            "n_exact_stable": data["n_exact_stable"],
            "exact_stability_rate": data["exact_stability_rate"],
            "n_boundary_stable": data["n_boundary_stable"],
            "boundary_stability_rate": data["boundary_stability_rate"],
            "source": str(path),
        })
    return cells


def _nondeterminism_notice(decision_variance: list[dict]) -> str:
    """Derived from the actual served numbers, not a separately hardcoded
    string that could drift from the table above it. Deliberately does NOT
    pool Phase 3's and Phase 4's current-round cells into one average --
    they are two separate studies (different condition sets: Phase 3 =
    {clean, f3_{0,3,5}, f2_{0,3}}, Phase 4 = {clean, sudden, gradual}) and
    Phase 3's is the dedicated current-round stability measurement the
    ~90% figure actually refers to; Phase 4's current-round cells exist to
    be compared against ITS OWN rolling-history cells, not folded into a
    cross-phase mean."""
    phase3_current_round = [
        c["exact_stability_rate"] for c in decision_variance
        if c["phase"] == "3" and c["mode"] == "current_round"
    ]
    rolling_boundary_rates = [
        c["boundary_stability_rate"] for c in decision_variance
        if c["mode"] == "rolling_history" and c["boundary_stability_rate"] is not None
    ]
    cr_pct = round(100 * mean(phase3_current_round)) if phase3_current_round else None
    rh_lo = round(100 * min(rolling_boundary_rates)) if rolling_boundary_rates else None
    rh_hi = round(100 * max(rolling_boundary_rates)) if rolling_boundary_rates else None
    return (
        "Trust decisions are generated by an LLM (ByzAgent) and are NOT deterministic: "
        "repeating the identical round 3x independently changes the exact decision "
        f"~{100 - cr_pct if cr_pct is not None else '?'}% of the time in current-round mode "
        f"(~{cr_pct if cr_pct is not None else '?'}% exact-match stability, Phase 3's dedicated "
        "measurement), though the coarser trust-vs-flagged boundary is far more stable there "
        "(100% in every current-round cell below). Rolling-history mode is materially less "
        f"stable at that boundary ({rh_lo}-{rh_hi}% across conditions, Phase 4). "
        "See decision_variance below for the per-condition numbers this summary is computed from."
    )


def build_trust_snapshot(cfg_paths: dict, resolve_path) -> dict:
    """Reads every artifact once and returns a plain, JSON-serializable
    dict. Called once at backend startup; main.py caches the rendered JSON
    string and this function is never called again per-request."""
    attacks_dir = resolve_path(cfg_paths, "attacks_dir")
    federated_results_dir = resolve_path(cfg_paths, "federated_results_dir")

    conditions = []
    excluded = []
    for attack_cfg in _load_attack_conditions(attacks_dir):
        attack_tag = attack_cfg["tag"]
        alpha = str(attack_cfg["alpha"])
        seed = int(attack_cfg["partition_seed"])
        f = int(attack_cfg["f"])

        attack_dir = federated_results_dir / _federated_dir_name(attack_tag, f)
        clean_dir = federated_results_dir / _clean_dir_name(alpha, seed)

        clean_summary, clean_reason = _build_run_summary(clean_dir, clean_dir.name)
        attack_summary, attack_reason = _build_run_summary(attack_dir, attack_dir.name)

        if clean_summary is None or attack_summary is None:
            reason = "; ".join(r for r in (clean_reason, attack_reason) if r)
            log.warning("GET /trust: excluding condition %s -- %s", attack_tag, reason)
            excluded.append({"attack_tag": attack_tag, "reason": reason})
            continue

        conditions.append({
            "attack_tag": attack_tag,
            "alpha": alpha,
            "seed": seed,
            "f": f,
            "mode": attack_cfg["mode"],
            # Never hardcoded -- comes from this attack_config.json or the
            # condition is excluded above, per the task's explicit rule.
            "true_malicious_silos": list(attack_cfg["malicious_silos"]),
            "clean": clean_summary,
            "attack": attack_summary,
        })

    decision_variance = _decision_variance_phase3(
        resolve_path(cfg_paths, "decision_variance_phase3")
    ) + _decision_variance_phase4(
        resolve_path(cfg_paths, "decision_variance_phase4")
    )

    log.info(
        "GET /trust snapshot built: %d condition pair(s), %d excluded, %d decision-variance cell(s)",
        len(conditions), len(excluded), len(decision_variance),
    )

    return {
        "conditions": conditions,
        "excluded_conditions": excluded,
        "decision_variance": decision_variance,
        "nondeterminism_notice": _nondeterminism_notice(decision_variance),
    }
