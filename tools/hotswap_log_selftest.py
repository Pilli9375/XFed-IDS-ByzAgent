"""Self-test / proof for src/hotswap/audit_log.py -- Step 1 of hot-swap
retraining (the audit log only, no training).

Writes one synthetic hot-swap event to a SCRATCH log file (never the real
state/hotswap_log/events.jsonl -- append-only means a synthetic record
could never be cleaned back out of the real trail), reads it back, and
resolves every reference the record makes against what's actually on
disk right now: the source checkpoint, the base partition file, and its
hash against manifest.json's hash_train. No training runs here -- this
only proves that a correctly-formed record's references are real.

Run as:   python -m tools.hotswap_log_selftest
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

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


def _check_real_dirty_tree_is_enforced(scratch_log: Path) -> None:
    """This repo currently has real uncommitted changes under src/ (Step 1's
    own new files, not yet committed) -- so the UNPATCHED writer must refuse
    to log against them. Proves the dirty-check fires for real, not just in
    theory, before we patch it out below to reach the happy path."""
    print("[0] Confirming the real (unpatched) dirty-tree check refuses to write")
    try:
        hs.append_event(_synthetic_fields(), log_path=scratch_log)
        raise AssertionError(
            "append_event() succeeded against the real repo state -- expected it to refuse "
            "given this repo's current uncommitted changes under src/. If src/hotswap/ has "
            "since been committed, this check is stale and can be removed."
        )
    except RuntimeError as e:
        print(f"    OK  refused as expected: {e}".splitlines()[0] + " ...")
    assert not scratch_log.exists() or scratch_log.read_text() == "", (
        "the refused write must leave no trace in the log"
    )
    print("    OK  scratch log has no trace of the refused write")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        scratch_log = Path(tmp) / "events.jsonl"

        _check_real_dirty_tree_is_enforced(scratch_log)

        # From here on: this test-only patch simulates "HEAD is clean" so the
        # append/resolve happy path can be proven without committing anything
        # on my own initiative. Nothing in src/hotswap/audit_log.py itself is
        # changed or bypassed -- the real module still refuses on a dirty
        # tree, as [0] just showed for real.
        print("\n[patch] Simulating a clean tree + fixed HEAD sha for the happy-path proof below "
              "(test-only; the real dirty-check was already proven above)")
        fake_sha = "a" * 40

        with mock.patch.object(hs, "_assert_git_clean", lambda cwd, scope: None), \
             mock.patch.object(hs, "_git_head_sha", lambda cwd: fake_sha):

            print(f"\n[1] Writing synthetic event to scratch log: {scratch_log}")
            fields = _synthetic_fields()
            record = hs.append_event(fields, log_path=scratch_log)
            print(f"    OK: event_id={record['event_id']} code_version={record['code_version']}")
            print(f"    timestamp={record['timestamp']}")

        print(f"[2] Reading back from {scratch_log} (validate=True)")
        records = hs.read_events(validate=True, resolve=False, log_path=scratch_log)
        assert len(records) == 1, f"expected 1 record, got {len(records)}"
        readback = records[0]
        assert readback == record, "record read back does not match the record that was appended"
        print(f"    OK: {len(records)} record(s), round-trips identically to what was written")

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
            hs.append_event(bad_fields, log_path=scratch_log)
            raise AssertionError("append_event() accepted a record missing best_round")
        except hs.HotSwapValidationError as e:
            print(f"    OK  rejected as expected: {e}")

        print("[5] Confirming a record with an UNRESOLVABLE reference is REJECTED too "
              "(well-formed, but points at a checkpoint that doesn't exist)")
        unresolvable_fields = dict(_synthetic_fields())
        unresolvable_fields["source_model_round"] = 9999  # no such checkpoint on disk
        with mock.patch.object(hs, "_assert_git_clean", lambda cwd, scope: None), \
             mock.patch.object(hs, "_git_head_sha", lambda cwd: fake_sha):
            try:
                hs.append_event(unresolvable_fields, log_path=scratch_log)
                raise AssertionError("append_event() accepted a record with a nonexistent checkpoint")
            except hs.HotSwapResolutionError as e:
                print(f"    OK  rejected as expected: {e}")

        # Both rejections above must leave the log exactly as it was after [1]:
        # one good record, nothing partial.
        records_after = hs.read_events(validate=True, resolve=False, log_path=scratch_log)
        assert len(records_after) == 1, (
            f"expected both rejected writes to leave the log untouched (1 record), "
            f"got {len(records_after)}"
        )
        print(f"    OK  scratch log still has exactly 1 record after both rejected writes")

        print("\nAll checks passed. No training was run -- this only proves the log's own "
              "structural and referential guarantees.")


if __name__ == "__main__":
    main()
