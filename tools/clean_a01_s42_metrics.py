"""Clean up stale silo_metrics.jsonl contamination in fedavg_a0.1_s42.

The 2-round smoke test that ran before the real 20-round sweep wrote 40
lines (round 1-2 x 10 silos x 2 phases) into the same append-only file.
The real 20-round sweep then appended its own 400 lines on top, giving
440 total. Checkpoints were unaffected (fixed filenames, overwritten
cleanly) -- only this JSONL log accumulated the stale rows.

This takes the LAST 400 lines (written after the contamination, by the
real sweep), verifies they cover exactly round 1-20 x silo 0-9 x
phase(train,evaluate) with no duplicates or gaps -- not just assumes it --
backs up the original file, then overwrites it with the clean 400 lines.

Run from project root: python tools/clean_a01_s42_metrics.py
"""
import json
import shutil
from pathlib import Path

TARGET = Path("results/federated/fedavg_a0.1_s42/silo_metrics.jsonl")
BACKUP = TARGET.with_suffix(".jsonl.contaminated_backup")


def main() -> int:
    if not TARGET.exists():
        print(f"NOT FOUND: {TARGET.resolve()}")
        return 1

    lines = TARGET.read_text().splitlines()
    print(f"Total lines found: {len(lines)}")
    if len(lines) != 440:
        print("Expected exactly 440 lines given the known contamination "
              "pattern. Stopping -- do not proceed on an assumption that "
              "doesn't match reality.")
        return 1

    clean_lines = lines[-400:]

    expected = {(r, s, p) for r in range(1, 21) for s in range(10)
                for p in ("train", "evaluate")}
    seen = set()
    for line in clean_lines:
        row = json.loads(line)
        seen.add((row["round"], row["silo_id"], row["phase"]))

    if seen != expected:
        missing = expected - seen
        extra = seen - expected
        print("MISMATCH -- the last 400 lines do not cleanly cover the "
              "expected grid. Stopping, NOT overwriting.")
        print(f"  missing (first 10): {sorted(missing)[:10]}")
        print(f"  extra   (first 10): {sorted(extra)[:10]}")
        return 1

    print("Verified: last 400 lines cover exactly round 1-20 x silo 0-9 x "
          "phase(train,evaluate) -- no duplicates, no gaps.")

    shutil.copy(TARGET, BACKUP)
    TARGET.write_text("\n".join(clean_lines) + "\n")
    print(f"Backup of full 440-line file: {BACKUP}")
    print(f"Clean 400-line file written: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
