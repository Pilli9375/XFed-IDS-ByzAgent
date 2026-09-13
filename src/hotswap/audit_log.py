"""Append-only hot-swap retraining audit log.

Step 1 of hot-swap retraining (see PROJECT_INSTRUCTIONS.md): the log only.
No retraining logic, no model swap, no UI reads or writes through this
module -- it exists purely so that, whenever a future hot-swap event
happens, the record it leaves behind is provably sufficient to regenerate
the resulting model from scratch. "Provably" means two things this module
enforces, not just documents:

1. validate_event() rejects a record missing or malforming any field the
   regeneration walkthrough (see the design writeup) actually depends on
   -- a record is written whole or not at all, never partially.
2. resolve_event() confirms the record's references (a source checkpoint,
   a base partition file, its manifest.json hash) point at real things on
   disk *at write time*, so a broken reference is caught immediately
   instead of discovered the day someone tries to regenerate.

Storage: state/hotswap_log/events.jsonl, one JSON object per line,
outside results/ (operational state, not a contribution artifact) and
outside git (see .gitignore -- every hot-swap during a demo would
otherwise be a dirty-tree/commit event). The append-only guarantee is
structural: each call opens in append mode, writes one line, flushes, and
fsyncs -- never a read-modify-rewrite of the whole file. A file lock
guards against two writers interleaving mid-line; the feature this
guards is still single-writer by design (one dashboard-triggered hot-swap
at a time), the lock is a backstop, not a concurrency model.

Two independent audit trails corroborate every record without needing
git history: the record's own timestamp + code_version (rerun that exact
commit) and resulting_checkpoint_sha256 (hash the regenerated checkpoint,
compare).

Place at: src/hotswap/audit_log.py
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PROJECT_ROOT = _PROJECT_ROOT

LOG_PATH = PROJECT_ROOT / "state" / "hotswap_log" / "events.jsonl"
_LOCK_PATH = LOG_PATH.with_suffix(".lock")

TRAIN_POOL_PATH = PROJECT_ROOT / "data" / "processed" / "train_pool.parquet"
PARTITIONS_DIR = PROJECT_ROOT / "data" / "processed" / "partitions"
MANIFEST_PATH = PARTITIONS_DIR / "manifest.json"
FEDERATED_RESULTS_DIR = PROJECT_ROOT / "results" / "federated"

# Scoped, not repo-wide: an unrelated dirty file (a doc edit, a dashboard
# tweak) has no bearing on whether *this* run is reproducible from
# code_version. Widening this list widens what "reproducible" is allowed
# to depend on -- narrow it only if a real dependency lives outside these.
GIT_DIRTY_SCOPE = ["src", "federated", "backend", "configs"]

# Fields the caller supplies -- the reproducibility-relevant facts about
# the hot-swap run itself. append_event() fills in the rest (event_id,
# timestamp, code_version) so a caller can never assert a commit hash or
# time that doesn't match what the writer actually observed.
CALLER_FIELDS = frozenset({
    "seed",
    "warm_start",
    "source_model_tag",
    "source_model_round",
    "base_partition_ref",
    "sample_ids",
    "sample_silo",
    "training_config",
    "best_round",
    "verify_metric_name",
    "verify_metric_value",
    "resulting_checkpoint_sha256",
})

# Populated by append_event() itself, never by the caller.
WRITER_FIELDS = frozenset({"event_id", "timestamp", "code_version"})

ALL_FIELDS = CALLER_FIELDS | WRITER_FIELDS

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GITSHA_RE = re.compile(r"^[0-9a-f]{40}$")


class HotSwapValidationError(ValueError):
    """Raised by validate_event() -- a record is malformed and must not be written."""


class HotSwapResolutionError(RuntimeError):
    """Raised by resolve_event() -- a record's references don't resolve on disk."""


# --------------------------------------------------------------------- #
# Pure structural validation -- no filesystem access. A record can be
# validated identically whether it was just assembled by append_event()
# or read back from an existing log line.
# --------------------------------------------------------------------- #

def validate_event(record: dict) -> None:
    """Raises HotSwapValidationError on the first violation found."""
    if not isinstance(record, dict):
        raise HotSwapValidationError(f"record must be a dict, got {type(record).__name__}")

    keys = set(record)
    missing = ALL_FIELDS - keys
    extra = keys - ALL_FIELDS
    if missing or extra:
        raise HotSwapValidationError(
            f"record has missing fields {sorted(missing)} and/or unknown fields "
            f"{sorted(extra)}. Required fields: {sorted(ALL_FIELDS)}."
        )

    def _require(cond: bool, msg: str) -> None:
        if not cond:
            raise HotSwapValidationError(msg)

    event_id = record["event_id"]
    _require(isinstance(event_id, str), "event_id must be a str")
    try:
        uuid.UUID(event_id, version=4)
    except (ValueError, AttributeError, TypeError) as e:
        raise HotSwapValidationError(f"event_id {event_id!r} is not a valid UUID4: {e}") from e

    timestamp = record["timestamp"]
    _require(isinstance(timestamp, str), "timestamp must be a str")
    try:
        parsed_ts = datetime.fromisoformat(timestamp)
    except ValueError as e:
        raise HotSwapValidationError(f"timestamp {timestamp!r} is not ISO-8601: {e}") from e
    _require(parsed_ts.tzinfo is not None, f"timestamp {timestamp!r} must be timezone-aware (UTC)")

    code_version = record["code_version"]
    _require(isinstance(code_version, str), "code_version must be a str")
    _require(
        bool(_GITSHA_RE.match(code_version)),
        f"code_version {code_version!r} must be a 40-character lowercase hex git SHA",
    )

    seed = record["seed"]
    _require(isinstance(seed, int) and not isinstance(seed, bool), "seed must be an int")

    warm_start = record["warm_start"]
    _require(isinstance(warm_start, bool), "warm_start must be a bool")

    source_model_tag = record["source_model_tag"]
    source_model_round = record["source_model_round"]
    if warm_start:
        _require(
            isinstance(source_model_tag, str) and source_model_tag,
            "warm_start=true requires a non-empty source_model_tag",
        )
        _require(
            isinstance(source_model_round, int) and not isinstance(source_model_round, bool)
            and source_model_round >= 0,
            "warm_start=true requires source_model_round to be a non-negative int",
        )
    else:
        _require(
            source_model_tag is None and source_model_round is None,
            "warm_start=false requires source_model_tag and source_model_round to both be null "
            "(a cold-start run has no functional dependency on a prior checkpoint -- logging one "
            "anyway would imply a dependency that doesn't exist)",
        )

    base_partition_ref = record["base_partition_ref"]
    if base_partition_ref is not None:
        _require(isinstance(base_partition_ref, dict), "base_partition_ref must be a dict or null")
        _require(
            set(base_partition_ref) == {"alpha", "seed"},
            f"base_partition_ref must have exactly keys {{'alpha', 'seed'}}, "
            f"got {sorted(base_partition_ref)}",
        )
        _require(isinstance(base_partition_ref["alpha"], str), "base_partition_ref.alpha must be a str")
        _require(
            isinstance(base_partition_ref["seed"], int)
            and not isinstance(base_partition_ref["seed"], bool),
            "base_partition_ref.seed must be an int",
        )

    sample_ids = record["sample_ids"]
    sample_silo = record["sample_silo"]
    _require(isinstance(sample_ids, list), "sample_ids must be a list")
    _require(isinstance(sample_silo, list), "sample_silo must be a list")
    _require(
        all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in sample_ids),
        "sample_ids must be a list of non-negative ints",
    )
    _require(
        all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in sample_silo),
        "sample_silo must be a list of non-negative ints",
    )
    _require(
        all(sample_ids[i] < sample_ids[i + 1] for i in range(len(sample_ids) - 1)),
        "sample_ids must be sorted strictly increasing (no duplicates) -- it is the canonical "
        "resolved row set, not a log of individual selection events",
    )
    _require(
        len(sample_ids) == len(sample_silo),
        f"sample_ids ({len(sample_ids)}) and sample_silo ({len(sample_silo)}) must be the same "
        f"length -- sample_silo[i] is the silo sample_ids[i] was trained on",
    )
    _require(
        len(sample_ids) > 0 or base_partition_ref is not None,
        "a record with empty sample_ids and null base_partition_ref describes a run with no "
        "training data at all",
    )

    training_config = record["training_config"]
    _require(
        isinstance(training_config, dict) and len(training_config) > 0,
        "training_config must be a non-empty dict",
    )
    try:
        json.dumps(training_config)
    except TypeError as e:
        raise HotSwapValidationError(f"training_config is not JSON-serializable: {e}") from e

    best_round = record["best_round"]
    _require(
        isinstance(best_round, int) and not isinstance(best_round, bool) and best_round >= 0,
        "best_round must be a non-negative int",
    )

    verify_metric_name = record["verify_metric_name"]
    _require(
        isinstance(verify_metric_name, str) and verify_metric_name,
        "verify_metric_name must be a non-empty str",
    )

    verify_metric_value = record["verify_metric_value"]
    _require(
        isinstance(verify_metric_value, (int, float)) and not isinstance(verify_metric_value, bool),
        "verify_metric_value must be a number",
    )
    _require(math.isfinite(float(verify_metric_value)), "verify_metric_value must be finite")

    resulting_checkpoint_sha256 = record["resulting_checkpoint_sha256"]
    _require(
        isinstance(resulting_checkpoint_sha256, str)
        and bool(_SHA256_RE.match(resulting_checkpoint_sha256)),
        f"resulting_checkpoint_sha256 {resulting_checkpoint_sha256!r} must be a 64-character "
        f"lowercase hex sha256 digest",
    )


# --------------------------------------------------------------------- #
# Resolution -- confirms the record's references point at real, matching
# things on disk. Touches the filesystem; kept separate from
# validate_event() so "is this record well-formed" and "do its references
# actually resolve right now" stay independently callable.
# --------------------------------------------------------------------- #

def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise HotSwapResolutionError(f"partition manifest not found: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text())


def resolve_event(record: dict) -> dict:
    """Raises HotSwapResolutionError on the first unresolved reference.

    Returns a dict of what was resolved, for reuse by callers (e.g. a
    verification script) that want the actual paths without re-deriving
    them.
    """
    resolved: dict = {}

    manifest = _load_manifest()
    n_silos = int(manifest["n_silos"])
    bad_silos = sorted({s for s in record["sample_silo"] if not (0 <= s < n_silos)})
    if bad_silos:
        raise HotSwapResolutionError(
            f"sample_silo contains out-of-range silo indices {bad_silos}; "
            f"n_silos={n_silos} per {MANIFEST_PATH}"
        )

    if not TRAIN_POOL_PATH.exists():
        raise HotSwapResolutionError(f"train_pool.parquet not found: {TRAIN_POOL_PATH}")
    resolved["train_pool_path"] = TRAIN_POOL_PATH
    if record["sample_ids"]:
        n_pool = pq.ParquetFile(TRAIN_POOL_PATH).metadata.num_rows
        max_id = record["sample_ids"][-1]  # sorted ascending, validated by validate_event()
        if max_id >= n_pool:
            raise HotSwapResolutionError(
                f"sample_ids contains position {max_id}, but {TRAIN_POOL_PATH} has only "
                f"{n_pool:,} rows"
            )
        resolved["train_pool_n_rows"] = n_pool

    if record["warm_start"]:
        tag = record["source_model_tag"]
        rnd = record["source_model_round"]
        ckpt = FEDERATED_RESULTS_DIR / tag / "round_checkpoints" / f"round_{rnd:03d}.pt"
        if not ckpt.exists():
            raise HotSwapResolutionError(f"source checkpoint does not exist: {ckpt}")
        resolved["source_checkpoint_path"] = ckpt

    base_partition_ref = record["base_partition_ref"]
    if base_partition_ref is not None:
        alpha, seed = base_partition_ref["alpha"], base_partition_ref["seed"]
        tag = f"a{alpha}_s{seed}"
        train_path = PARTITIONS_DIR / f"assign_{tag}_train.parquet"
        if not train_path.exists():
            raise HotSwapResolutionError(f"base partition file does not exist: {train_path}")

        cfg = manifest.get("configs", {}).get(tag)
        if cfg is None:
            raise HotSwapResolutionError(
                f"base_partition_ref resolves to tag={tag!r}, not found in "
                f"{MANIFEST_PATH}'s configs. Known tags: {sorted(manifest.get('configs', {}))}"
            )
        expected_hash = cfg["hash_train"]
        arr = pd.read_parquet(train_path)["silo"].to_numpy()
        actual_hash = hashlib.sha256(arr.tobytes()).hexdigest()
        if actual_hash != expected_hash:
            raise HotSwapResolutionError(
                f"{train_path} does not match {MANIFEST_PATH}: hash_train={expected_hash}, "
                f"recomputed sha256={actual_hash} -- the partition file has drifted since the "
                f"manifest was written"
            )
        resolved["base_partition_train_path"] = train_path
        resolved["base_partition_hash_verified"] = True

    return resolved


# --------------------------------------------------------------------- #
# Git provenance -- computed by the writer, never accepted from the
# caller (a caller-supplied SHA could silently lie about what code ran).
# --------------------------------------------------------------------- #

def _git_head_sha(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _assert_git_clean(cwd: Path, scope: list[str]) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--"] + scope,
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    dirty = result.stdout.strip()
    if dirty:
        raise RuntimeError(
            f"Refusing to log a hot-swap event: {cwd} has uncommitted changes under "
            f"{scope} --\n{dirty}\n"
            f"A hot-swap logged against an uncommitted code state cannot be regenerated from "
            f"its code_version SHA (PROJECT_INSTRUCTIONS.md: 'a hot-swapped model that cannot "
            f"be reproduced from a logged seed is an escalation trigger'). Commit or stash "
            f"first."
        )


# --------------------------------------------------------------------- #
# Single-writer append with a lock as a backstop, not a concurrency model.
# --------------------------------------------------------------------- #

@contextlib.contextmanager
def _file_lock(lock_path: Path, timeout: float = 10.0, poll_interval: float = 0.05):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() - start > timeout:
                raise TimeoutError(
                    f"Could not acquire hot-swap log lock at {lock_path} within {timeout}s -- "
                    f"another writer may be stuck (or a stale lock file was left behind)."
                )
            time.sleep(poll_interval)
    try:
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


def append_event(fields: dict, log_path: Path = LOG_PATH) -> dict:
    """Validates, resolves, and appends one hot-swap event.

    `fields` must contain exactly CALLER_FIELDS -- event_id, timestamp,
    and code_version are computed here, not accepted from the caller.
    Raises (and writes nothing) if the record is malformed, if any
    reference doesn't resolve on disk, or if the repo has uncommitted
    changes under GIT_DIRTY_SCOPE.

    log_path defaults to the real audit log; pass a different path only
    for tests/self-checks so a synthetic event never lands in the real
    trail (append-only means it can't be cleaned up afterwards).
    """
    keys = set(fields)
    missing = CALLER_FIELDS - keys
    extra = keys - CALLER_FIELDS
    if missing or extra:
        raise HotSwapValidationError(
            f"append_event() fields has missing {sorted(missing)} and/or unexpected "
            f"{sorted(extra)}. Caller-supplied fields are exactly: {sorted(CALLER_FIELDS)}."
        )

    _assert_git_clean(PROJECT_ROOT, GIT_DIRTY_SCOPE)
    code_version = _git_head_sha(PROJECT_ROOT)

    record = {
        **fields,
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code_version": code_version,
    }

    validate_event(record)
    resolve_event(record)

    line = json.dumps(record, sort_keys=True)
    lock_path = log_path.with_suffix(".lock")
    with _file_lock(lock_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())

    return record


# --------------------------------------------------------------------- #
# Reader
# --------------------------------------------------------------------- #

def read_events(validate: bool = True, resolve: bool = False, log_path: Path = LOG_PATH) -> list[dict]:
    """Loads every record in the log, in append order.

    validate=True (default) re-runs validate_event() on every line and
    raises with the offending line number on the first failure -- an
    append-only log is only as trustworthy as its weakest historical
    record. resolve=True additionally re-runs resolve_event() on every
    record (slower: reads train_pool.parquet's row count and, for any
    record with a base_partition_ref, hashes a partition file).
    """
    if not log_path.exists():
        return []

    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise HotSwapValidationError(f"{log_path}:{lineno} is not valid JSON: {e}") from e

            if validate:
                try:
                    validate_event(record)
                except HotSwapValidationError as e:
                    raise HotSwapValidationError(f"{log_path}:{lineno}: {e}") from e
            if resolve:
                try:
                    resolve_event(record)
                except HotSwapResolutionError as e:
                    raise HotSwapResolutionError(f"{log_path}:{lineno}: {e}") from e

            records.append(record)

    return records
