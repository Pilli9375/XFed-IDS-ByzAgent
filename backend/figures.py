"""Snapshots for dashboard v2: GET /figures, /accuracy, /agreement/summary,
and the baselines + fidelity blocks added to GET /trust.

Each builder reads its results files once at startup and returns a plain,
JSON-serializable dict. Every value carries the repo-relative path of the
file it came from (`source`), so the frontend can link each number to its
file through GET /source/{path}. Nothing here is a typed-in result: values
are read from the files named in configs/backend.yaml, or derived from them
by a stated rule (a difference, a ratio, an exclusion count). No test rows
are read: the test-set figures shown are values already logged in the
results files (docs/test_set_exposure_audit.md).

Place at: backend/figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# GET /figures
# ---------------------------------------------------------------------------

def build_figures_snapshot(cfg_paths: dict, dash_cfg: dict, resolve_path) -> dict:
    fc = dash_cfg["figures"]
    alpha = str(fc["headline_alpha"])

    prereg_path = resolve_path(cfg_paths, "prereg_test_result")
    prereg = _json(prereg_path)
    pa = prereg["per_alpha"][alpha]

    fed_path = resolve_path(cfg_paths, "federated_headline")
    fed = pd.read_csv(fed_path, dtype={"alpha": str})
    fed_row = fed[fed["alpha"] == alpha].iloc[0]

    speed_path = resolve_path(cfg_paths, "inference_speed_summary")
    speed = _json(speed_path)
    serving = speed["variants"][fc["serving_variant"]]
    reference = speed["variants"][fc["reference_variant"]]
    dropped = speed["variants"][fc["dropped_inference_variant"]]

    comp_path = resolve_path(cfg_paths, "update_compression")
    comp = _json(comp_path)
    stat = fc["upload_delta_stat"]

    def scheme(name: str) -> dict:
        s = comp["schemes"][name]
        d = s["delta_vs_uncompressed_over_seeds"][stat]
        return {
            "scheme": name,
            "bytes_up_saved_pct": s["bytes_up_saved_pct"],
            "bytes_up_per_round": s["bytes_up_per_round"],
            "delta_stat": stat,
            "delta_mean": d["mean"],
            "delta_sd": d["sd"],
            "n_seeds": len(d["values"]),
        }

    comm_path = resolve_path(cfg_paths, "communication")
    comm = _json(comm_path)
    analytic = comm["analytic"]
    wall = comm["wall_time_per_round"]
    fedavg_logged = comm["harness_logged"]["by_server_strategy"]["fedavg"]

    pre_path = resolve_path(cfg_paths, "agent_prescreen_replay")
    pre = _json(pre_path)
    at_t = pre["results_at_t_selected"]
    # The rule was chosen on seed 42; report how the other seeds' attack
    # runs fared at the chosen threshold (the "did not transfer" result).
    transfer = [
        {
            "run": key,
            "seed": r["seed"],
            "flag_rate_poisoned_replay": r["flag_rate_poisoned_replay"],
            "flag_rate_poisoned_logged": r["flag_rate_poisoned_logged"],
        }
        for key, r in at_t.items()
        if not r["used_for_selection"] and r["attack"] != "none" and r["seed"] != pre["selection_rule"]["seed"]
    ]

    return {
        "fedavgm_test_macro_f1": {
            "alpha": alpha,
            "method": prereg["method"],
            "mean": pa["macro_f1_headline_mean"],
            "std": pa["macro_f1_headline_std"],
            "n": pa["n"],
            "kind": "one preregistered test evaluation",
            "prereg_file": prereg["prereg_file"],
            "source": _rel(prereg_path),
        },
        "fedavg_test_macro_f1": {
            "alpha": alpha,
            "mean": float(fed_row["mean"]),
            "std": float(fed_row["std"]),
            "n": int(fed_row["n"]),
            "source": _rel(fed_path),
        },
        "latency": {
            "serving_variant": fc["serving_variant"],
            "reference_variant": fc["reference_variant"],
            "serving_p50_us": serving["p50_us"]["median_of_sessions"],
            "reference_p50_us": reference["p50_us"]["median_of_sessions"],
            "serving_rows_per_sec": serving["rows_per_sec"]["median_of_sessions"],
            "reference_rows_per_sec": reference["rows_per_sec"]["median_of_sessions"],
            "throughput_batch_size": speed["protocol"]["throughput"]["batch_size"],
            "prediction_agreement": serving["prediction_agreement_with_eager"],
            "n_sessions": speed["n_sessions"],
            "source": _rel(speed_path),
        },
        "upload": {**scheme(fc["upload_scheme"]), "source": _rel(comp_path)},
        "upload_alt": {**scheme(fc["upload_scheme_alt"]), "source": _rel(comp_path)},
        "traffic": {
            "per_round_bytes": analytic["per_round_bytes"],
            "n_parameters": analytic["n_parameters"],
            "n_silos": analytic["n_silos"],
            "directions_per_round": analytic["directions_per_round"],
            "matches_logs": bool(fedavg_logged["matches_analytic"]),
            "source": _rel(comm_path),
        },
        "round_time": {
            "median_s": wall["median_s"],
            "n_runs": wall["n_runs"],
            "source": _rel(comm_path),
        },
        "int8_inference": {
            "variant": fc["dropped_inference_variant"],
            "delta_val_macro_f1": dropped["delta_vs_eager"],
            "source": _rel(speed_path),
        },
        "prescreen": {
            "selection_seed": pre["selection_rule"]["seed"],
            "t_selected": pre["t_selected"],
            "transfer": transfer,
            "source": _rel(pre_path),
        },
    }


# ---------------------------------------------------------------------------
# GET /accuracy
# ---------------------------------------------------------------------------

def build_accuracy_snapshot(cfg_paths: dict, resolve_path) -> dict:
    fed_path = resolve_path(cfg_paths, "federated_headline")
    fed = pd.read_csv(fed_path, dtype={"alpha": str})
    fed_fam_path = resolve_path(cfg_paths, "federated_per_family")
    fed_fam = pd.read_csv(fed_fam_path)
    prereg_path = resolve_path(cfg_paths, "prereg_test_result")
    prereg = _json(prereg_path)
    sel_path = resolve_path(cfg_paths, "prereg_selection")
    sel = _json(sel_path)

    alphas = [str(a) for a in fed["alpha"]]
    per_alpha = []
    for a in alphas:
        row = fed[fed["alpha"] == a].iloc[0]
        pa = prereg["per_alpha"][a]
        per_alpha.append({
            "alpha": a,
            "fedavg": {"mean": float(row["mean"]), "std": float(row["std"]), "n": int(row["n"])},
            "fedavgm": {
                "mean": pa["macro_f1_headline_mean"],
                "std": pa["macro_f1_headline_std"],
                "n": pa["n"],
            },
        })

    def headline(key: str) -> dict:
        p = resolve_path(cfg_paths, key)
        df = pd.read_csv(p)
        row = df[df["metric"].str.startswith("macro-F1 (7")].iloc[0]
        return {"mean": float(row["mean"]), "std": float(row["std"]), "n": int(row["n"]), "source": _rel(p)}

    families = list(fed_fam["family"])
    per_class = []
    for fam in families:
        fr = fed_fam[fed_fam["family"] == fam].iloc[0]
        per_class.append({
            "family": fam,
            "fedavg": {a: {"mean": float(fr[f"a{a}_mean"]), "std": float(fr[f"a{a}_std"])} for a in alphas},
            "fedavgm": {
                a: {
                    "mean": prereg["per_alpha"][a]["per_class_f1_mean"][fam],
                    "std": prereg["per_alpha"][a]["per_class_f1_std"][fam],
                }
                for a in alphas
            },
        })

    # Headline vs per-class-only families: the 9-wide vocabulary from the
    # prereg file minus its headline set (the metric string names the two
    # it excludes; the class list itself comes from the run's per_class keys).
    all_classes = list(prereg["runs"][0]["test"]["per_class"].keys())
    centralized = headline("centralized_headline")
    xgboost = headline("xgboost_headline")
    headline_classes = [f for f in all_classes if _is_headline(f, prereg)]

    return {
        "metric": prereg["metric"],
        "per_alpha": per_alpha,
        "fedavg_source": _rel(fed_path),
        "fedavgm_method": prereg["method"],
        "fedavgm_source": _rel(prereg_path),
        "fedavgm_kind": "one preregistered test evaluation",
        "selection": {
            "n_candidates_compared": len(sel["candidates"]),
            "n_dropped_by_budget_guard": len(sel["dropped_by_budget_guard"]),
            "chosen": sel["chosen"],
            "source": _rel(sel_path),
        },
        "centralized": centralized,
        "xgboost": xgboost,
        "per_class": per_class,
        "per_class_sources": [_rel(fed_fam_path), _rel(prereg_path)],
        "headline_classes": headline_classes,
        "per_class_only": [f for f in all_classes if f not in headline_classes],
    }


def _is_headline(family: str, prereg: dict) -> bool:
    # result.json states the rule in its metric string: "... (Infiltration,
    # Heartbleed per class only)". Parse that list rather than retype it.
    metric = prereg["metric"]
    inside = metric[metric.index("(") + 1: metric.index(" per class only")]
    excluded = {s.strip() for s in inside.split(",")}
    return family not in excluded


# ---------------------------------------------------------------------------
# GET /agreement/summary
# ---------------------------------------------------------------------------

def build_agreement_summary(cfg_paths: dict, dash_cfg: dict, resolve_path, n_features: int) -> dict:
    from tools.agreement_metrics import chance_jaccard
    from tools.chat04_closeout import cluster_bootstrap_median

    ac = dash_cfg["agreement_summary"]
    agree_path = resolve_path(cfg_paths, "agreement_metrics")
    floor_path = resolve_path(cfg_paths, "centralized_instability_floor")

    agree = pd.read_csv(agree_path)
    agree = agree[agree["family_eligible"]].copy()
    agree["alpha"] = agree["alpha"].astype(str)
    sub = agree[agree["alpha"] == str(ac["ci_alpha"])]
    point, lo, hi, n_clusters = cluster_bootstrap_median(
        sub, list(ac["cluster_cols"]), ac["ci_metric"], int(ac["n_boot"]), int(ac["rng_seed"])
    )

    floor = pd.read_csv(floor_path)
    pair_medians = floor.groupby("seed_pair")[ac["ci_metric"]].median()

    return {
        "metric": ac["ci_metric"],
        "ci": {
            "alpha": str(ac["ci_alpha"]),
            "median": float(point),
            "low": float(lo),
            "high": float(hi),
            "n_clusters": int(n_clusters),
            "n_boot": int(ac["n_boot"]),
            "rng_seed": int(ac["rng_seed"]),
            "method": "cluster bootstrap by (seed, silo), tools/chat04_closeout.py",
            "source": _rel(agree_path),
        },
        "floor": {
            "median": float(floor[ac["ci_metric"]].median()),
            "pair_medians": {k: float(v) for k, v in pair_medians.items()},
            "low": float(pair_medians.min()),
            "high": float(pair_medians.max()),
            "source": _rel(floor_path),
        },
        "overlap": not (hi < pair_medians.min() or lo > pair_medians.max()),
        "chance": {
            "k": int(ac["chance_k"]),
            "n_features": n_features,
            "value": chance_jaccard(int(ac["chance_k"]), n_features),
            "method": "E|A∩B| / E|A∪B| for two uniform random k-subsets, tools/agreement_metrics.py chance_jaccard()",
            "source": "tools/agreement_metrics.py",
        },
    }


# ---------------------------------------------------------------------------
# GET /trust additions: baselines + fidelity
# ---------------------------------------------------------------------------

def build_trust_baselines(cfg_paths: dict, dash_cfg: dict, resolve_path) -> dict:
    tb = dash_cfg["trust_baselines"]
    fed_dir = resolve_path(cfg_paths, "federated_results_dir")
    attacks_dir = resolve_path(cfg_paths, "attacks_dir")

    ref_path = fed_dir / tb["clean_reference_run"] / "final_metrics.json"
    ref = _json(ref_path)["test"]["macro_f1_headline"]
    costs = []
    for d in tb["clean_control_runs"]:
        p = fed_dir / d["run"] / "final_metrics.json"
        m = _json(p)["test"]["macro_f1_headline"]
        costs.append({
            "label": d["label"],
            "run": d["run"],
            "test_macro_f1": m,
            "reference_test_macro_f1": ref,
            "cost_pp": 100 * (m - ref),
            "source": _rel(p),
        })

    exclusions = []
    for d in tb["multikrum_attack_runs"]:
        cfg_path = attacks_dir / d["attack"] / "attack_config.json"
        malicious = set(_json(cfg_path)["malicious_silos"])
        sel_path = fed_dir / d["run"] / "krum_selection.jsonl"
        rows = [json.loads(line) for line in sel_path.read_text().splitlines() if line.strip()]
        mal_rows = [r for r in rows if r["silo_id"] in malicious]
        n_excluded = sum(1 for r in mal_rows if not r["selected"])
        exclusions.append({
            "run": d["run"],
            "malicious_silos": sorted(malicious),
            "n_malicious_slots": len(mal_rows),
            "n_excluded": n_excluded,
            "exclusion_rate": n_excluded / len(mal_rows),
            "n_rounds": len({r["round"] for r in rows}),
            "f_assumed": rows[0]["num_malicious_nodes_assumed"],
            "source": _rel(sel_path),
            "attack_config": _rel(cfg_path),
        })

    return {
        "seed": tb["seed"],
        "clean_reference_run": tb["clean_reference_run"],
        "clean_reference_source": _rel(ref_path),
        "defence_costs": costs,
        "multikrum_exclusions": exclusions,
        "cost_metric": "logged test macro-F1 (headline), clean control minus clean FedAvg",
    }


def build_trust_fidelity(cfg_paths: dict, resolve_path) -> dict:
    audit_path = resolve_path(cfg_paths, "phase4_reasoning_audit")
    hand_path = resolve_path(cfg_paths, "trend_claim_handcheck")
    audit = _json(audit_path)["trend_language_check"]
    hand = _json(hand_path)
    wrong = [r for r in hand["rows"] if r["heuristic_verdict"] == "wrong"]
    ambiguous_wrong = [r for r in wrong if r["hand_check"] == "ambiguous"]
    high = audit["overall_error_rate"]
    # contribution_b_results.md §8: discount the automated rate by the share
    # of hand-checked "wrong" verdicts that were genuinely ambiguous.
    low = high * (1 - len(ambiguous_wrong) / len(wrong))
    return {
        "n_trend_claims": audit["n_trend_claims_total"],
        "automated_error_rate": high,
        "adjusted_error_rate_low": low,
        "handcheck_n": hand["n_sampled"],
        "handcheck_wrong": len(wrong),
        "handcheck_ambiguous_wrong": len(ambiguous_wrong),
        "sources": [_rel(audit_path), _rel(hand_path)],
    }


# ---------------------------------------------------------------------------
# GET /limits
# ---------------------------------------------------------------------------

def _section(lines: list[str], title: str) -> list[str]:
    start = next(i for i, l in enumerate(lines) if l.strip() == f"## {title}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1:end]


def _bullet_groups(body: list[str]) -> list[dict]:
    """'**Group**' headings, each followed by '- ' bullets whose wrapped
    continuation lines are indented. Text is kept as written (Markdown)."""
    groups: list[dict] = []
    for line in body:
        s = line.rstrip()
        if s.startswith("**") and s.endswith("**") and not s.startswith("- "):
            groups.append({"title": s.strip("*"), "items": []})
        elif s.startswith("- ") and groups:
            groups[-1]["items"].append(s[2:])
        elif s.startswith("  ") and groups and groups[-1]["items"]:
            groups[-1]["items"][-1] += " " + s.strip()
    return groups


def _paragraphs_from(lines: list[str], marker: str) -> list[str]:
    """Paragraphs from the line starting with `marker` up to the next '---'."""
    start = next(i for i, l in enumerate(lines) if l.startswith(marker))
    paras, cur = [], []
    for l in lines[start:]:
        if l.strip() == "---":
            break
        if not l.strip():
            if cur:
                paras.append(" ".join(cur))
                cur = []
        else:
            cur.append(l.strip())
    if cur:
        paras.append(" ".join(cur))
    return paras


def _excerpt(path: Path, marker: str) -> str:
    """The comment block or paragraph containing `marker`, verbatim, with
    YAML comment markers removed."""
    lines = path.read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(lines) if marker in l)
    is_comment = lines[i].lstrip().startswith("#")
    out = []
    for l in lines[i:]:
        s = l.strip()
        if not s or (is_comment and not s.startswith("#")):
            break
        out.append(s.lstrip("#").strip() if is_comment else s)
    return " ".join(out)


def build_limits_snapshot(limits_cfg: dict) -> dict:
    claims_path = ROOT / limits_cfg["claims_file"]
    lines = claims_path.read_text(encoding="utf-8").splitlines()
    return {
        "claims": {
            "title": limits_cfg["section"],
            "groups": _bullet_groups(_section(lines, limits_cfg["section"])),
            "source": _rel(claims_path),
        },
        "test_set": {
            "paragraphs": _paragraphs_from(lines, limits_cfg["test_set_marker"]),
            "source": _rel(claims_path),
        },
        "excerpts": [
            {"title": e["title"], "text": _excerpt(ROOT / e["file"], e["marker"]), "source": e["file"]}
            for e in limits_cfg["excerpts"]
        ],
    }
