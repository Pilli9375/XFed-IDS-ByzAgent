"""Explainer-stochasticity noise floor for tools/parity_monitor.py -- the
VALIDATION step that script's docstring flagged as an unresolved KNOWN GAP,
approved to run 2026-08-24 (representative slice, not the full 9-config
sweep) after the user was asked and picked that option explicitly.

QUESTION THIS ANSWERS: shap.GradientExplainer.shap_values() takes an
optional `rseed` (background choice, interpolation, smoothing) that
parity_monitor.py's underlying SHAP calls never fix -- every call is an
independently-random draw. So re-explaining the SAME already-trained
checkpoint, with the SAME background and SAME eval rows held fixed, and
ONLY the explainer's internal random draw left to vary, tells us how much
apparent "silo deviation" and "fleet parity" would move even if NOTHING
about the model or data changed at all. That is the noise floor
parity_monitor.py's modified-z flags need to be compared against before
"flagged" can be read as "real drift" rather than "this checkpoint's
explanation is just unstable to resample."

REPRESENTATIVE SLICE (not the full sweep -- cost matched to what was
approved): seed=1337, round=5, all three alphas (0.1, 0.5, 5.0), all
size-eligible silos. seed=1337/round=5 is not an arbitrary pick -- it is
the exact (tag, round) where parity_monitor.py's only two flags occurred
(fedavg_a0.1_s1337, round 5, silos 6 and 8), so this is the slice where the
floor actually matters for a real decision. The other two alphas at the
same seed/round are included for contrast, not coverage -- this pass does
NOT establish a floor for other rounds or other seeds; extending it would
need the same reasoning applied there.

METHOD: for each eligible silo, run GradientExplainer TWICE on the exact
same (checkpoint, background, eval rows) -- draw A with rseed=1001, draw B
with rseed=2002 (both fixed and reproducible, unlike parity_monitor.py's
own underlying cached run, which used no rseed at all). Each draw is
vote-aggregated into a top-10 list exactly as parity_monitor.py does
(reuses aggregate_topk_for_silo, jaccard_sets, leave_one_out_consensus,
modified_z_flags from that module -- not reimplemented). Then:
  - jaccard_self_A_B: draw A's top-10 vs draw B's top-10, SAME checkpoint.
    This is the noise floor itself -- 1 minus this is what "deviation"
    would look like from resampling noise alone, for a silo that hasn't
    drifted from anything.
  - fleet_parity / silo_deviation / flagged, computed INDEPENDENTLY from
    draw A's lists and again from draw B's lists, using the identical
    procedure parity_monitor.py uses on its one cached draw. If the same
    silo flags under both A and B, the flag is not an artifact of which
    random draw parity_monitor.py happened to cache. If a silo flips
    flagged/not-flagged between A and B, the original flag is not
    trustworthy at this fidelity.

Background/eval/eligibility construction is reused verbatim from
tools/local_shap_pipeline.py and tools/round_wise_shap.py (same
BACKGROUND_SEED_BASE=777, same EVAL_SEED=12345, same T_SILO/M_FAMILY via
tools/agreement_metrics.py) so draw A and draw B differ ONLY in the
explainer's own internal randomness -- nothing else.

Run from project root: python tools/parity_noise_floor.py
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "tools")
# local_shap_pipeline first -- see round_wise_shap.py's import-order note
# (importing torch ahead of shap crashed 0xC0000005 on this machine).
import local_shap_pipeline as lsp  # noqa: E402
import agreement_metrics as am  # noqa: E402  (build_eligibility / is_family_eligible reused)
import parity_monitor as pm  # noqa: E402  (aggregate_topk_for_silo / jaccard_sets / leave_one_out_consensus / modified_z_flags reused)

torch = lsp.torch
task = lsp.task
np = lsp.np
import pandas as pd

NSAMPLES = 1000  # matches round_wise_shap.py's reduced-fidelity pass, same one parity_monitor.py reads
ROUND = 5
SEED = 1337
ALPHAS = ["0.1", "0.5", "5.0"]
RSEED_A = 1001
RSEED_B = 2002

FEDERATED_ROOT = Path("results/federated")
OUT_CSV = Path("results/inspection/parity_noise_floor.csv")
OUT_META = Path("results/inspection/parity_noise_floor_metadata.json")


def explain_with_rseed(model, background_X: np.ndarray, eval_X_scaled: np.ndarray, rseed: int):
    """Same as local_shap_pipeline.explain_one_model, plus an explicit,
    reproducible rseed -- that script's version leaves rseed unset
    (independently random every call), which is exactly the behavior this
    script needs to characterize, not inherit silently.
    """
    import shap
    background_t = torch.from_numpy(background_X.copy())
    eval_t = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, background_t)
    shap_values = explainer.shap_values(eval_t, nsamples=NSAMPLES, rseed=rseed)
    return np.array(shap_values)


def main() -> int:
    model_cfg = task.load_yaml("configs/model.yaml")
    data_cfg = task.load_yaml("configs/data.yaml")
    class_weights = task.load_global_class_weights(model_cfg)

    n_per_class = max(1, lsp.N_EVAL_ROWS // len(model_cfg["labels"]["headline_classes"]))
    eval_X_raw, eval_y, eval_families, _ = lsp.load_fixed_eval_rows(
        data_cfg, model_cfg, n_per_headline_class=n_per_class
    )

    sizes_long = pd.read_csv(am.SIZES_PATH)
    sizes_long["alpha"] = sizes_long["alpha"].astype(str)
    total_sizes = am.build_eligibility({})

    rows = []
    for alpha in ALPHAS:
        tag = f"fedavg_a{alpha}_s{SEED}"
        print(f"\n{'='*70}\n{tag}  round {ROUND}\n{'='*70}")
        ckpt_dir = FEDERATED_ROOT / tag

        topk_A: dict[int, list[int]] = {}
        topk_B: dict[int, list[int]] = {}

        for silo_id in range(10):
            size_row = total_sizes[(total_sizes.alpha == alpha) &
                                    (total_sizes.seed == SEED) &
                                    (total_sizes.silo == silo_id)]
            if size_row.empty or not bool(size_row["size_eligible"].iloc[0]):
                continue

            splits = task.load_silo_for_client(silo_id, alpha, SEED, data_cfg, model_cfg, class_weights)
            model = task.build_model(model_cfg, seed=SEED, device="cpu")
            state_dict = torch.load(
                ckpt_dir / "silo_checkpoints" / f"round_{ROUND:03d}_silo_{silo_id}.pt", map_location="cpu"
            )
            model.load_state_dict(state_dict)
            model.eval()

            eval_X_scaled = lsp.scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
            bg_idx = lsp.build_stratified_background(
                splits.X_train, splits.y_train, lsp.BACKGROUND_TARGET, lsp.BACKGROUND_SEED_BASE + silo_id + 1
            )
            bg = splits.X_train[bg_idx]

            sv_A = explain_with_rseed(model, bg, eval_X_scaled, RSEED_A)
            sv_B = explain_with_rseed(model, bg, eval_X_scaled, RSEED_B)

            eligible_mask = np.array([
                am.is_family_eligible(sizes_long, alpha, SEED, silo_id, str(eval_families[i]))
                for i in range(len(eval_y))
            ])
            tk_A = pm.aggregate_topk_for_silo(sv_A, eval_y, eligible_mask, pm.K)
            tk_B = pm.aggregate_topk_for_silo(sv_B, eval_y, eligible_mask, pm.K)
            print(f"  silo {silo_id}: draw A/B done "
                  f"(self-Jaccard@10={pm.jaccard_sets(tk_A, tk_B):.3f})" if tk_A and tk_B else
                  f"  silo {silo_id}: no family-eligible eval rows this round")

            if tk_A is not None:
                topk_A[silo_id] = tk_A
            if tk_B is not None:
                topk_B[silo_id] = tk_B

        n_eligible = len(topk_A)
        if n_eligible < 2:
            print(f"  fewer than 2 eligible silos for {tag} -- skipping fleet stats")
            continue

        pairs = list(combinations(topk_A.keys(), 2))
        fleet_parity_A = float(np.nanmean([pm.jaccard_sets(topk_A[a], topk_A[b]) for a, b in pairs]))
        fleet_parity_B = float(np.nanmean([pm.jaccard_sets(topk_B[a], topk_B[b]) for a, b in pairs]))

        deviations_A = {sid: 1.0 - pm.jaccard_sets(tk, pm.leave_one_out_consensus(topk_A, sid, pm.K))
                         for sid, tk in topk_A.items()}
        deviations_B = {sid: 1.0 - pm.jaccard_sets(tk, pm.leave_one_out_consensus(topk_B, sid, pm.K))
                         for sid, tk in topk_B.items()}

        if n_eligible >= pm.MIN_ELIGIBLE_SILOS:
            _, flags_A, _, _ = pm.modified_z_flags(deviations_A)
            _, flags_B, _, _ = pm.modified_z_flags(deviations_B)
        else:
            flags_A = {sid: False for sid in deviations_A}
            flags_B = {sid: False for sid in deviations_B}

        for sid in topk_A:
            rows.append({
                "tag": tag, "alpha": alpha, "seed": SEED, "round": ROUND, "silo_id": sid,
                "jaccard_self_A_B": pm.jaccard_sets(topk_A[sid], topk_B[sid]),
                "fleet_parity_A": fleet_parity_A, "fleet_parity_B": fleet_parity_B,
                "deviation_A": deviations_A[sid], "deviation_B": deviations_B[sid],
                "flagged_A": flags_A[sid], "flagged_B": flags_B[sid],
            })

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nWritten: {OUT_CSV}  ({len(df)} rows)")

    print("\n" + "=" * 70)
    print("EXPLAINER-STOCHASTICITY NOISE FLOOR (jaccard_self_A_B: same checkpoint, "
          "same background/eval, only explainer's internal randomness differs)")
    print("=" * 70)
    print(df.groupby("alpha")["jaccard_self_A_B"].agg(["median", "min", "max"]).to_string())
    print(f"\nOverall median self-Jaccard@10: {df['jaccard_self_A_B'].median():.4f}  "
          f"(noise-floor 'deviation equivalent' = 1 - this = "
          f"{1 - df['jaccard_self_A_B'].median():.4f})")

    print("\nFlag stability (does the same silo flag under both independent draws?):")
    unstable = df[df.flagged_A != df.flagged_B]
    print(f"  {len(unstable)} / {len(df)} silo-rows flip flagged status between draw A and draw B")
    if len(unstable):
        print(unstable[["tag", "silo_id", "flagged_A", "flagged_B", "deviation_A", "deviation_B"]].to_string(index=False))

    both_flagged = df[df.flagged_A & df.flagged_B]
    print(f"\n  {len(both_flagged)} / {len(df)} silo-rows flag under BOTH independent draws:")
    if len(both_flagged):
        print(both_flagged[["tag", "silo_id", "deviation_A", "deviation_B", "jaccard_self_A_B"]].to_string(index=False))

    meta = {
        "generated_by": "tools/parity_noise_floor.py",
        "purpose": "explainer-stochasticity noise floor for tools/parity_monitor.py's KNOWN GAP",
        "slice": {"alphas": ALPHAS, "seed": SEED, "round": ROUND,
                   "note": "seed/round chosen because that is where parity_monitor.py's only "
                            "two flags occurred (fedavg_a0.1_s1337, round 5, silos 6 and 8) -- "
                            "not extended to other rounds/seeds in this pass"},
        "nsamples": NSAMPLES,
        "rseed_draw_A": RSEED_A,
        "rseed_draw_B": RSEED_B,
        "method": "same checkpoint, same background, same eval rows for both draws; only "
                  "GradientExplainer's internal rseed differs -- isolates explainer sampling "
                  "noise from every other source of variation",
        "reused_from_parity_monitor": ["aggregate_topk_for_silo", "jaccard_sets",
                                         "leave_one_out_consensus", "modified_z_flags", "K"],
        "n_rows": len(df),
    }
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(f"\nWritten: {OUT_META}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
