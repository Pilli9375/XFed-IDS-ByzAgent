"""Efficiency Part C -- runs FedAvg with compressed client->server updates on
the validation-only method path, strictly sequentially, plus one uncompressed
regression run on the same code. Every parameter lives in
configs/efficiency.yaml (compression.runs); the federated method itself in
configs/federated_methods.yaml.

  python tools/efficiency_compression_runs.py

Finished runs (run_summary.json present) are skipped, so an interrupted batch
resumes. Each launch is appended to compression.run_log. No test rows: the
method path has no test evaluation, client evaluate() is off, and a
final_metrics.json appearing in a run directory stops the batch.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path

import yaml

from run_federated_methods import FLWR, ROOT, check_manifest, git_state

EFF_CFG = yaml.safe_load((ROOT / "configs/efficiency.yaml").read_text())["compression"]
FM_CFG = yaml.safe_load((ROOT / "configs/federated_methods.yaml").read_text())


def out_dir(method: str, scheme: str, alpha: str, seed: int, group: str) -> Path:
    method_tag = f"{method}_up-{scheme}" if scheme else method
    return ROOT / FM_CFG["experiment"]["results_root"] / group / f"{method_tag}_a{alpha}_s{seed}"


def launch(method: str, scheme: str, alpha: str, seed: int, group: str) -> None:
    exp = FM_CFG["experiment"]
    rounds = int(exp["num_server_rounds"])
    out = out_dir(method, scheme, alpha, seed, group)
    if (out / "run_summary.json").exists():
        print(f"SKIP (finished): {out.relative_to(ROOT)}")
        return
    rc = (f"alpha='{alpha}' seed={seed} method='{method}' run-group='{group}' "
          f"num-server-rounds={rounds} local-epochs={exp['local_epochs']} "
          f"upload-compression='{scheme}'")
    log_path = ROOT / exp["results_root"] / "logs" / f"{group}_{out.name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env_bin = [str(FLWR.parent), str(FLWR.parent.parent), str(FLWR.parent.parent / "Library" / "bin")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", XFED_PROJECT_ROOT=str(ROOT),
               PATH=os.pathsep.join(env_bin + [os.environ.get("PATH", "")]))
    print(f"\n=== {out.name} ===", flush=True)
    started = dt.datetime.now().isoformat(timespec="seconds")
    t0 = time.perf_counter()
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(FLWR), "run", "federated", "local-simulation", "--run-config", rc, "--stream"],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            log.write(line)
            if "val macro-F1" in line or "best val" in line or "Error" in line:
                print("   " + line.rstrip(), flush=True)
        proc.wait()
    wall = time.perf_counter() - t0

    problems = []
    if not (out / "run_summary.json").exists():
        problems.append("run_summary.json missing")
    else:
        if len(json.loads((out / "round_history.json").read_text())) != rounds + 1:
            problems.append("round_history length")
        if len((out / "round_timing_comm.jsonl").read_text().splitlines()) != rounds:
            problems.append("round_timing_comm length")
        summary = json.loads((out / "run_summary.json").read_text())
        if summary.get("upload_compression") != (scheme or None):
            problems.append(f"run_summary upload_compression={summary.get('upload_compression')!r}")
    if (out / "final_metrics.json").exists():
        problems.append("final_metrics.json exists -- a test evaluation happened. STOP.")
    row = {"run": out.name, "group": group, "method": method, "upload_compression": scheme or None,
           "alpha": alpha, "seed": seed, "rounds": rounds, "started": started,
           "process_wall_s": wall, "returncode": proc.returncode, "ok": not problems,
           "problems": problems, "log": str(log_path.relative_to(ROOT)), **git_state()}
    with open(ROOT / EFF_CFG["run_log"], "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"{'PASS' if not problems else 'FAIL'} {out.name} {wall / 60:.1f} min {problems or ''}", flush=True)
    if problems:
        raise SystemExit(f"Stopping: {problems}. Log: {log_path}")


def main() -> None:
    r = EFF_CFG["runs"]
    alpha, group, method = str(r["alpha"]), r["run_group"], r["method"]
    check_manifest([alpha], sorted(set(r["seeds"]) | set(r["regression_seeds"])))
    for s in r["regression_seeds"]:
        launch(method, "", alpha, int(s), group)
    for scheme in r["schemes"]:
        for s in r["seeds"]:
            launch(method, scheme, alpha, int(s), group)


if __name__ == "__main__":
    main()
