"""Export real project results as small JSON files for the static showcase site.

Read-only on results/ and docs/. Writes only into output_dir (configs/showcase_export.yaml,
default site/public/data/). Values are COPIED or AGGREGATED (median/mean/count/difference)
from existing artifacts; nothing is rounded, smoothed or invented. Every JSON file carries a
"source" field naming the repo file(s) it was computed from.

No raw feature rows are exported (the dataset is not redistributed): replay_alerts.json keeps
only top-k feature names and SHAP values, plus the precomputed analyst sentence.

Run from project root:  python tools/export_showcase_data.py
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "configs" / "showcase_export.yaml"


# ---------------------------------------------------------------- helpers
def clean(o):
    """Make JSON-safe without changing any value (no rounding). NaN -> None."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def write_json(out_dir: Path, name: str, source: list[str], body: dict) -> Path:
    payload = {"source": source, **body}
    p = out_dir / name
    p.write_text(json.dumps(clean(payload), separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return p


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def load_jsonl(rel: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if l.strip()]


def alpha_key(a) -> str:
    return str(float(a))


def tag(kind: str, alpha, seed) -> str:
    return f"{kind}_a{alpha}_s{seed}"


def val_series(cfg, run: str) -> list[float]:
    """val_macro_f1_headline for rounds 1..N (round 0 = untrained init, excluded)."""
    rh = load_json(f"{cfg['paths']['federated_dir']}/{run}/round_history.json")
    return [r["val_macro_f1_headline"] for r in rh if r["round"] >= 1]


def four_stats(series: list[float], final_window: int) -> dict:
    s = np.array(series)
    return {
        "mean": s.mean(),
        "median": float(np.median(s)),
        "final5mean": s[-final_window:].mean(),
        "max": s.max(),
        "n_rounds": len(s),
    }


# ---------------------------------------------------------------- headline
def instability_floor(cfg) -> dict:
    df = pd.read_csv(ROOT / cfg["paths"]["instability_floor"])
    pair_med = df.groupby("seed_pair")[["jaccard_at_10", "kendall_weighted_tau"]].median()
    return {
        "per_seed_pair_median": pair_med.to_dict(orient="index"),
        "jaccard_at_10_median_of_pair_medians": float(pair_med["jaccard_at_10"].median()),
        "jaccard_at_10_range": [float(pair_med["jaccard_at_10"].min()), float(pair_med["jaccard_at_10"].max())],
        "tau_median_of_pair_medians": float(pair_med["kendall_weighted_tau"].median()),
        "tau_range": [float(pair_med["kendall_weighted_tau"].min()), float(pair_med["kendall_weighted_tau"].max())],
        "n_seed_pairs": int(pair_med.shape[0]),
        "n_rows": int(len(df)),
    }


def chance_jaccard(k: int, n: int) -> float:
    # identical formula to tools/agreement_metrics.py::chance_jaccard
    exp_intersect = k * k / n
    exp_union = 2 * k - exp_intersect
    return exp_intersect / exp_union


def eligible_agreement(cfg) -> pd.DataFrame:
    df = pd.read_csv(ROOT / cfg["paths"]["agreement_metrics"])
    return df[df[cfg["eligible_column"]]]


def export_headline(cfg, out_dir):
    P = cfg["paths"]
    row = cfg["headline_metric_row"]

    def agg_row(path):
        df = pd.read_csv(ROOT / path)
        r = df[df["metric"] == row].iloc[0]
        return {c: r[c] for c in df.columns if c != "metric"}

    fed = pd.read_csv(ROOT / P["federated_headline"])
    el = eligible_agreement(cfg)
    med = el.groupby("alpha")[["jaccard_at_10", "kendall_weighted_tau"]].median()
    n_rows = el.groupby("alpha").size()
    manifest = load_json(P["best_rounds_manifest"])
    demo = next(m for m in manifest if m["tag"] == "fedavg_a0.5_s42")
    body = {
        "centralized_mlp_macro_f1_headline": agg_row(P["centralized_headline"]),
        "xgboost_macro_f1_headline": agg_row(P["xgboost_headline"]),
        "fedavg_macro_f1_headline_by_alpha": {alpha_key(r.alpha): {"n": r.n, "mean": r["mean"], "std": r["std"], "min": r["min"], "max": r["max"]} for _, r in fed.iterrows()},
        "agreement_by_alpha": {
            alpha_key(a): {
                "jaccard_at_10_median": med.loc[a, "jaccard_at_10"],
                "weighted_tau_median": med.loc[a, "kendall_weighted_tau"],
                "n_eligible_rows": int(n_rows.loc[a]),
            }
            for a in cfg["alphas"]
        },
        "chance_jaccard_at_10": {"value": chance_jaccard(cfg["k"], cfg["n_features"]), "k": cfg["k"], "n_features": cfg["n_features"],
                                 "formula": "exp_intersect=k*k/n; exp_union=2k-exp_intersect; ratio (tools/agreement_metrics.py::chance_jaccard)"},
        "centralized_seed_instability_floor": instability_floor(cfg),
        "served_demo_model": {k: demo[k] for k in ("tag", "alpha", "seed", "best_round", "best_val_macro_f1_headline", "test_macro_f1_headline")},
        "notes": [
            "Agreement medians: median over family_eligible==True rows of agreement_metrics.csv, grouped by alpha.",
            "Centralized/XGBoost/FedAvg macro-F1 are the 7-class headline macro-F1 on the test set (evaluated once), best-by-validation round for FedAvg; mean/std across the 3 seeds.",
            "Test-set access: the test set was evaluated exactly once. Raw features of 514 already-explained rows were read once for demo display only; no metric derives from them (docs/contribution_a_results.md, Test-set access note).",
        ],
    }
    return write_json(out_dir, "headline.json",
                      [P["centralized_headline"], P["xgboost_headline"], P["federated_headline"], P["agreement_metrics"],
                       P["instability_floor"], P["best_rounds_manifest"], "tools/agreement_metrics.py (chance formula)", P["contribution_a"]], body)


# ---------------------------------------------------------------- agreement by alpha / round
def export_agreement_by_alpha(cfg, out_dir):
    P = cfg["paths"]
    df = pd.read_csv(ROOT / P["agreement_metrics"])
    el = df[df[cfg["eligible_column"]]]
    cols = ["jaccard_at_5", "jaccard_at_10", "jaccard_at_20", "kendall_weighted_tau"]
    out = {}
    for a in cfg["alphas"]:
        sub = el[el.alpha == a]
        per_seed = {}
        for s in cfg["seeds"]:
            ss = sub[sub.seed == s]
            per_seed[str(s)] = {"n_eligible_rows": int(len(ss)), "median": ss[cols].median().to_dict(), "mean": ss[cols].mean().to_dict()}
        out[alpha_key(a)] = {
            "n_rows_total": int((df.alpha == a).sum()),
            "n_eligible_rows": int(len(sub)),
            "median": sub[cols].median().to_dict(),
            "mean": sub[cols].mean().to_dict(),
            "per_seed": per_seed,
        }
    body = {
        "metric_columns": cols,
        "aggregation_note": "Headline convention (docs/contribution_a_results.md §2): MEDIAN over family_eligible==True rows. Means are also provided; per-seed values use the same eligible rows.",
        "by_alpha": out,
        "chance_jaccard_at_10": chance_jaccard(cfg["k"], cfg["n_features"]),
        "instability_floor": instability_floor(cfg),
        "limitation": "The below-floor result at alpha=0.1 is directional, not significant (cluster-bootstrap CIs overlap; see ci.json).",
    }
    return write_json(out_dir, "agreement_by_alpha.json", [P["agreement_metrics"], P["instability_floor"], "tools/agreement_metrics.py (chance formula)", P["contribution_a"]], body)


def export_agreement_by_round(cfg, out_dir):
    P = cfg["paths"]
    rw = pd.read_csv(ROOT / P["round_wise_agreement"])
    meta = load_json(P["round_wise_metadata"])
    out = {}
    for a in cfg["alphas"]:
        rows = {}
        for r in cfg["rounds_wise"]:
            sub = rw[(rw.alpha == a) & (rw["round"] == r)]
            vals = [
                load_json(f"{P['federated_dir']}/{tag('fedavg', a, s)}/round_history.json")
                for s in cfg["seeds"]
            ]
            val = [next(x["val_macro_f1_headline"] for x in rh if x["round"] == r) for rh in vals]
            rows[str(r)] = {
                "jaccard_at_10_mean": sub["jaccard_at_10"].mean(),
                "weighted_tau_mean": sub["tau_w"].mean(),
                "val_macro_f1_headline_mean": float(np.mean(val)),
                "val_macro_f1_headline_per_seed": dict(zip(map(str, cfg["seeds"]), val)),
                "n_silo_rows": int(len(sub)),
            }
        out[alpha_key(a)] = rows
    body = {
        "rounds": cfg["rounds_wise"],
        "by_alpha_round": out,
        "nsamples_note": meta["nsamples_note"],
        "metadata": meta,
        "limitation": "Directional, not formally tested. SHAP at reduced fidelity (nsamples=1000), so magnitudes are not comparable to headline agreement numbers.",
    }
    return write_json(out_dir, "agreement_by_round.json",
                      [P["round_wise_agreement"], P["round_wise_metadata"], f"{P['federated_dir']}/fedavg_a<alpha>_s<seed>/round_history.json", P["contribution_a"]], body)


# ---------------------------------------------------------------- parity monitor
def export_parity(cfg, out_dir):
    P = cfg["paths"]
    df = pd.read_csv(ROOT / P["parity_monitor"])
    meta = load_json(P["parity_monitor_metadata"])
    flagged = df[df.flagged]
    med = df.groupby(["alpha", "round"]).agg(median_silo_deviation=("silo_deviation", "median"), n_silos=("silo_id", "size"), n_flagged=("flagged", "sum")).reset_index()
    body = {
        "n_rows": int(len(df)),
        "n_flagged": int(len(flagged)),
        "flagged_rows": flagged.to_dict(orient="records"),
        "by_alpha_round": med.to_dict(orient="records"),
        "rows": df.to_dict(orient="records"),
        "metadata": {k: meta[k] for k in ("generated_by", "scope", "k", "n_draws", "rseeds", "nsamples", "rounds_run", "n_eval_rows", "eligibility_filters",
                                          "silo_deviation", "threshold_method", "why_averaged", "n_rows")},
        "limitation": "Zero flags at alpha=0.1 does not mean alpha=0.1 is healthy: the modified-z threshold is relative to each fleet's own spread that round. Flags rely on multi-draw averaging (N>=3).",
    }
    return write_json(out_dir, "parity_monitor.json", [P["parity_monitor"], P["parity_monitor_metadata"], P["contribution_a"]], body)


# ---------------------------------------------------------------- fedprox
def export_fedprox(cfg, out_dir):
    P = cfg["paths"]
    avg = eligible_agreement(cfg)
    prox = pd.read_csv(ROOT / P["agreement_metrics_fedprox"])
    prox = prox[prox[cfg["eligible_column"]]]
    mf = {m["tag"]: m for m in load_json(P["best_rounds_manifest"])}
    mp = {m["tag"]: m for m in load_json(P["best_rounds_manifest_fedprox"])}
    rows = []
    for a in cfg["alphas"]:
        for s in cfg["seeds"]:
            fa = avg[(avg.alpha == a) & (avg.seed == s)]
            fp = prox[(prox.alpha == a) & (prox.seed == s)]
            ta, tp = mf[tag("fedavg", a, s)], mp[tag("fedprox_mu0.0005", a, s)]
            row = {
                "alpha": a, "seed": s, "n_eligible_rows_fedavg": int(len(fa)), "n_eligible_rows_fedprox": int(len(fp)),
                "fedavg": {"jaccard_at_10_mean": fa.jaccard_at_10.mean(), "weighted_tau_mean": fa.kendall_weighted_tau.mean(), "test_macro_f1_headline": ta["test_macro_f1_headline"], "best_round": ta["best_round"]},
                "fedprox_mu0.0005": {"jaccard_at_10_mean": fp.jaccard_at_10.mean(), "weighted_tau_mean": fp.kendall_weighted_tau.mean(), "test_macro_f1_headline": tp["test_macro_f1_headline"], "best_round": tp["best_round"]},
            }
            row["delta"] = {
                "jaccard_at_10": row["fedprox_mu0.0005"]["jaccard_at_10_mean"] - row["fedavg"]["jaccard_at_10_mean"],
                "weighted_tau": row["fedprox_mu0.0005"]["weighted_tau_mean"] - row["fedavg"]["weighted_tau_mean"],
                "test_macro_f1_headline": row["fedprox_mu0.0005"]["test_macro_f1_headline"] - row["fedavg"]["test_macro_f1_headline"],
            }
            rows.append(row)
    body = {
        "mu": 0.0005,
        "aggregation_note": "MEAN (not median) of Jaccard@10 / weighted tau over family_eligible==True rows per (alpha, seed), as in docs/contribution_a_results.md §6. delta = FedProx - FedAvg.",
        "rows": rows,
        "limitation": "FedProx results are at mu=0.0005 only (not swept). alpha=0.5: agreement up with flat accuracy in all 3 seeds on Jaccard@10; alpha=0.1 inconclusive at n=3 (agreement and accuracy move together); alpha=5.0 no effect.",
    }
    return write_json(out_dir, "fedprox_vs_fedavg.json",
                      [P["agreement_metrics"], P["agreement_metrics_fedprox"], P["best_rounds_manifest"], P["best_rounds_manifest_fedprox"], P["contribution_a"]], body)


# ---------------------------------------------------------------- ByzAgent
def flip_table(cfg, attack_tag):
    """{(round, silo): flip_fraction} + malicious silos, straight from flip_log.csv / attack_config.json."""
    base = f"{cfg['paths']['attacks_dir']}/{attack_tag}"
    ac = load_json(f"{base}/attack_config.json")
    fl = pd.read_csv(ROOT / base / "flip_log.csv")
    flips = {(int(r["round"]), int(r.silo_id)): r.flip_fraction for _, r in fl.iterrows()}
    return ac, flips, base


def export_byzagent(cfg, out_dir):
    P = cfg["paths"]
    src = [P["contribution_b"], P["project_instructions"]]
    seeds_out = {}
    for blk in cfg["byzagent"]:
        conds = {}
        for c in blk["conditions"]:
            path = f"{P['federated_dir']}/{c['run']}/{c['file']}"
            src.append(path)
            rows = load_jsonl(path)
            if c["attack"]:
                ac, flips, base = flip_table(cfg, c["attack"])
                src += [f"{base}/attack_config.json", f"{base}/flip_log.csv"]
                mal = ac["malicious_silos"]
                attack = {k: ac[k] for k in ("f", "mode", "strategy", "malicious_silos", "attack_seed", "sudden", "gradual")}
            else:
                mal, flips, attack = [], {}, None
            decisions = []
            for r in rows:
                silo = int(r["silo_id"].split("_")[1])
                st = r["raw_stats_given"]
                decisions.append({
                    "round": r["round"], "silo": silo, "decision": r["decision"], "explanation": r["explanation"],
                    "is_malicious": silo in mal,
                    "flip_fraction": flips.get((r["round"], silo), 0.0) if attack else 0.0,
                    "stats": {k: st[k] for k in ("update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy")},
                })
            tally = {}
            for grp, sel in (("malicious", True), ("honest", False)):
                ds = [d["decision"] for d in decisions if d["is_malicious"] == sel]
                if ds:
                    tally[grp] = {"n": len(ds), **{k: ds.count(k) for k in ("trust", "downweight", "quarantine")}}
            conds[c["name"]] = {"run": c["run"], "run_file": path, "attack": attack, "true_malicious_silos": mal,
                                "decision_counts": tally, "decisions": decisions}
        seeds_out[str(blk["seed"])] = conds
    body = {
        "alpha": 0.5,
        "n_silos": 10,
        "n_rounds": 20,
        "decision_labels": ["trust", "downweight", "quarantine"],
        "by_seed": seeds_out,
        "locked_claim": ("Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; "
                         "real attack-responsive detection is also present and becomes visible where silos are not already saturated. "
                         "Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition."),
        "caveats": [
            "Clean and attack conditions are always shown together: the agent flags silos (quarantine/downweight) even when nobody is attacking, because of a compositional confound.",
            "Explainability wording: the agent produces decisions plus a rationale of measured fidelity; roughly 35-45% of trend claims contradicted the data they were given (docs/contribution_b_results.md §8).",
            "LLM decisions are nondeterministic; seed 42 clean/sudden/gradual condition files come from single runs.",
            "Agent sees only per-silo behaviour statistics (stats); is_malicious/flip_fraction are ground truth from attack_config.json/flip_log.csv, never shown to the agent.",
            "train_loss is the only strong attack signal; val_accuracy inverts (malicious silos score higher on a Benign-heavy validation set).",
            "Rolling-history variants failed their pre-registered test and are not exported.",
            "Phase 4 matrix and gradual mode are n=1 by design.",
        ],
    }
    return write_json(out_dir, "byzagent_decisions.json", sorted(set(src)), body)


# ---------------------------------------------------------------- baselines
def export_baselines(cfg, out_dir):
    P, fw = cfg["paths"], cfg["final_window"]
    fd = P["federated_dir"]
    src = [P["contribution_b"], P["project_instructions"], "scripts/phase2_analysis.py (recovery_fraction definition + locked anchors)"]
    ref = cfg["baseline_reference"]
    ref_stats = {c: four_stats(val_series(cfg, ref[c]), fw) for c in ("clean", "f3", "f2")}
    ref_test = load_json(f"{fd}/{ref['clean']}/final_metrics.json")
    src += [f"{fd}/{ref[c]}/round_history.json" for c in ref] + [f"{fd}/{ref['clean']}/final_metrics.json"]
    clean_final5 = ref_stats["clean"]["final5mean"]
    clean_test = ref_test["test"]["macro_f1_headline"]

    strategies = []
    for b in cfg["baselines"]:
        entry = {"strategy": b["strategy"], "label": b["label"], "role": b["role"], "oracle_defense": True, "conditions": {}}
        for cond in ("f3", "f2", "clean"):
            run = b["runs"][cond]
            d = f"{fd}/{run}"
            stats = four_stats(val_series(cfg, run), fw)
            val_sum = load_json(f"{d}/attack_val_summary.json") if cond != "clean" else None
            dcfg = load_json(f"{d}/defense_config.json")
            src += [f"{d}/round_history.json", f"{d}/defense_config.json"]
            e = {"run": run, "val_macro_f1_headline": stats, "num_malicious_nodes_oracle": dcfg["num_malicious_nodes_oracle"]}
            if val_sum:
                e["best_round"], e["best_val_macro_f1_headline"] = val_sum["best_round"], val_sum["best_val_macro_f1_headline"]
                src.append(f"{d}/attack_val_summary.json")
                la = cfg["locked_anchors"][cond]
                gap = la["clean_final5mean"] - la["poisoned_fedavg_final5mean"]
                e["recovery_fraction"] = (stats["final5mean"] - la["poisoned_fedavg_final5mean"]) / gap
                e["recovery_anchor"] = {**la, "gap": gap, "source": "locked anchors, docs/contribution_b_results.md §4 / scripts/phase2_analysis.py ANCHORS"}
                ref_c = ref_stats[cond]
                e["recovery_fraction_unrounded_anchors_not_for_display"] = (stats["final5mean"] - ref_c["final5mean"]) / (clean_final5 - ref_c["final5mean"])
            else:
                fm = load_json(f"{d}/final_metrics.json")
                src.append(f"{d}/final_metrics.json")
                t, tf = fm["test"]["macro_f1_headline"], fm["test_final_round_unselected"]["macro_f1_headline"]
                e["best_round"], e["best_val_macro_f1_headline"] = fm["best_round"], fm["best_val_macro_f1_headline"]
                e["test_macro_f1_headline_best_by_val"] = t
                e["test_macro_f1_headline_final_round"] = tf
                e["fedavg_clean_test_macro_f1_headline"] = clean_test
                e["clean_control_cost_pp"] = (t - clean_test) * 100
            # mechanism-level
            if b["kind"] == "krum":
                sel = load_jsonl(f"{d}/krum_selection.jsonl")
                src.append(f"{d}/krum_selection.jsonl")
                sdf = pd.DataFrame(sel)
                excl = 1 - sdf.groupby("silo_id")["selected"].mean()
                n_sel = int(sdf.num_nodes_to_select.iloc[0])
                e["mechanism"] = {"type": "krum_selection", "num_nodes_to_select": n_sel, "chance_exclusion_rate": (10 - n_sel) / 10,
                                  "per_silo_exclusion_rate": {str(k): v for k, v in excl.items()},
                                  "always_excluded_silos": [int(k) for k, v in excl.items() if v == 1.0]}
            else:
                tr = pd.DataFrame(load_jsonl(f"{d}/trim_rate.jsonl"))
                src.append(f"{d}/trim_rate.jsonl")
                beta = float(tr.beta.iloc[0])
                e["mechanism"] = {"type": "trim_rate", "beta": beta, "chance_trim_rate_2beta": 2 * beta,
                                  "per_silo_mean_trim_rate": {str(k): v for k, v in tr.groupby("silo_id")["trim_rate"].mean().items()}}
            if cond != "clean":
                ac = load_json(f"{cfg['paths']['attacks_dir']}/{cfg['baseline_attack_configs'][cond]}/attack_config.json")
                mal = ac["malicious_silos"]
                e["true_malicious_silos"] = mal
                m = e["mechanism"]
                if m["type"] == "krum_selection":
                    sub = sdf[sdf.silo_id.isin(mal)]
                    m["malicious_exclusion_rate"] = 1 - sub["selected"].mean()
                else:
                    m["malicious_mean_trim_rate"] = tr[tr.silo_id.isin(mal)]["trim_rate"].mean()
                    m["malicious_minus_2beta"] = m["malicious_mean_trim_rate"] - m["chance_trim_rate_2beta"]
            entry["conditions"][cond] = e
        strategies.append(entry)
    body = {
        "alpha": 0.5, "seed": 42, "n_rounds": 20, "n_silos": 10,
        "reference_fedavg": {"clean": ref_stats["clean"], "f3_poisoned": ref_stats["f3"], "f2_poisoned": ref_stats["f2"], "clean_test_macro_f1_headline": clean_test},
        "strategies": strategies,
        "stat_definitions": "val_macro_f1_headline over rounds 1..20 (round 0 = untrained init excluded): mean, median, final5mean (rounds 16-20), max. recovery_fraction = (final5mean - poisoned FedAvg final5mean) / (clean FedAvg final5mean - poisoned FedAvg final5mean), using the LOCKED 4-decimal anchors (clean 0.9513; poisoned FedAvg 0.8746 at f=3, 0.8787 at f=2) exactly as in docs/contribution_b_results.md.",
        "caveats": [
            "All three baselines were given the TRUE number of attackers (oracle f). ByzAgent is never given this.",
            "Classical Krum is a secondary sanity check, not a standalone baseline. Its mechanical exclusion rate of 1.0 is chance-level here (it always selects 1 of 10 silos, so 9/10 are always excluded).",
            "Multi-Krum's f=2 recovery_fraction > 1 is a compositional artifact (it excludes the same large Benign-heavy silos with or without an attacker), NOT evidence of attack mitigation.",
            "Krum-family exclusion is dominated by silo size/composition, not attack behaviour: malicious exclusion rate 0 for Multi-Krum in both conditions.",
            "Trimmed-mean trim rates track the same compositional confound; chance baseline is 2*beta (the originally pre-registered f/n baseline was wrong).",
            "Poisoned-condition rows are validation macro-F1 only (test set was evaluated once, on clean-control runs); clean_control_cost_pp is a test-set difference vs clean FedAvg.",
            "Single seed (42): baselines are n=1 by design.",
        ],
    }
    return write_json(out_dir, "baselines.json", sorted(set(src)), body)


# ---------------------------------------------------------------- replay alerts
def export_replay(cfg, out_dir):
    P = cfg["paths"]
    pool = np.load(ROOT / P["streamed_pool"], allow_pickle=True)
    sent = load_json(P["sentences"])
    cls = [str(c) for c in pool["class_names"]]
    alerts = []
    for i, sid in enumerate(pool["sample_id"].tolist()):
        row = sent["rows"][str(sid)]
        assert row["source"] == cfg["replay"]["source_label"], (sid, row["source"])
        assert row["sample_id"] == sid
        true_family = str(pool["eval_families"][i])
        assert cls[int(pool["eval_y"][i])] == true_family
        alerts.append({
            "seq": i,
            "sample_id": sid,
            "true_family": true_family,
            "predicted_family": row["predicted_family"],
            "correct": row["predicted_family"] == true_family,
            "confidence": row["confidence"],
            "top_features": [{"name": f["name"], "shap_value": f["shap_value"]} for f in row["top_features"]],
            "sentence": row["sentence"],
        })
    n_stream = sum(1 for r in sent["rows"].values() if r["source"] == cfg["replay"]["source_label"])
    assert n_stream == len(alerts), (n_stream, len(alerts))
    body = {
        "tag": sent["tag"],
        "n_alerts": len(alerts),
        "order": "Stored order of streamed_pool.npz (sample_id array); not shuffled.",
        "sentence_generator": {k: sent[k] for k in ("model", "temperature", "top_k", "prompt_template_sha256")},
        "shap_note": "shap_value = SHAP value of the predicted class for that feature (GradientExplainer, client-side, fixed seeded background); top-5 by |SHAP|.",
        "caveats": [
            "Raw feature values are not exported (dataset not redistributed). The analyst sentences were generated by an LLM from raw values and may quote a few of them in prose.",
            "The sentences are a usability feature, not a research claim; ~35-45% of LLM trend claims contradicted their data in the ByzAgent audit.",
            "Served demo model fedavg_a0.5_s42 (round 18, val macro-F1 0.9760). These are real model outputs on a pool of 500 test rows, which were read once for display only; no metric derives from them.",
        ],
        "alerts": alerts,
    }
    return write_json(out_dir, "replay_alerts.json", [P["streamed_pool"], P["sentences"], P["contribution_a"]], body)


# ---------------------------------------------------------------- CI and KL partial (re-run committed scripts, read-only)
def export_ci(cfg, out_dir):
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from chat04_closeout import cluster_bootstrap_median, N_BOOT, RNG_SEED  # reused, not reimplemented
    P, bc = cfg["paths"], cfg["bootstrap"]
    df = pd.read_csv(ROOT / P["agreement_metrics"])
    df = df[df[cfg["eligible_column"]]].copy()
    df["alpha"] = df["alpha"].astype(str)
    sub = df[df.alpha == bc["alpha"]]
    res = {}
    for m in bc["metrics"]:
        point, lo, hi, n_clusters = cluster_bootstrap_median(sub, bc["cluster_cols"], m, N_BOOT, RNG_SEED)
        res[m] = {"median": point, "ci95_low": lo, "ci95_high": hi, "n_clusters": n_clusters}
    fl = instability_floor(cfg)
    j = res["jaccard_at_10"]
    flo, fhi = fl["jaccard_at_10_range"]
    body = {
        "alpha": float(bc["alpha"]),
        "method": "cluster bootstrap (resample (seed, silo) clusters with replacement, median of all rows), 95% percentile CI",
        "n_boot": N_BOOT, "rng_seed": RNG_SEED, "cluster_cols": bc["cluster_cols"],
        "by_metric": res,
        "instability_floor_jaccard_at_10_range": [flo, fhi],
        "ci_overlaps_floor_range": not (j["ci95_high"] < flo or j["ci95_low"] > fhi),
        "reading": "Directional, not significant: the alpha=0.1 Jaccard@10 CI overlaps the centralized-seed instability floor range. The floor's 3 seed-pairs are not independent. Reported only for alpha=0.1 (the only slice a CI was computed for).",
    }
    return write_json(out_dir, "ci.json", ["tools/chat04_closeout.py::cluster_bootstrap_median", "tools/plot_instability_floor_vs_alpha.py (call pattern)", P["agreement_metrics"], P["instability_floor"], P["contribution_a"]], body)


def export_kl_partial(cfg, out_dir):
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from plot_entropy_kl_partial_correlation import partial_corr  # reused, not reimplemented
    from scipy.stats import pearsonr
    kc = cfg["kl_partial"]
    df = pd.read_csv(ROOT / kc["path"])
    df["alpha"] = df["alpha"].astype(str)
    df.loc[df["alpha"] == "5", "alpha"] = "5.0"
    reported = {tuple(r) for r in kc["reported_in_doc"]}
    rows = []
    for a in kc["alphas"]:
        s = df[df.alpha == a]
        z = s[kc["control"]].to_numpy()
        for cov in kc["covariates"]:
            for m in ("jaccard_at_10", "kendall_weighted_tau"):
                x, y = s[cov].to_numpy(), s[m].to_numpy()
                rows.append({"alpha": float(a), "covariate": cov, "metric": m, "n": int(len(s)),
                             "zero_order_r": pearsonr(x, y)[0], "partial_r_controlling_log_size": partial_corr(x, y, z),
                             "reported_in_doc": (a, cov, m) in reported})
    body = {
        "control": kc["control"],
        "rows": rows,
        "reporting_rule": "Report r and n only, no p-values (silos within a seed are not independent). Show only rows with reported_in_doc=true; the others are computed by the same script but not in the doc.",
        "ordering_note": "Entropy was the pre-specified covariate and failed conditioning on log(size) (partial r flips sign at alpha=0.5); KL from global was substituted after. State that order.",
        "limitation": "Observational: silo size and heterogeneity are jointly determined by the same Dirichlet draw; size-controlled partitions were proven impossible under this partitioner.",
    }
    return write_json(out_dir, "kl_partial.json", ["tools/plot_entropy_kl_partial_correlation.py::partial_corr", kc["path"], cfg["paths"]["contribution_a"]], body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CFG_PATH))
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    out_dir = ROOT / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for fn in (export_headline, export_agreement_by_alpha, export_agreement_by_round, export_parity, export_fedprox,
               export_byzagent, export_baselines, export_replay, export_ci, export_kl_partial):
        p = fn(cfg, out_dir)
        print(f"wrote {p.relative_to(ROOT)}  ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
