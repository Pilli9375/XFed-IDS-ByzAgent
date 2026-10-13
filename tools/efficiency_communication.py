"""Efficiency Part C1/C2 -- bytes per round from the parameter count, cross-
checked against what the harness serializes, and per-round wall time from the
method runs already on disk. Reads checkpoints and logs only; trains nothing.

Run from project root (conda env xfed, which has flwr):
  python tools/efficiency_communication.py
"""
from __future__ import annotations

import pyarrow  # noqa: F401  -- must import before torch in this env

import json
import statistics
from pathlib import Path

import torch
import yaml
from flwr.app import ArrayRecord
from flwr.common.serde import array_record_to_proto

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cfg = yaml.safe_load((ROOT / "configs/efficiency.yaml").read_text())["communication"]
    n_silos = int(yaml.safe_load((ROOT / "configs/data.yaml").read_text())["federation"]["n_silos"])
    directions = int(cfg["directions_per_round"])

    sd = torch.load(ROOT / cfg["checkpoint"], map_location="cpu", weights_only=False)
    n_params = int(sum(v.numel() for v in sd.values()))
    bytes_per_param = 4
    assert all(v.dtype == torch.float32 for v in sd.values())
    model_bytes = n_params * bytes_per_param
    rec = ArrayRecord(sd)
    npy_bytes = int(sum(len(a.data) for a in rec.values()))          # Flower Array payload (.npy blobs)
    proto_bytes = int(array_record_to_proto(rec).ByteSize())          # serialized ArrayRecord protobuf

    analytic = {
        "n_parameters": n_params,
        "bytes_per_parameter_fp32": bytes_per_param,
        "model_bytes": model_bytes,
        "per_round_bytes": model_bytes * n_silos * directions,
        "per_round_bytes_down": model_bytes * n_silos,
        "per_round_bytes_up": model_bytes * n_silos,
        "n_silos": n_silos,
        "directions_per_round": directions,
    }
    serialized = {
        "array_payload_bytes_per_model": npy_bytes,
        "array_payload_overhead_vs_tensor_bytes": npy_bytes - model_bytes,
        "arrayrecord_protobuf_bytes_per_model": proto_bytes,
        "arrayrecord_protobuf_per_round_bytes": proto_bytes * n_silos * directions,
        "note": ("array payload = Flower Array.data (numpy .npy blob incl. header, one per tensor); "
                 "protobuf = flwr.common.serde.array_record_to_proto(...).ByteSize(). Excludes "
                 "Message metadata, metrics/config records, gRPC/TLS framing. The simulation "
                 "runs in one process, so no bytes cross a real network."),
    }

    # Harness-logged bytes and wall time (method path, validation only).
    root = ROOT / cfg["method_runs_root"]
    logged, wall = [], {}
    for group in cfg["wall_time_groups"]:
        for run in sorted((root / group).iterdir()):
            p = run / "round_timing_comm.jsonl"
            if not p.exists() or not (run / "run_summary.json").exists():
                continue
            summary = json.loads((run / "run_summary.json").read_text())
            if int(summary["local_epochs"]) != 3:
                continue
            rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            logged.extend((summary["server"], r["round"], r["bytes_down"], r["bytes_up"]) for r in rows)
            wall[f"{group}/{run.name}"] = {
                "alpha": summary["alpha"], "seed": summary["seed"],
                "per_round_s": [r["wall_time_s"] for r in rows],
            }
    by_server = {}
    for server, rnd, d, u in logged:
        e = by_server.setdefault(server, {"rounds": 0, "bytes_down_round1": set(), "bytes_down_round2plus": set(),
                                           "bytes_up": set()})
        e["rounds"] += 1
        e["bytes_down_round1" if rnd == 1 else "bytes_down_round2plus"].add(d)
        e["bytes_up"].add(u)
    by_server = {k: {kk: sorted(vv) if isinstance(vv, set) else vv for kk, vv in v.items()}
                 for k, v in sorted(by_server.items())}
    want_d, want_u = analytic["per_round_bytes_down"], analytic["per_round_bytes_up"]
    for v in by_server.values():
        v["matches_analytic"] = (v["bytes_down_round1"] == [want_d] and v["bytes_down_round2plus"] == [want_d]
                                 and v["bytes_up"] == [want_u])
    harness = {
        "rounds_checked": len(logged),
        "by_server_strategy": by_server,
        "definition": "federated/xfed_federated/task.py arrayrecord_nbytes: sum of tensor nbytes, no framing",
        "fedadam_note": ("FedAdam's downlink from round 2 on is 2x the fp32 size: flwr 1.33 "
                         "serverapp/strategy/fedadam.py multiplies by eta_norm, a numpy float64 scalar, so the "
                         "new global arrays are float64 (8 B/param). FedYogi multiplies by a Python float and "
                         "stays float32. Uplink is float32 for every strategy. FedAvg (served model) unaffected."),
    }

    all_rounds = [t for w in wall.values() for t in w["per_round_s"]]
    round1 = [w["per_round_s"][0] for w in wall.values()]
    later = [t for w in wall.values() for t in w["per_round_s"][1:]]
    by_alpha = {}
    for w in wall.values():
        by_alpha.setdefault(w["alpha"], []).extend(w["per_round_s"])
    wall_summary = {
        "n_runs": len(wall),
        "n_rounds": len(all_rounds),
        "median_s": statistics.median(all_rounds),
        "min_s": min(all_rounds),
        "max_s": max(all_rounds),
        "round1_median_s": statistics.median(round1),
        "rounds2plus_median_s": statistics.median(later),
        "by_alpha_median_s": {a: statistics.median(v) for a, v in sorted(by_alpha.items())},
        "definition": ("server_app.py _MethodRunLogging: configure_train(r) to end of the server-side "
                       "validation pass for r; 10 simulated clients x 3 local epochs on CPU "
                       "(Flower runtime torch CPU build), one machine"),
        "runs": {k: {"alpha": v["alpha"], "seed": v["seed"],
                     "median_s": statistics.median(v["per_round_s"])} for k, v in wall.items()},
    }

    out = {
        "source": (f"Parameter count from {cfg['checkpoint']}; serialized sizes from flwr ArrayRecord of that "
                   f"checkpoint; logged bytes and wall time from {cfg['method_runs_root']}/"
                   f"{{{','.join(cfg['wall_time_groups'])}}}/*/round_timing_comm.jsonl (3-local-epoch runs). "
                   "Script: tools/efficiency_communication.py. No training, no test rows."),
        "kind": "computed from parameter count + existing run logs",
        "analytic": analytic,
        "serialized": serialized,
        "harness_logged": harness,
        "wall_time_per_round": wall_summary,
    }
    out_path = ROOT / cfg["output"]
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "wall_time_per_round"}, indent=2))
    print({k: v for k, v in wall_summary.items() if k != "runs"})


if __name__ == "__main__":
    main()
