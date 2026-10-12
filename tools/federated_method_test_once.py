"""The single preregistered test evaluation (Step 3). Run once; never re-run.

  python tools/federated_method_test_once.py

Refuses to start unless:
  * selection.json says "selected" and sealed_checkpoints.json names the same method;
  * docs/preregistration_accuracy.md is committed, has no uncommitted changes,
    and contains the chosen method name and every sealed file SHA256;
  * every checkpoint file still hashes to its sealed SHA256;
  * no earlier attempt exists (results/federated_methods/test_once/ LOCK or result).

Before the test split is touched, every sealed checkpoint's VALIDATION
macro-F1 is recomputed with this script's own pipeline and must equal the
value logged during training -- this proves the evaluation pipeline matches
the harness without looking at test. Then the LOCK file is written, and each
sealed checkpoint is scored on test_global.parquet exactly once.

Output: results/federated_methods/test_once/result.json with the git commit
of the prereg file, per-run metrics, macro-F1 mean +/- std (population,
ddof=0, as in the published table) per alpha, and per-class F1.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet  # noqa: F401  before torch: importing torch first crashes pyarrow's parquet reader on this machine (access violation)
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "federated"))
from xfed_federated._vendored.loaders import load_centralized  # noqa: E402
from xfed_federated._vendored.metrics import compute_metrics  # noqa: E402
from xfed_federated._vendored.mlp import build_model  # noqa: E402
from xfed_federated._vendored.schema import class_names, headline_class_indices  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "federated_methods.yaml").read_text())
RES = ROOT / CFG["experiment"]["results_root"]
OUT = RES / "test_once"
PREREG = ROOT / "docs" / "preregistration_accuracy.md"
DEVICE = "cpu"  # the harness trained and validated on CPU (torch 2.13.0+cpu)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def predict(model, X: np.ndarray, batch: int = 8192) -> np.ndarray:
    model.eval()
    Xt = torch.from_numpy(X.copy())
    out = []
    with torch.no_grad():
        for i in range(0, len(Xt), batch):
            out.append(model(Xt[i:i + batch].to(DEVICE)).argmax(dim=1).cpu())
    return torch.cat(out).numpy()


def main() -> None:
    # ---------------- preconditions (no test data touched) ----------------
    if (OUT / "LOCK").exists() or (OUT / "result.json").exists():
        raise SystemExit(f"{OUT} already holds a test attempt. The test evaluation is never re-run.")
    sel = json.loads((RES / "selection.json").read_text())
    sealed = json.loads((RES / "sealed_checkpoints.json").read_text())
    if sel["outcome"] != "selected" or sel["chosen"] != sealed["method"]:
        raise SystemExit("selection.json and sealed_checkpoints.json disagree, or nothing was selected")
    method = sealed["method"]

    if git("status", "--porcelain", "--", str(PREREG.relative_to(ROOT))):
        raise SystemExit("docs/preregistration_accuracy.md has uncommitted changes")
    prereg_commit = git("log", "-1", "--format=%H", "--", str(PREREG.relative_to(ROOT)))
    if not prereg_commit:
        raise SystemExit("docs/preregistration_accuracy.md is not committed")
    text = PREREG.read_text(encoding="utf-8")
    if method not in text:
        raise SystemExit(f"prereg file does not name {method}")
    for c in sealed["checkpoints"]:
        if c["file_sha256"] not in text:
            raise SystemExit(f"prereg file does not contain sealed hash {c['file_sha256']}")
        got = hashlib.sha256((ROOT / c["path"]).read_bytes()).hexdigest()
        if got != c["file_sha256"]:
            raise SystemExit(f"{c['path']} hash {got} != sealed {c['file_sha256']}")

    model_cfg = yaml.safe_load((ROOT / "configs" / "model.yaml").read_text())
    data_cfg = yaml.safe_load((ROOT / "configs" / "data.yaml").read_text())
    cnames = class_names(model_cfg)
    hidx = headline_class_indices(model_cfg)
    n_classes = int(model_cfg["labels"]["n_classes"])
    split = load_centralized(data_cfg, model_cfg, root=ROOT / "data" / "processed")

    models = {}
    val_check = []
    for c in sealed["checkpoints"]:
        m = build_model(model_cfg, seed=int(c["seed"]), device=DEVICE)
        m.load_state_dict(torch.load(ROOT / c["path"], map_location=DEVICE, weights_only=True))
        v = compute_metrics(split.y_val, predict(m, split.X_val), n_classes, cnames, hidx)["macro_f1_headline"]
        ok = abs(v - c["best_val_macro_f1_headline"]) < 1e-9
        val_check.append({"alpha": c["alpha"], "seed": c["seed"], "recomputed_val": v,
                          "logged_val": c["best_val_macro_f1_headline"], "match": ok})
        if not ok:
            raise SystemExit(f"validation recompute mismatch {c['alpha']}/{c['seed']}: {v} vs "
                             f"{c['best_val_macro_f1_headline']}. Pipeline differs; test NOT touched.")
        models[(c["alpha"], c["seed"])] = m
    print(f"validation recompute matches for all {len(val_check)} sealed checkpoints")

    # ---------------- the one test evaluation ----------------
    OUT.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now().isoformat(timespec="seconds")
    (OUT / "LOCK").write_text(json.dumps({"started": started, "prereg_commit": prereg_commit,
                                          "head": git("rev-parse", "HEAD"), "method": method}, indent=2))

    runs = []
    for c in sealed["checkpoints"]:
        tm = compute_metrics(split.y_test, predict(models[(c["alpha"], c["seed"])], split.X_test),
                             n_classes, cnames, hidx)
        runs.append({**{k: c[k] for k in ("alpha", "seed", "best_round", "path", "file_sha256")}, "test": tm})

    per_alpha = {}
    for a in CFG["experiment"]["test_alphas"]:
        rs = [r for r in runs if r["alpha"] == a]
        mf = np.array([r["test"]["macro_f1_headline"] for r in rs])
        per_alpha[a] = {
            "n": len(rs),
            "macro_f1_headline_mean": float(mf.mean()), "macro_f1_headline_std": float(mf.std()),
            "macro_f1_headline_per_seed": {str(r["seed"]): r["test"]["macro_f1_headline"] for r in rs},
            "per_class_f1_mean": {k: float(np.mean([r["test"]["per_class"][k]["f1"] for r in rs])) for k in cnames},
            "per_class_f1_std": {k: float(np.std([r["test"]["per_class"][k]["f1"] for r in rs])) for k in cnames},
        }

    result = {
        "method": method, "method_yaml": sealed["method_yaml"],
        "prereg_file": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "prereg_commit": prereg_commit, "head_at_evaluation": git("rev-parse", "HEAD"),
        "evaluated_at": started, "device": DEVICE, "torch": torch.__version__,
        "metric": "macro-F1 over 7 headline families (Infiltration, Heartbleed per class only)",
        "std": "population (ddof=0), as in results/aggregated/federated_headline.csv",
        "validation_recompute_check": val_check,
        "per_alpha": per_alpha, "runs": runs,
        "note": "Single preregistered test evaluation. Reported whatever the result. Never re-run.",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2))
    for a, r in per_alpha.items():
        print(f"alpha={a}: test macro-F1 {r['macro_f1_headline_mean']:.4f} +/- {r['macro_f1_headline_std']:.4f}")


if __name__ == "__main__":
    main()
