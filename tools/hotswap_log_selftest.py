"""Self-test / proof for src/hotswap/audit_log.py -- Step 1 of hot-swap
retraining (the audit log only, no training).

By default writes to a SCRATCH log file (a throwaway temp path, cleaned
up automatically) -- safe to re-run any time without touching the real
audit trail. Pass --real-log for a one-off end-to-end proof against the
actual state/hotswap_log/events.jsonl: real git dirty-check, real
`git rev-parse HEAD` as code_version, no mocking of anything. That mode
leaves a synthetic record in the real log and deletes it again afterward
(only if the log had zero records before this run -- see --no-cleanup)
since a test record sitting in an append-only audit log is the kind of
thing that gets read later as a real event.

Either way: writes one synthetic event, reads it back, and resolves
every reference the record makes against what's actually on disk right
now -- the source checkpoint, the base partition file, and its hash
against manifest.json's hash_train. No training runs here -- this only
proves that a correctly-formed record's references are real.

Run as:   python -m tools.hotswap_log_selftest
          python -m tools.hotswap_log_selftest --real-log
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.hotswap import audit_log as hs  # noqa: E402


def _synthetic_fields() -> dict:
    """A plausible-shaped hot-swap event. seed/best_round/metric/checkpoint-hash
    are synthetic (no training ran); everything the record REFERENCES
    (source_model_tag/round, base_partition_ref, sample_ids' bounds,
    sample_silo's range) must resolve against real, existing artifacts --
    that's the point of the proof.
    """
    return {
        "seed": 999999,
        "warm_start": True,
        "source_model_tag": "fedavg_a0.5_s42",
        "source_model_round": 18,  # results/inspection/best_rounds_manifest.json: best_round for this tag
        "base_partition_ref": {"alpha": "0.5", "seed": 42},
        "sample_ids": [0, 1, 2, 100, 5000],
        "sample_silo": [0, 0, 1, 2, 3],
        "training_config": {
            "num_rounds": 5,
            "local_epochs": 3,
            "mu": 0.0,
            "fraction_train": 1.0,
            "fraction_evaluate": 1.0,
        },
        "best_round": 3,
        "verify_metric_name": "val_macro_f1_headline",
        "verify_metric_value": 0.9701,
        "resulting_checkpoint_sha256": hashlib.sha256(b"synthetic-hotswap-selftest").hexdigest(),
    }


def _real_git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=hs.PROJECT_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


def run_checks(log_path: Path) -> dict:
    """Runs the full proof against log_path with NO mocking anywhere --
    append_event()'s real git dirty-check and real git_head_sha run as-is.
    Returns the record that was written, for the caller to clean up.
    """
    pre_existing = hs.read_events(validate=True, resolve=False, log_path=log_path) if log_path.exists() else []
    print(f"[0] Target log: {log_path}")
    print(f"    {len(pre_existing)} pre-existing record(s) before this run")

    print("\n[1] Writing synthetic event (real git dirty-check, real HEAD sha -- no mocks)")
    fields = _synthetic_fields()
    record = hs.append_event(fields, log_path=log_path)
    real_head = _real_git_head()
    assert record["code_version"] == real_head, (
        f"record code_version={record['code_version']!r} does not match "
        f"`git rev-parse HEAD`={real_head!r}"
    )
    print(f"    OK  event_id={record['event_id']}")
    print(f"    OK  code_version={record['code_version']} == git rev-parse HEAD")
    print(f"    timestamp={record['timestamp']}")

    print(f"\n[2] Reading back from {log_path} (validate=True)")
    records = hs.read_events(validate=True, resolve=False, log_path=log_path)
    assert len(records) == len(pre_existing) + 1, (
        f"expected {len(pre_existing) + 1} record(s), got {len(records)}"
    )
    readback = records[-1]
    assert readback == record, "record read back does not match the record that was appended"
    print(f"    OK: {len(records)} record(s) total, new record round-trips identically")

    print("[3] Re-resolving the READ-BACK record's references against disk")
    resolved = hs.resolve_event(readback)
    print(json.dumps({k: str(v) for k, v in resolved.items()}, indent=2))

    ckpt = resolved["source_checkpoint_path"]
    assert ckpt.exists(), ckpt
    print(f"    OK  source checkpoint exists: {ckpt}")

    part = resolved["base_partition_train_path"]
    assert part.exists(), part
    assert resolved["base_partition_hash_verified"] is True
    print(f"    OK  base partition file exists and matches manifest.json hash_train: {part}")

    pool = resolved["train_pool_path"]
    assert pool.exists(), pool
    print(f"    OK  train_pool.parquet exists, {resolved['train_pool_n_rows']:,} rows "
          f"(max sample_id {fields['sample_ids'][-1]} is in range)")

    print("[4] Confirming a structurally malformed record is REJECTED, not partially written")
    bad_fields = dict(_synthetic_fields())
    del bad_fields["best_round"]  # simulate a missing required field
    try:
        hs.append_event(bad_fields, log_path=log_path)
        raise AssertionError("append_event() accepted a record missing best_round")
    except hs.HotSwapValidationError as e:
        print(f"    OK  rejected as expected: {e}")

    print("[5] Confirming a record with an UNRESOLVABLE reference is REJECTED too "
          "(well-formed, but points at a checkpoint that doesn't exist)")
    unresolvable_fields = dict(_synthetic_fields())
    unresolvable_fields["source_model_round"] = 9999  # no such checkpoint on disk
    try:
        hs.append_event(unresolvable_fields, log_path=log_path)
        raise AssertionError("append_event() accepted a record with a nonexistent checkpoint")
    except hs.HotSwapResolutionError as e:
        print(f"    OK  rejected as expected: {e}")

    records_after = hs.read_events(validate=True, resolve=False, log_path=log_path)
    assert len(records_after) == len(pre_existing) + 1, (
        f"expected both rejected writes to leave the log untouched "
        f"({len(pre_existing) + 1} record(s)), got {len(records_after)}"
    )
    print(f"    OK  log still has exactly {len(records_after)} record(s) after both rejected writes")

    print("\nAll checks passed. No training was run -- this only proves the log's own "
          "structural and referential guarantees.")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-log", action="store_true",
        help="Target the real state/hotswap_log/events.jsonl instead of a throwaway scratch "
             "file. Requires a clean git tree (the real dirty-check is not mocked). Leaves a "
             "synthetic record that gets deleted afterward unless --no-cleanup is passed.",
    )
    parser.add_argument(
        "--no-cleanup", action="store_true",
        help="With --real-log, leave the synthetic record in the real log instead of deleting "
             "it afterward.",
    )
    args = parser.parse_args()

    if not args.real_log:
        with tempfile.TemporaryDirectory() as tmp:
            run_checks(Path(tmp) / "events.jsonl")
        return

    log_path = hs.LOG_PATH
    pre_existing_count = len(
        hs.read_events(validate=True, resolve=False, log_path=log_path) if log_path.exists() else []
    )
    run_checks(log_path)

    if args.no_cleanup:
        print(f"\n--no-cleanup passed: leaving the synthetic record in {log_path}")
        return

    if pre_existing_count != 0:
        print(
            f"\n[cleanup] SKIPPED: {log_path} had {pre_existing_count} real record(s) before "
            f"this run -- refusing to touch a log that already has real content. Remove the "
            f"synthetic record (last line) by hand."
        )
        return

    print(f"\n[cleanup] {log_path} had 0 records before this run, so this run's synthetic "
          f"record is the only thing in it -- deleting the file so the log starts empty for "
          f"real use.")
    log_path.unlink()
    lock_path = log_path.with_suffix(".lock")
    lock_path.unlink(missing_ok=True)
    if log_path.parent.exists() and not any(log_path.parent.iterdir()):
        log_path.parent.rmdir()
    print(f"    OK  {log_path} removed")


if __name__ == "__main__":
    main()
