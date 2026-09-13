"""Step 2B: hot-swap orchestration for the live backend.

Hard boundary: src/hotswap/retrain.py (the actual FedAvg-lite training
code) is NEVER imported here, or anywhere else under backend/. It runs
exclusively inside a separate subprocess (tools/hotswap_worker.py),
spawned and polled from this module. This is not a performance
optimization -- it's a survivability guarantee. Step 2A's own proof run
segfaulted twice (heavy pyarrow/parquet reads immediately following torch
training crash this specific process, intermittently, for reasons not
worth chasing further -- subprocess isolation is the right architecture
regardless of root cause). A crash inside this backend's own process
would take /predict down with it; a crash in a worker subprocess cannot
touch this process at all. See trigger()/poll() below for how a crashed
worker is told apart from an accepted or rejected one.

This module only ever touches src.hotswap.audit_log for path CONSTANTS
(LOG_PATH, PROJECT_ROOT) and for read_events()/resolve_event() -- pure
reads of an append-only file, no training, no pyarrow-heavy per-silo
work, safe to call in-process.

Place at: backend/hotswap_service.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass

import torch
import torch.nn as nn

from src.hotswap import audit_log as hs
from src.models.mlp import build_model

JOBS_DIR = hs.LOG_PATH.parent / "jobs"


@dataclass
class HotSwapState:
    """Lives on app.state.hotswap. In-memory only -- a backend restart
    always comes back up serving the base model with active=False,
    regardless of what's in the (persistent) audit log. Deliberate: which
    historical event to "resume" into on restart is genuinely ambiguous,
    and re-deriving it is out of scope here."""

    base_tag: str
    active: bool = False
    event_id: str | None = None
    # Count of accepted swaps since startup/last revert. Every hot-swap
    # warm-starts from base_tag's OWN checkpoint (never from a previous
    # hot-swap's checkpoint, see src/hotswap/retrain.py's source_model_tag
    # resolution) -- so this is an honest activity counter, not a claim
    # that swap N was built on top of swap N-1's weights.
    swap_depth: int = 0
    active_model: nn.Module | None = None
    job_id: str | None = None
    job_process: subprocess.Popen | None = None
    job_status: str | None = None  # "running" | "accepted" | "rejected" | "error" | "crashed" | None
    job_detail: str | None = None
    job_family: str | None = None


def _state_dict_sha256(state_dict: dict) -> str:
    """Duplicated from src/hotswap/retrain.py -- deliberately: importing
    that module here would reintroduce exactly the coupling this file's
    docstring says never to reintroduce. This is pure numpy/torch (no
    pyarrow, no per-silo data work), so it carries none of the actual risk."""
    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode("utf-8"))
        h.update(state_dict[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def new_state(base_tag: str) -> HotSwapState:
    return HotSwapState(base_tag=base_tag)


def trigger(state: HotSwapState, family: str) -> dict:
    """Spawns the worker subprocess. Returns immediately -- does not wait
    for completion. Raises RuntimeError (caller should turn this into a
    409) if a job is already running."""
    if state.job_status == "running":
        raise RuntimeError("a hot-swap job is already running")

    job_id = str(uuid.uuid4())
    # A fresh seed per trigger, generated here (never asked of the caller --
    # an analyst clicks "confirm", they don't supply a seed) and logged by
    # the worker's own call into src.hotswap.audit_log, which is what makes
    # it reproducible after the fact.
    seed = int.from_bytes(uuid.uuid4().bytes[:4], "big")

    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "tools.hotswap_worker",
            "--family", family,
            "--seed", str(seed),
            "--source-tag", state.base_tag,
            "--job-id", job_id,
        ],
        cwd=hs.PROJECT_ROOT,
    )

    state.job_id = job_id
    state.job_process = proc
    state.job_status = "running"
    state.job_detail = None
    state.job_family = family
    return {"job_id": job_id, "status": "running", "family": family, "seed": seed}


def _read_job_result(job_id: str) -> dict | None:
    path = JOBS_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def poll(state: HotSwapState, model_cfg: dict, device: str) -> None:
    """Cheap, non-blocking, idempotent -- call it from any request handler
    that wants up-to-date status (GET /config, GET /hotswap/status). Does
    nothing if no job is running.

    The crash-detection contract: the worker (tools/hotswap_worker.py)
    ALWAYS writes a result file before a clean exit, whether accepted,
    rejected, or an ordinary Python exception. If the process has exited
    (poll() returns non-None) and no result file exists, the worker died
    without finishing -- a segfault, a SIGKILL, anything -- and this
    function marks the job "crashed" without touching state.active_model
    or state.active at all. The served model is whatever it already was.
    """
    if state.job_status != "running" or state.job_process is None:
        return

    ret = state.job_process.poll()
    if ret is None:
        return  # still running

    result = _read_job_result(state.job_id)
    if result is None:
        state.job_status = "crashed"
        state.job_detail = f"worker process exited (code={ret}) without writing a result -- served model unchanged"
        state.job_process = None
        return

    if result["status"] == "accepted":
        ckpt_path = (
            hs.PROJECT_ROOT / "state" / "hotswap_log" / "checkpoints"
            / f"{result['resulting_checkpoint_sha256']}.pt"
        )
        if not ckpt_path.exists():
            state.job_status = "error"
            state.job_detail = f"accepted event's checkpoint file is missing: {ckpt_path}"
            state.job_process = None
            return

        state_dict = torch.load(ckpt_path, map_location=device, weights_only=False)
        recomputed = _state_dict_sha256(state_dict)
        if recomputed != result["resulting_checkpoint_sha256"]:
            # Hash-verified before trusted, per instruction -- refuse to
            # serve a checkpoint whose bytes don't match what the audit
            # record claims, however that mismatch happened.
            state.job_status = "error"
            state.job_detail = (
                f"checkpoint hash mismatch: file hashes to {recomputed}, "
                f"record says {result['resulting_checkpoint_sha256']} -- refusing to serve it"
            )
            state.job_process = None
            return

        model = build_model(model_cfg, seed=0, device=device)  # seed inconsequential -- overwritten below
        model.load_state_dict(state_dict)
        model.eval()

        state.active_model = model
        state.active = True
        state.event_id = result["event_id"]
        state.swap_depth += 1
        state.job_status = "accepted"
        state.job_detail = None
    else:
        state.job_status = result["status"]  # "rejected" or "error"
        state.job_detail = result.get("reason")

    state.job_process = None


def revert(state: HotSwapState) -> None:
    """One call, fully synchronous -- reloads nothing from disk because
    nothing needs to be: the base model is app.state.loaded.model, which
    was never touched by a hot-swap in the first place (see main.py's
    /predict handler). This just stops routing to the swapped-in model."""
    state.active = False
    state.event_id = None
    state.swap_depth = 0
    state.active_model = None
    state.job_id = None
    state.job_process = None
    state.job_status = None
    state.job_detail = None
    state.job_family = None


def kill_running_job(state: HotSwapState) -> bool:
    """Not part of the normal flow -- exists for the mid-run-kill proof
    (and as a real operational escape hatch). Returns True if a process
    was actually killed."""
    if state.job_process is None:
        return False
    state.job_process.kill()
    return True
