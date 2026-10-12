"""Seal the chosen configuration's best-by-validation checkpoints (Step 2).

  python tools/seal_federated_method.py

Requires results/federated_methods/selection.json with outcome "selected".
For every (alpha, seed) in experiment.test_alphas x seeds: checks the run is
validation-only, that model_best.pt equals round_checkpoints/round_<best>.pt
tensor-for-tensor, and records the SHA256 of the file bytes and of the
tensor content. Writes results/federated_methods/sealed_checkpoints.json.
Opens no test data.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "federated_methods.yaml").read_text())
EXP = CFG["experiment"]
RES = ROOT / EXP["results_root"]


def file_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def state_sha256(sd: dict) -> str:
    # Same construction as federated/xfed_federated/task.py::state_dict_sha256.
    h = hashlib.sha256()
    for k in sorted(sd):
        h.update(k.encode("utf-8"))
        h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def main() -> None:
    sel = json.loads((RES / "selection.json").read_text())
    if sel["outcome"] != "selected":
        raise SystemExit(f"outcome is {sel['outcome']!r}: nothing to seal, the test set is not touched")
    method = sel["chosen"]

    sealed = []
    for a in EXP["test_alphas"]:
        group = "runs" if a in EXP["alphas"] else "chosen"
        for s in EXP["seeds"]:
            d = RES / group / f"{method}_a{a}_s{s}"
            rs = json.loads((d / "run_summary.json").read_text())
            if rs["test_evaluated"] is not False or (d / "final_metrics.json").exists():
                raise SystemExit(f"{d}: not a validation-only run")
            best = torch.load(d / "model_best.pt", map_location="cpu", weights_only=True)
            rnd = torch.load(d / "round_checkpoints" / f"round_{rs['best_round']:03d}.pt",
                             map_location="cpu", weights_only=True)
            if best.keys() != rnd.keys() or any(not torch.equal(best[k], rnd[k]) for k in best):
                raise SystemExit(f"{d}: model_best.pt differs from round_{rs['best_round']:03d}.pt")
            st = state_sha256(best)
            if st != rs["model_best_state_sha256"]:
                raise SystemExit(f"{d}: state hash {st} != logged {rs['model_best_state_sha256']}")
            sealed.append({
                "method": method, "alpha": a, "seed": s,
                "path": str((d / "model_best.pt").relative_to(ROOT)).replace("\\", "/"),
                "best_round": rs["best_round"],
                "best_val_macro_f1_headline": rs["best_val_macro_f1_headline"],
                "file_sha256": file_sha256(d / "model_best.pt"),
                "state_sha256": st,
            })

    out = {"method": method, "method_yaml": CFG["methods"][method], "checkpoints": sealed}
    (RES / "sealed_checkpoints.json").write_text(json.dumps(out, indent=2))
    for c in sealed:
        print(f"{c['alpha']:>4} {c['seed']:>5} r{c['best_round']:02d} val {c['best_val_macro_f1_headline']:.4f} "
              f"{c['file_sha256']}")


if __name__ == "__main__":
    main()
