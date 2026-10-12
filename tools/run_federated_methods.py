"""Driver for the preregistered federated optimizer comparison (2026-10-12).

Runs `flwr run federated local-simulation` once per (method, alpha, seed),
strictly sequentially (6 GB GPU; a concurrent run corrupted
fedprox_mu0.0005_a0.1_s42 before). Every method parameter lives in
configs/federated_methods.yaml; this script only passes method name, alpha,
seed and the YAML's rounds/epochs. Method runs are validation-only (see
federated/xfed_federated/server_app.py::_run_method).

  python tools/run_federated_methods.py check-manifest
  python tools/run_federated_methods.py timing --method fedavg --alpha 0.1 --seed 42 --rounds 1
  python tools/run_federated_methods.py estimate
  python tools/run_federated_methods.py run                      # the YAML grid
  python tools/run_federated_methods.py run --group regression --methods fedavg --alphas 0.1 --seeds 42

Already-finished runs (run_summary.json present) are skipped, so an
interrupted grid resumes where it stopped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "configs" / "federated_methods.yaml"
FLWR = Path(sys.executable).parent / "Scripts" / "flwr.exe"


def load_cfg() -> dict:
    return yaml.safe_load(CFG_PATH.read_text())


def git_state() -> dict:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "federated", "configs", "tools"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.strip()
    return {"git_head": head, "harness_dirty": bool(dirty)}


def check_manifest(alphas, seeds) -> list[dict]:
    """Same hash as src/data/partition.py: sha256 of int16 assignment bytes."""
    part = ROOT / "data" / "processed" / "partitions"
    manifest = json.loads((part / "manifest.json").read_text())
    rows = []
    for a in alphas:
        for s in seeds:
            tag = f"a{a}_s{s}"
            for split in ("train", "test"):
                arr = pd.read_parquet(part / f"assign_{tag}_{split}.parquet")["silo"].to_numpy(np.int16)
                got = hashlib.sha256(arr.tobytes()).hexdigest()
                want = manifest["configs"][tag][f"hash_{split}"]
                rows.append({"tag": tag, "split": split, "ok": got == want, "sha256": got})
                if got != want:
                    raise SystemExit(f"MANIFEST MISMATCH {tag} {split}: {got} != {want}. STOP.")
    return rows


def run_dir(cfg: dict, group: str, method: str, alpha: str, seed: int) -> Path:
    return ROOT / cfg["experiment"]["results_root"] / group / f"{method}_a{alpha}_s{seed}"


def launch(cfg: dict, method: str, alpha: str, seed: int, group: str, rounds: int) -> dict:
    exp = cfg["experiment"]
    out = run_dir(cfg, group, method, alpha, seed)
    if (out / "run_summary.json").exists():
        print(f"SKIP (finished): {out.relative_to(ROOT)}")
        return {"skipped": True}

    rc = (f"alpha='{alpha}' seed={seed} method='{method}' run-group='{group}' "
          f"num-server-rounds={rounds} local-epochs={exp['local_epochs']}")
    log_dir = ROOT / exp["results_root"] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{group}_{method}_a{alpha}_s{seed}.log"
    # flwr spawns flower-superlink by name, so the env's Scripts dir and
    # root must be on PATH even when this script is run by absolute python.
    env_bin = [str(FLWR.parent), str(FLWR.parent.parent), str(FLWR.parent.parent / "Library" / "bin")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               PATH=os.pathsep.join(env_bin + [os.environ.get("PATH", "")]))

    print(f"\n=== {group}: {method} alpha={alpha} seed={seed} rounds={rounds} ===", flush=True)
    t0 = time.perf_counter()
    started = dt.datetime.now().isoformat(timespec="seconds")
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(FLWR), "run", "federated", "local-simulation", "--run-config", rc, "--stream"],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            log.write(line)
            if "round" in line and "val macro-F1" in line or "best val" in line or "Error" in line:
                print("   " + line.rstrip(), flush=True)
        proc.wait()
    wall = time.perf_counter() - t0

    problems = []
    if not (out / "run_summary.json").exists():
        problems.append("run_summary.json missing")
    else:
        hist = json.loads((out / "round_history.json").read_text())
        if len(hist) != rounds + 1:
            problems.append(f"round_history has {len(hist)} rows, expected {rounds + 1}")
        timing = (out / "round_timing_comm.jsonl").read_text().splitlines()
        if len(timing) != rounds:
            problems.append(f"round_timing_comm has {len(timing)} rows, expected {rounds}")
        if exp.get("save_round_checkpoints", True):
            n_ck = len(list((out / "round_checkpoints").glob("round_*.pt")))
            if n_ck != rounds + 1:
                problems.append(f"{n_ck} round checkpoints, expected {rounds + 1}")
        if (out / "final_metrics.json").exists():
            problems.append("final_metrics.json exists -- a test evaluation happened. STOP.")

    row = {
        "group": group, "method": method, "alpha": alpha, "seed": seed, "rounds": rounds,
        "started": started, "process_wall_s": wall, "returncode": proc.returncode,
        "ok": not problems, "problems": problems, "log": str(log_path.relative_to(ROOT)),
        **git_state(),
    }
    with open(ROOT / exp["results_root"] / "run_log.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    status = "PASS" if not problems else "FAIL"
    print(f"{status} {method} a{alpha} s{seed}  {wall / 60:.1f} min  {problems or ''}", flush=True)
    if problems:
        raise SystemExit(f"Stopping: {problems}. Log: {log_path}")
    return row


def estimate(cfg: dict) -> dict:
    """Per-run time = process startup/teardown overhead + rounds x per-round
    time, both measured from the timing run(s); total over the planned runs."""
    exp = cfg["experiment"]
    log = [json.loads(l) for l in (ROOT / exp["results_root"] / "run_log.jsonl").read_text().splitlines()]
    timing_runs = [r for r in log if r["group"] == "timing" and r["ok"]]
    if not timing_runs:
        raise SystemExit("no timing run in run_log.jsonl")
    per_round, overhead = [], []
    for r in timing_runs:
        d = run_dir(cfg, "timing", r["method"], r["alpha"], r["seed"])
        rows = [json.loads(l) for l in (d / "round_timing_comm.jsonl").read_text().splitlines()]
        rt = [x["wall_time_s"] for x in rows]
        per_round.extend(rt)
        overhead.append(r["process_wall_s"] - sum(rt))
    sec_round = float(np.mean(per_round))
    sec_overhead = float(np.mean(overhead))
    sec_run = sec_overhead + exp["num_server_rounds"] * sec_round

    n_grid = len(cfg["grid"]) * len(exp["alphas"]) * len(exp["seeds"])
    n_extra_alpha = len(set(exp["test_alphas"]) - set(exp["alphas"])) * len(exp["seeds"])  # chosen config only
    n_regression = 1  # fedavg re-run on the new path vs the published curve
    n_total = n_grid + n_extra_alpha + n_regression
    hours = n_total * sec_run / 3600
    est = {
        "timing_runs": [f"{r['method']}_a{r['alpha']}_s{r['seed']}" for r in timing_runs],
        "sec_per_round_mean": sec_round,
        "sec_per_round_values": per_round,
        "sec_process_overhead_mean": sec_overhead,
        "sec_per_20_round_run": sec_run,
        "runs_grid": n_grid,
        "runs_chosen_config_extra_alpha": n_extra_alpha,
        "runs_regression_check": n_regression,
        "runs_total": n_total,
        "estimated_gpu_hours": hours,
        "budget_gpu_hours": exp["budget_gpu_hours"],
        "over_budget": hours > exp["budget_gpu_hours"],
    }
    (ROOT / exp["results_root"] / "budget_estimate.json").write_text(json.dumps(est, indent=2))
    return est


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-manifest")
    t = sub.add_parser("timing")
    t.add_argument("--method", required=True)
    t.add_argument("--alpha", required=True)
    t.add_argument("--seed", type=int, required=True)
    t.add_argument("--rounds", type=int, required=True)
    sub.add_parser("estimate")
    r = sub.add_parser("run")
    r.add_argument("--methods", nargs="+")
    r.add_argument("--alphas", nargs="+")
    r.add_argument("--seeds", nargs="+", type=int)
    r.add_argument("--group", default="runs",
                   help="runs (candidates), regression (fedavg on the new path vs the published curve), "
                        "or chosen (the selected config at extra alphas)")
    args = ap.parse_args()

    cfg = load_cfg()
    exp = cfg["experiment"]
    (ROOT / exp["results_root"]).mkdir(parents=True, exist_ok=True)

    if args.cmd == "check-manifest":
        rows = check_manifest(sorted(set(exp["alphas"]) | set(exp["test_alphas"])), exp["seeds"])
        (ROOT / exp["results_root"] / "manifest_check.json").write_text(json.dumps({
            "checked_at": dt.datetime.now().isoformat(timespec="seconds"), "rows": rows}, indent=2))
        print(f"manifest OK for {len(rows)} assignment files")
    elif args.cmd == "timing":
        launch(cfg, args.method, args.alpha, args.seed, "timing", args.rounds)
    elif args.cmd == "estimate":
        print(json.dumps(estimate(cfg), indent=2))
    elif args.cmd == "run":
        methods = args.methods or cfg["grid"]
        alphas = args.alphas or exp["alphas"]
        seeds = args.seeds or exp["seeds"]
        for m in methods:
            if m not in cfg["methods"]:
                raise SystemExit(f"unknown method {m}")
        check_manifest(alphas, seeds)
        for i, m in enumerate(methods):
            if args.group == "runs" and not budget_allows(cfg, methods[i:], alphas, seeds):
                print(f"BUDGET GUARD: dropping {methods[i:]} (see budget_guard.jsonl)")
                break
            for a in alphas:
                for s in seeds:
                    launch(cfg, m, a, s, args.group, int(exp["num_server_rounds"]))


def budget_allows(cfg: dict, remaining_methods: list[str], alphas, seeds) -> bool:
    """Timing-only budget guard (prereg Part 1, 2026-10-12). Before a
    candidate starts: elapsed wall time of every logged run + mean candidate
    run time x (runs still needed for this and all later candidates + the
    chosen config's extra-alpha runs) must fit experiment.budget_gpu_hours.
    If not, this candidate and all later ones are dropped, whole, in grid
    order. Reads run_log.jsonl wall times only, never a validation score.
    A candidate that has already started is never dropped."""
    exp = cfg["experiment"]
    log_path = ROOT / exp["results_root"] / "run_log.jsonl"
    log = [json.loads(l) for l in log_path.read_text().splitlines()]
    elapsed = sum(r["process_wall_s"] for r in log)
    cand = [r["process_wall_s"] for r in log if r["group"] == "runs" and r["ok"]]
    if not cand:
        return True
    mean_run = float(np.mean(cand))
    started = any(run_dir(cfg, "runs", remaining_methods[0], a, s).exists() for a in alphas for s in seeds)
    if started:
        return True
    todo = sum(1 for m in remaining_methods for a in alphas for s in seeds
               if not (run_dir(cfg, "runs", m, a, s) / "run_summary.json").exists())
    extra = len(set(exp["test_alphas"]) - set(exp["alphas"])) * len(exp["seeds"])
    projected_h = (elapsed + mean_run * (todo + extra)) / 3600
    ok = projected_h <= exp["budget_gpu_hours"]
    rec = {"checked_at": dt.datetime.now().isoformat(timespec="seconds"),
           "next_candidate": remaining_methods[0], "remaining_candidates": remaining_methods,
           "elapsed_h": elapsed / 3600, "mean_candidate_run_min": mean_run / 60,
           "runs_todo": todo, "extra_alpha_runs": extra, "projected_total_h": projected_h,
           "budget_h": exp["budget_gpu_hours"], "allowed": ok}
    with open(ROOT / exp["results_root"] / "budget_guard.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"budget guard: next={remaining_methods[0]} projected {projected_h:.2f} h -> {'run' if ok else 'DROP'}")
    return ok


if __name__ == "__main__":
    main()
