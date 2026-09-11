"""Extract best-by-validation round (R*) for all 9 sweep configs.

Reads each config's final_metrics.json (schema confirmed from a real
file, not guessed), builds a summary table, and writes a manifest that
downstream SHAP code will use to know exactly which checkpoint files
to load per config -- no re-deriving this logic in multiple places.

Run from project root: python tools/extract_best_rounds.py
For a non-FedAvg sweep (e.g. FedProx) sharing the same alpha/seed grid
but a different result-dir prefix, pass --tag-prefix and --out so the
FedAvg manifest is never touched:
  python tools/extract_best_rounds.py --tag-prefix fedprox_mu0.0005 \\
      --out results/inspection/best_rounds_manifest_fedprox_mu0.0005.json
"""
import argparse
import json
from pathlib import Path

CONFIGS = [
    ("0.1", 42), ("0.1", 1337), ("0.1", 2024),
    ("0.5", 42), ("0.5", 1337), ("0.5", 2024),
    ("5.0", 42), ("5.0", 1337), ("5.0", 2024),
]

RESULTS_DIR = Path("results/federated")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag-prefix", default="fedavg",
                     help="result-dir tag prefix, e.g. 'fedavg' or 'fedprox_mu0.0005' (default: fedavg)")
    ap.add_argument("--out", type=Path, default=Path("results/inspection/best_rounds_manifest.json"),
                     help="manifest output path (default: results/inspection/best_rounds_manifest.json)")
    args = ap.parse_args()
    out_path = args.out

    manifest = []
    print(f"{'alpha':<6}{'seed':<7}{'R*':<5}{'best_val_F1':<14}{'test_F1(7)':<12}"
          f"{'silo_ckpt_exists':<18}{'global_ckpt_exists'}")
    print("-" * 90)

    all_ok = True
    for alpha, seed in CONFIGS:
        tag = f"{args.tag_prefix}_a{alpha}_s{seed}"
        fm_path = RESULTS_DIR / tag / "final_metrics.json"
        if not fm_path.exists():
            print(f"{alpha:<6}{seed:<7}MISSING final_metrics.json for {tag}")
            all_ok = False
            continue

        fm = json.loads(fm_path.read_text())
        r_star = fm["best_round"]
        best_val = fm["best_val_macro_f1_headline"]
        test_f1 = fm["test"]["macro_f1_headline"]

        global_ckpt = RESULTS_DIR / tag / "round_checkpoints" / f"round_{r_star:03d}.pt"
        # Check all 10 silo checkpoints exist for R*
        silo_ckpts = [RESULTS_DIR / tag / "silo_checkpoints" / f"round_{r_star:03d}_silo_{s}.pt"
                      for s in range(10)]
        silo_ok = all(p.exists() for p in silo_ckpts)
        global_ok = global_ckpt.exists()
        if not (silo_ok and global_ok):
            all_ok = False

        print(f"{alpha:<6}{seed:<7}{r_star:<5}{best_val:<14.4f}{test_f1:<12.4f}"
              f"{str(silo_ok):<18}{global_ok}")

        manifest.append({
            "alpha": alpha,
            "seed": seed,
            "tag": tag,
            "best_round": r_star,
            "best_val_macro_f1_headline": best_val,
            "test_macro_f1_headline": test_f1,
            "global_checkpoint": str(global_ckpt),
            "silo_checkpoints": [str(p) for p in silo_ckpts],
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written: {out_path}")

    if not all_ok:
        print("\nWARNING: some checkpoint files are missing for their R*. "
              "Do not proceed to SHAP until this is resolved.")
        return 1

    print("All 9 configs: R* identified, all silo + global checkpoints confirmed present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
