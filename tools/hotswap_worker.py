"""Subprocess worker for one hot-swap attempt -- Step 2B.

Runs OUTSIDE the FastAPI process, always. backend/hotswap_service.py
spawns this via subprocess.Popen and never imports src.hotswap.retrain
in-process -- see that module's own docstring for why: Step 2A's proof
run segfaulted (intermittently, root cause not chased -- see that
session's findings) when heavy pyarrow/parquet reads immediately followed
torch training in the same process. A crash HERE just ends this process;
backend/hotswap_service.py's poll() sees the exit and marks the job
"crashed" without touching the served model.

Contract with the backend: ALWAYS write a JSON result file to
state/hotswap_log/jobs/{job_id}.json before this process exits normally
-- accepted, rejected, or an ordinary exception all count as "finished,"
and the backend tells them apart from a real crash (segfault, SIGKILL)
by whether that file exists at all once the process has exited.

Run as:
  python -m tools.hotswap_worker --family WebAttack --seed 12345 \\
      --source-tag fedavg_a0.5_s42 --job-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.hotswap import audit_log as hs  # noqa: E402
from src.hotswap.retrain import HotSwapGateRejected, run_hotswap  # noqa: E402

JOBS_DIR = hs.LOG_PATH.parent / "jobs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--source-tag", required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()

    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = JOBS_DIR / f"{args.job_id}.json"

    try:
        record = run_hotswap(
            confirmed_family=args.family, seed=args.seed, source_model_tag=args.source_tag,
        )
        result_path.write_text(json.dumps({
            "status": "accepted",
            "event_id": record["event_id"],
            "resulting_checkpoint_sha256": record["resulting_checkpoint_sha256"],
            "verify_metric_name": record["verify_metric_name"],
            "verify_metric_value": record["verify_metric_value"],
        }))
    except HotSwapGateRejected as e:
        result_path.write_text(json.dumps({"status": "rejected", "reason": str(e)}))
    except Exception as e:  # noqa: BLE001 -- deliberately broad: any failure still gets a result file
        result_path.write_text(json.dumps({
            "status": "error",
            "reason": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }))
        raise  # non-zero exit code; the result file above is what the backend actually reads


if __name__ == "__main__":
    main()
