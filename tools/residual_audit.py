#!/usr/bin/env python
"""Read-only audit of GradientExplainer additivity residuals in the SHAP files
the explanation check used: FedAvg and FedProx (mu=0.0005), every alpha x seed,
the global model and every silo, for the final checkpoints and for the
round-wise pass (rounds 5/10/15/20, nsamples=1000).

Stored files only. Each file's additivity_max_diff is a single scalar: the
largest |sum(SHAP) - (f(x) - E[f])| over that file's 14 fixed eval rows and 9
classes, logit units. Nothing here runs a model, and test rows are never
read -- the scalars were written when those files were built.

Per-silo Jaccard@10 for the Spearman correlation is the median over
family-eligible (silo, sample) rows, the aggregation
tools/per_silo_breakdown.py used for results/inspection/per_silo_agreement.csv.
That aggregation is re-applied to the FedProx sample-level file and checked
against per_silo_agreement.csv on the FedAvg file first. Round-wise rows use
results/inspection/round_wise_agreement.csv (already per silo). r and n only,
no p-values (silos within a seed are not independent).

Writes results/inspection/residual_audit.csv and residual_audit_summary.json.
Run as: python -m tools.residual_audit
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
SHAP_ROOT = ROOT / "results" / "shap"
INSPECTION = ROOT / "results" / "inspection"
VAL_POOL_SUMMARY = SHAP_ROOT / "fedavg_a0.5_s42" / "val_pool_summary.json"

ALGOS = {"fedavg": "fedavg", "fedprox_mu0.0005": "fedprox_mu0.0005"}
AGREEMENT_FILES = {
    "fedavg": INSPECTION / "agreement_metrics.csv",
    "fedprox_mu0.0005": INSPECTION / "agreement_metrics_fedprox_mu0.0005.csv",
}
TAG_RE = re.compile(r"^(fedavg|fedprox_mu0\.0005)_a([0-9.]+)_s(\d+)$")
MODEL_RE = re.compile(r"^(global|silo_(\d+))_shap\.npz$")


def _scan() -> pd.DataFrame:
    rows = []
    for tag_dir in sorted(SHAP_ROOT.iterdir()):
        m = TAG_RE.match(tag_dir.name)
        if not m:
            continue
        algo, alpha, seed = m.group(1), float(m.group(2)), int(m.group(3))
        targets = [(None, tag_dir)]
        rw = tag_dir / "round_wise"
        if rw.is_dir():
            targets += [(int(d.name.split("_")[1]), d) for d in sorted(rw.iterdir()) if d.is_dir()]
        for rnd, d in targets:
            for f in sorted(d.glob("*_shap.npz")):
                mm = MODEL_RE.match(f.name)
                if not mm:
                    continue
                with np.load(f) as npz:
                    if "additivity_max_diff" not in npz.files:
                        continue
                    resid = float(npz["additivity_max_diff"])
                    n_rows = int(npz["shap_values"].shape[0])
                rows.append({
                    "tag": tag_dir.name, "algo": algo, "alpha": alpha, "seed": seed,
                    "pass": "final" if rnd is None else "round_wise", "round": rnd,
                    "model": "global" if mm.group(1) == "global" else "silo",
                    "silo": None if mm.group(2) is None else int(mm.group(2)),
                    "n_eval_rows": n_rows, "additivity_max_diff": resid,
                    "file": f.relative_to(ROOT).as_posix(),
                })
    return pd.DataFrame(rows)


def _per_silo_jaccard(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    elig = df[df["family_eligible"]]
    return elig.groupby(["alpha", "seed", "silo"])["jaccard_at_10"].median().reset_index()


def main() -> None:
    val_max = json.loads(VAL_POOL_SUMMARY.read_text())["additivity_abs_logit"]["max"]
    audit = _scan()

    # Check the re-applied aggregation reproduces the stored FedAvg per-silo file.
    stored = pd.read_csv(INSPECTION / "per_silo_agreement.csv")
    rebuilt = _per_silo_jaccard(AGREEMENT_FILES["fedavg"])
    chk = stored.merge(rebuilt, on=["alpha", "seed", "silo"], suffixes=("_stored", "_rebuilt"))
    max_diff = float((chk["jaccard_at_10_stored"] - chk["jaccard_at_10_rebuilt"]).abs().max())
    if len(chk) != len(stored) or max_diff > 1e-9:
        raise RuntimeError(f"per-silo aggregation does not reproduce per_silo_agreement.csv (max diff {max_diff})")

    jac = pd.concat([_per_silo_jaccard(p).assign(algo=a) for a, p in AGREEMENT_FILES.items()])
    rw = pd.read_csv(INSPECTION / "round_wise_agreement.csv").rename(columns={"silo_id": "silo"})

    audit["exceeds_val_pool_max"] = audit["additivity_max_diff"] > val_max
    audit = audit.merge(jac.rename(columns={"jaccard_at_10": "jaccard_at_10_final"}),
                        on=["algo", "alpha", "seed", "silo"], how="left")
    audit.loc[audit["pass"] != "final", "jaccard_at_10_final"] = np.nan
    rw_j = rw[["alpha", "seed", "round", "silo", "jaccard_at_10"]].rename(columns={"jaccard_at_10": "jaccard_at_10_round"})
    audit = audit.merge(rw_j.assign(algo="fedavg", **{"pass": "round_wise"}),
                        on=["algo", "pass", "alpha", "seed", "round", "silo"], how="left")
    audit = audit.sort_values(["algo", "pass", "alpha", "seed", "round", "model", "silo"], na_position="first")
    out_csv = INSPECTION / "residual_audit.csv"
    audit.to_csv(out_csv, index=False)

    def corr(sub: pd.DataFrame, col: str) -> dict:
        sub = sub.dropna(subset=[col])
        if len(sub) < 3:
            return {"r": None, "n": int(len(sub))}
        r = spearmanr(sub["additivity_max_diff"], sub[col]).statistic
        return {"r": round(float(r), 3), "n": int(len(sub))}

    silos = audit[audit["model"] == "silo"]
    summary = {
        "val_pool_max_reference": val_max,
        "per_silo_check_max_abs_diff": max_diff,
        "n_files": int(len(audit)),
        "n_files_by_pass": audit.groupby("pass").size().to_dict(),
        "exceed_val_pool_max": {},
        "spearman_silo_residual_vs_jaccard10": {},
    }
    for (algo, pss), g in audit.groupby(["algo", "pass"]):
        key = f"{algo}/{pss}"
        ex = g[g["exceeds_val_pool_max"]]
        summary["exceed_val_pool_max"][key] = {
            "n_exceed": int(len(ex)), "n_files": int(len(g)),
            "by_alpha": {str(a): f"{int(x.exceeds_val_pool_max.sum())}/{len(x)}" for a, x in g.groupby("alpha")},
            "by_model": {m: f"{int(x.exceeds_val_pool_max.sum())}/{len(x)}" for m, x in g.groupby("model")},
            "by_silo_index": {int(s): int(x.exceeds_val_pool_max.sum())
                              for s, x in g[g.model == "silo"].groupby("silo")},
            "max": round(float(g.additivity_max_diff.max()), 3),
            "median": round(float(g.additivity_max_diff.median()), 3),
        }
    for algo, g in silos[silos["pass"] == "final"].groupby("algo"):
        summary["spearman_silo_residual_vs_jaccard10"][f"{algo}/final"] = {
            str(a): corr(x, "jaccard_at_10_final") for a, x in g.groupby("alpha")
        }
    # One correlation per round: pooling rounds would count each silo 4 times.
    g = silos[(silos["pass"] == "round_wise") & (silos["algo"] == "fedavg")]
    summary["spearman_silo_residual_vs_jaccard10"]["fedavg/round_wise"] = {
        f"alpha={a} round={int(r)}": corr(x, "jaccard_at_10_round") for (a, r), x in g.groupby(["alpha", "round"])
    }
    ex = audit[audit["exceeds_val_pool_max"]]
    summary["files_exceeding"] = [
        {k: (None if pd.isna(v) else v) for k, v in rec.items()}
        for rec in ex[["algo", "pass", "alpha", "seed", "round", "model", "silo", "additivity_max_diff"]]
        .round({"additivity_max_diff": 3}).to_dict("records")
    ]
    (INSPECTION / "residual_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out_csv.relative_to(ROOT).as_posix()} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
