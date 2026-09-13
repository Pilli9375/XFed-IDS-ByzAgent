"""Step 2A end-to-end proof: one real hot-swap event.

Runs src.hotswap.retrain.run_hotswap() against real data, a real (clean)
git HEAD, and real training -- no mocks anywhere. Prints the gate
decision, the written audit record, and confirms:
  - the record's code_version matches `git rev-parse HEAD`
  - resolve_event() (src/hotswap/audit_log.py, Step 1, UNMODIFIED by this
    script) passes on the real record
  - the persisted checkpoint file at
    state/hotswap_log/checkpoints/{sha256}.pt actually hashes to
    resulting_checkpoint_sha256

Writes one real record into the real state/hotswap_log/events.jsonl --
this is not a scratch/throwaway run like tools/hotswap_log_selftest.py.
That's deliberate: this is meant to be the first genuine hot-swap event
this system has ever produced.

Run as:   python -m tools.hotswap_retrain_proof
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch  # noqa: E402

from src.hotswap import audit_log as hs  # noqa: E402
from src.hotswap import retrain  # noqa: E402


def _real_git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=hs.PROJECT_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


def main() -> None:
    head = _real_git_head()
    print(f"[proof] git HEAD: {head}\n")

    print("[proof] Running one real hot-swap: confirmed_family='WebAttack', "
          "source=fedavg_a0.5_s42\n")
    record = retrain.run_hotswap(
        confirmed_family="WebAttack", seed=778899, source_model_tag="fedavg_a0.5_s42",
    )

    print("\n[proof] Written audit record:")
    print(json.dumps({k: v for k, v in record.items() if k != "sample_ids" and k != "sample_silo"},
                      indent=2, sort_keys=True))
    print(f"  sample_ids: {len(record['sample_ids'])} entries, "
          f"[{record['sample_ids'][0]} .. {record['sample_ids'][-1]}]")
    print(f"  sample_silo: {len(set(record['sample_silo']))} distinct silo(s): {set(record['sample_silo'])}")

    assert record["code_version"] == head, f"record code_version {record['code_version']!r} != HEAD {head!r}"
    print(f"\n[proof] OK  code_version matches git rev-parse HEAD")

    print("\n[proof] Reading back from the REAL log and re-validating every record")
    records = hs.read_events(validate=True, resolve=False)
    assert records[-1]["event_id"] == record["event_id"]
    print(f"[proof] OK  {len(records)} record(s) in the real log; the last one matches what was just written")

    print("\n[proof] resolve_event() -- Step 1's function, unmodified -- on the real record")
    resolved = hs.resolve_event(record)
    print(json.dumps({k: str(v) for k, v in resolved.items()}, indent=2))
    print("[proof] OK  resolve_event() passed: source checkpoint, base partition + hash, "
          "train_pool bounds all resolve on disk")

    print("\n[proof] Confirming the persisted checkpoint file matches resulting_checkpoint_sha256")
    ckpt_path = (
        hs.PROJECT_ROOT / "state" / "hotswap_log" / "checkpoints"
        / f"{record['resulting_checkpoint_sha256']}.pt"
    )
    assert ckpt_path.exists(), f"checkpoint file missing: {ckpt_path}"
    state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    recomputed = retrain._state_dict_sha256(state_dict)
    assert recomputed == record["resulting_checkpoint_sha256"], (
        f"recomputed hash {recomputed} != record's resulting_checkpoint_sha256 "
        f"{record['resulting_checkpoint_sha256']}"
    )
    print(f"[proof] OK  {ckpt_path.name} hashes to {recomputed}, matches the record exactly")

    print("\nAll checks passed. One real hot-swap event, end to end, no mocks.")


if __name__ == "__main__":
    main()
