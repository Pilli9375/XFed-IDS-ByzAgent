"""Server-side explanation-parity monitor -- fleet-wide agreement per round,
computed from ONLY the top-k feature-index rankings a silo would send under
locked decision 4 ("Only top-k rankings cross the trust boundary"). No SHAP
values, no raw data, no feature statistics ever enter the parity computation
or get written to disk here -- see "Boundary discipline" below.

--------------------------------------------------------------------------
v2: multi-draw averaged deviation (supersedes the single-cached-draw design)
--------------------------------------------------------------------------
The first version of this script read the SHAP values tools/round_wise_shap.py
had already cached (one draw per checkpoint, unseeded) and was therefore free
to run. tools/parity_noise_floor.py was built as a separate post-hoc check on
that version and found a real design gap, not just a caveat: shap.Gradient
Explainer's `rseed` is never fixed, so the ONE cached draw per (config,
round, silo) is a single random sample of an inherently noisy statistic.
Concretely, on a representative slice (seed=1337, round=5, all 3 alphas):
silo 8 of fedavg_a0.1_s1337 had an IDENTICAL deviation (0.889) across two
independent fresh draws -- it did not move -- yet it was flagged in the
original cached run and NOT flagged in either fresh draw. The cause: the
cached draw happened to produce an unusually tight cluster of tied
deviation values across the fleet (many silos landing on exactly 0.667 from
coarse top-k vote-tie-breaking over only 14 eval rows), which crushed that
round's MAD to 0.042 -- small enough that an ordinary deviation registered
as a >3.5 sigma outlier. Fresh draws had 3x the natural MAD (~0.13), and
the same 0.889 no longer qualified. The threshold math was never wrong;
judging it against a single uncontrolled draw was.

Fix: for every (config, round, silo), run GradientExplainer N_DRAWS times
with distinct fixed rseeds (not once, unseeded) on the exact same
checkpoint/background/eval rows. Each draw is aggregated into its own
top-k list (aggregate_topk_for_silo) and its own leave-one-out deviation
(silo vs consensus of that SAME draw's other eligible silos -- never mixing
feature indices from different draws into one consensus set). The N_DRAWS
per-silo deviations are then averaged BEFORE median/MAD/threshold is
computed. This directly targets the failure mode above: a single draw's
coarse ties can crush MAD; the mean of 2-3 draws does not collapse the same
way, because each draw's ties land differently. fleet_parity is likewise
reported as the mean of each draw's own fleet-wide pairwise Jaccard@10.

This is no longer free -- see "Cost" below.

--------------------------------------------------------------------------
Cost (measured on this machine, 2026-08-24, via tools/parity_noise_floor.py)
--------------------------------------------------------------------------
30 explainer calls (3 configs x 10 silos x 2 draws, round 5 only,
nsamples=1000) took 1747s wall-clock = 29.1s/call. Full scope is 9 configs x
4 rounds x ~9.9 avg eligible silos (356 (config,round,silo) combinations,
per results/inspection/parity_monitor.csv's original row count) x N_DRAWS:

    N_DRAWS=2: 356 x 2 x 29.1s =~ 20,700s =~ 5.75 hours
    N_DRAWS=3: 356 x 3 x 29.1s =~ 31,100s =~ 8.6 hours

Default entry point runs the SAME representative slice used to diagnose the
bug (seed=1337, round=5, all 3 alphas) -- 30-45 calls, ~15-22 min -- not the
full sweep. Pass --all to run every (config, round) combination; confirm
the cost estimate above before doing that.

--------------------------------------------------------------------------
Boundary discipline (why this is not just agreement_metrics.py renamed)
--------------------------------------------------------------------------
agreement_metrics.py compares each silo's FULL signed 82-feature SHAP vector
against the GLOBAL model's, using weighted Kendall's tau -- a statistic that
needs magnitude information for every feature, not just the top-k. That is a
valid *research* measurement (the global model's SHAP values are computed
centrally by the researcher from checkpoints, not received over any client
-> server channel), but it is not a valid template for what a deployed
server-side monitor may compute, because a deployed server never has the
global model's own SHAP values as a privacy-free comparison point, and never
receives more than a top-k index list from any client.

This script simulates that stricter channel:
  1. For each (config, round, silo, draw), the freshly computed SHAP vectors
     are used ONLY to determine, per eval row, which k=10 feature indices
     are largest by |SHAP| at the ground-truth class (same reference-class
     convention as agreement_metrics.py -- see docs/measurement_protocol.md
     Sec 2.2). This step happens "on the client side" in the simulation --
     magnitudes are touched here and nowhere past this point.
  2. Those per-row top-10 index sets are vote-aggregated (see
     aggregate_topk_for_silo()) into ONE ordered top-10 list per
     (silo, round, draw) -- a plausible stand-in for what a real silo would
     report once per round after aggregating its own local eval/background
     samples, not once per external eval row. This list of 10 integers is
     the only artifact the rest of the script touches.
  3. Fleet parity, per-silo deviation, and the drift flag are all computed
     from these index lists using unweighted Jaccard@10 (unordered set
     overlap) -- no magnitude, no rank-weighting, no raw SHAP value is used
     or stored anywhere past step 1.

--------------------------------------------------------------------------
Threshold derivation (data-derived per round, not an arbitrary constant)
--------------------------------------------------------------------------
Per (config, round), each eligible silo's DRAW-AVERAGED deviation is
converted to a modified z-score using the median and MAD of that round's own
averaged-deviation distribution:

    modified_z = 0.6745 * (deviation - median) / MAD

A silo is flagged if modified_z > 3.5 -- the cutoff recommended by
Iglewicz & Hoaglin (1993), "How to Detect and Handle Outliers", ASQC Basic
References in Quality Control Vol. 16. MAD-based (not std-based) because std
is itself inflated by the outliers it's supposed to detect, especially with
a fleet this small (<=10 silos per round). Degenerate case: if MAD == 0 for
a round (every eligible silo has an identical averaged deviation), no silo
is statistically distinguishable and none are flagged -- stated explicitly
in the metadata JSON, not silently swallowed.

Run from project root:
  python tools/parity_monitor.py           # representative slice (default, ~15-22 min)
  python tools/parity_monitor.py --all     # full 9x4 sweep -- see Cost above first
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, "tools")
# local_shap_pipeline first -- see round_wise_shap.py's import-order note
# (importing torch ahead of shap crashed 0xC0000005 on this machine).
import local_shap_pipeline as lsp  # noqa: E402
import agreement_metrics as am  # noqa: E402  (build_eligibility / is_family_eligible reused)

torch = lsp.torch
task = lsp.task
np = lsp.np
import matplotlib.pyplot as plt
import pandas as pd
import shap

ROUNDS_FULL = [5, 10, 15, 20]
ALPHAS_FULL = ["0.1", "0.5", "5.0"]
SEEDS_FULL = [42, 1337, 2024]

# Representative slice: exactly where the single-draw MAD-collapse bug was
# found and diagnosed (see parity_noise_floor.py / module docstring).
SLICE_ALPHAS = ["0.1", "0.5", "5.0"]
SLICE_SEED = 1337
SLICE_ROUNDS = [5]

K = 10  # matches this project's headline Jaccard@10 convention
N_DRAWS = 3  # averaged per silo -- see module docstring for why 1 draw is not enough
RSEEDS = [1001, 2002, 3003][:N_DRAWS]  # fixed, reproducible -- reuses parity_noise_floor.py's 1001/2002
NSAMPLES = 1000  # matches round_wise_shap.py's reduced-fidelity pass

MIN_ELIGIBLE_SILOS = 3  # below this, median/MAD of deviations is not meaningful
MODIFIED_Z_CUTOFF = 3.5  # Iglewicz & Hoaglin (1993) -- see docstring

FEDERATED_ROOT = Path("results/federated")
OUT_CSV = Path("results/inspection/parity_monitor.csv")
OUT_META = Path("results/inspection/parity_monitor_metadata.json")
OUT_FIG = Path("results/figures/parity_monitor.png")


def explain_with_rseed(model, background_X: np.ndarray, eval_X_scaled: np.ndarray, rseed: int):
    """Same computation as local_shap_pipeline.explain_one_model, plus an
    explicit, reproducible rseed -- that script's version leaves rseed
    unset (independently random every call), which is exactly what this
    script's averaging is designed to be robust to, not inherit silently.
    """
    background_t = torch.from_numpy(background_X.copy())
    eval_t = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, background_t)
    shap_values = explainer.shap_values(eval_t, nsamples=NSAMPLES, rseed=rseed)
    return np.array(shap_values)


def aggregate_topk_for_silo(shap_values: np.ndarray, eval_y: np.ndarray,
                             eligible_mask: np.ndarray, k: int) -> list[int] | None:
    """Vote-aggregates per-eval-row top-k index sets (ground-truth class,
    |SHAP|) into ONE ordered top-k list -- the simulated once-per-round
    message a silo sends. Votes = how many eligible eval rows placed a
    feature in their own top-k; ties broken by better (lower) mean rank
    across those appearances, then by feature index for determinism.
    Returns None if no eval row is family-eligible for this silo this round.
    """
    votes: Counter[int] = Counter()
    rank_sum: dict[int, float] = defaultdict(float)

    for idx in range(len(eval_y)):
        if not eligible_mask[idx]:
            continue
        true_class = int(eval_y[idx])
        vec = shap_values[idx, :, true_class]
        order = np.argsort(-np.abs(vec))[:k]
        for rank_pos, feat in enumerate(order):
            feat = int(feat)
            votes[feat] += 1
            rank_sum[feat] += rank_pos

    if not votes:
        return None

    def sort_key(feat: int):
        return (-votes[feat], rank_sum[feat] / votes[feat], feat)

    ranked = sorted(votes.keys(), key=sort_key)
    return ranked[:k]


def jaccard_sets(a: list[int], b: list[int]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return float("nan")
    return len(sa & sb) / len(union)


def leave_one_out_consensus(topk_by_silo: dict[int, list[int]], exclude_silo: int, k: int) -> list[int]:
    """Consensus top-k built from every OTHER eligible silo's list in the
    SAME draw (leave-one-out, so a silo can't trivially agree with itself;
    never mixes feature indices across different draws).
    """
    votes: Counter[int] = Counter()
    for sid, topk in topk_by_silo.items():
        if sid == exclude_silo:
            continue
        for feat in topk:
            votes[feat] += 1
    ranked = sorted(votes.keys(), key=lambda f: (-votes[f], f))
    return ranked[:k]


def modified_z_flags(deviations: dict[int, float]) -> tuple[dict[int, float], dict[int, bool], float, float]:
    vals = np.array(list(deviations.values()))
    median = float(np.median(vals))
    mad = float(np.median(np.abs(vals - median)))

    z_scores, flags = {}, {}
    for sid, dev in deviations.items():
        if mad == 0.0:
            z_scores[sid] = 0.0
            flags[sid] = False  # degenerate fleet: no silo is distinguishable -- see docstring
        else:
            z = 0.6745 * (dev - median) / mad
            z_scores[sid] = float(z)
            flags[sid] = bool(z > MODIFIED_Z_CUTOFF)
    return z_scores, flags, median, mad


def run_config_round(alpha: str, seed: int, round_num: int, model_cfg: dict, data_cfg: dict,
                      class_weights, eval_X_raw, eval_y, eval_families,
                      sizes_long: pd.DataFrame, total_sizes: pd.DataFrame) -> list[dict]:
    tag = f"fedavg_a{alpha}_s{seed}"
    ckpt_dir = FEDERATED_ROOT / tag

    # topk_by_draw[draw_idx] = {silo_id: topk list} -- kept separate per draw
    # so consensus is never built from mixed-draw feature indices.
    topk_by_draw: list[dict[int, list[int]]] = [dict() for _ in range(N_DRAWS)]

    for silo_id in range(10):
        size_row = total_sizes[(total_sizes.alpha == alpha) &
                                (total_sizes.seed == seed) &
                                (total_sizes.silo == silo_id)]
        if size_row.empty or not bool(size_row["size_eligible"].iloc[0]):
            continue

        splits = task.load_silo_for_client(silo_id, alpha, seed, data_cfg, model_cfg, class_weights)
        model = task.build_model(model_cfg, seed=seed, device="cpu")
        state_dict = torch.load(
            ckpt_dir / "silo_checkpoints" / f"round_{round_num:03d}_silo_{silo_id}.pt", map_location="cpu"
        )
        model.load_state_dict(state_dict)
        model.eval()

        eval_X_scaled = lsp.scale_rows(eval_X_raw, splits.scaler_center, splits.scaler_scale)
        bg_idx = lsp.build_stratified_background(
            splits.X_train, splits.y_train, lsp.BACKGROUND_TARGET, lsp.BACKGROUND_SEED_BASE + silo_id + 1
        )
        bg = splits.X_train[bg_idx]

        eligible_mask = np.array([
            am.is_family_eligible(sizes_long, alpha, seed, silo_id, str(eval_families[i]))
            for i in range(len(eval_y))
        ])

        for draw_idx, rseed in enumerate(RSEEDS):
            sv = explain_with_rseed(model, bg, eval_X_scaled, rseed)
            topk = aggregate_topk_for_silo(sv, eval_y, eligible_mask, K)
            if topk is not None:
                topk_by_draw[draw_idx][silo_id] = topk

    n_eligible = len(topk_by_draw[0])
    if n_eligible < 2:
        return []  # no pairs -- fleet_parity undefined

    fleet_parity_per_draw = []
    deviation_per_draw: list[dict[int, float]] = []
    for draw_topk in topk_by_draw:
        pairs = list(combinations(draw_topk.keys(), 2))
        fleet_parity_per_draw.append(float(np.nanmean(
            [jaccard_sets(draw_topk[a], draw_topk[b]) for a, b in pairs]
        )))
        deviations = {}
        for sid, topk in draw_topk.items():
            consensus = leave_one_out_consensus(draw_topk, sid, K)
            deviations[sid] = 1.0 - jaccard_sets(topk, consensus)
        deviation_per_draw.append(deviations)

    fleet_parity = float(np.mean(fleet_parity_per_draw))
    avg_deviation = {
        sid: float(np.mean([deviation_per_draw[d][sid] for d in range(N_DRAWS)]))
        for sid in topk_by_draw[0]
    }

    if n_eligible >= MIN_ELIGIBLE_SILOS:
        _, flags, _, _ = modified_z_flags(avg_deviation)
    else:
        flags = {sid: False for sid in avg_deviation}

    return [{
        "tag": tag, "alpha": alpha, "seed": seed, "round": round_num,
        "fleet_parity": fleet_parity,
        "silo_id": sid,
        "silo_deviation": avg_deviation[sid],
        "flagged": flags[sid],
    } for sid in avg_deviation]


def make_figure(df: pd.DataFrame) -> None:
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    colors = {"0.1": "tab:red", "0.5": "tab:orange", "5.0": "tab:blue"}
    alphas_sorted = sorted(df["alpha"].unique(), key=float)
    rounds_present = sorted(df["round"].unique())

    for alpha in alphas_sorted:
        sub = df[df.alpha == alpha]
        per_tag = sub.groupby(["seed", "round"])["fleet_parity"].first().reset_index()
        agg = per_tag.groupby("round")["fleet_parity"].mean().reindex(rounds_present)
        ax1.plot(rounds_present, agg.values, marker="o", linewidth=2,
                  color=colors.get(alpha, "black"), label=f"alpha={alpha}")
    ax1.set_xlabel("Federated round")
    ax1.set_ylabel(f"Fleet parity (mean of {N_DRAWS}-draw pairwise Jaccard@10, silo-vs-silo)")
    ax1.set_xticks(rounds_present)
    ax1.set_title("Fleet parity vs round\n(top-k rankings only -- see script docstring)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    for alpha in alphas_sorted:
        sub = df[df.alpha == alpha]
        not_flagged = sub[~sub.flagged]
        flagged = sub[sub.flagged]
        ax2.scatter(not_flagged["round"], not_flagged["silo_deviation"],
                    color=colors.get(alpha, "black"), alpha=0.35, s=25,
                    label=f"alpha={alpha}")
        if len(flagged):
            ax2.scatter(flagged["round"], flagged["silo_deviation"],
                        facecolors="none", edgecolors=colors.get(alpha, "black"),
                        s=110, linewidths=2, marker="o")
    ax2.set_xlabel("Federated round")
    ax2.set_ylabel(f"Silo deviation from leave-one-out consensus ({N_DRAWS}-draw average)")
    ax2.set_xticks(rounds_present)
    ax2.set_title("Per-silo deviation vs round\n(open circles = flagged, modified z > 3.5)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f"Server-side explanation-parity monitor ({N_DRAWS}-draw averaged, top-k rankings only)",
                 fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=200, bbox_inches="tight")
    print(f"Saved: {OUT_FIG}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                     help="run the full 9-config x 4-round sweep (see Cost in script docstring first)")
    args = ap.parse_args()

    if args.all:
        configs = [(a, s) for a in ALPHAS_FULL for s in SEEDS_FULL]
        rounds = ROUNDS_FULL
        scope_note = "full sweep (--all)"
    else:
        configs = [(a, SLICE_SEED) for a in SLICE_ALPHAS]
        rounds = SLICE_ROUNDS
        scope_note = "representative slice (default -- pass --all for full sweep)"

    print(f"Scope: {scope_note}")
    print(f"N_DRAWS={N_DRAWS}, rseeds={RSEEDS}, nsamples={NSAMPLES}")
    print(f"{len(configs)} configs x {len(rounds)} rounds x up to 10 silos x {N_DRAWS} draws")

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
    t0 = time.time()
    for alpha, seed in configs:
        for round_num in rounds:
            print(f"  fedavg_a{alpha}_s{seed} round {round_num} ...", flush=True)
            rows.extend(run_config_round(alpha, seed, round_num, model_cfg, data_cfg, class_weights,
                                          eval_X_raw, eval_y, eval_families, sizes_long, total_sizes))
    elapsed_min = (time.time() - t0) / 60
    print(f"\nElapsed: {elapsed_min:.1f} min")

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"Written: {OUT_CSV}  ({len(df)} rows)")

    n_flagged = int(df["flagged"].sum())
    print(f"\n{n_flagged} / {len(df)} (config, round, silo) rows flagged "
          f"(modified z > {MODIFIED_Z_CUTOFF}, deviation averaged over {N_DRAWS} independent draws).")

    meta = {
        "generated_by": "tools/parity_monitor.py (v2: multi-draw averaged, see module docstring)",
        "scope": scope_note,
        "k": K,
        "n_draws": N_DRAWS,
        "rseeds": RSEEDS,
        "nsamples": NSAMPLES,
        "configs_run": [f"a{a}_s{s}" for a, s in configs],
        "rounds_run": rounds,
        "n_eval_rows": 14,
        "eligibility_filters": {"T_SILO": am.T_SILO, "M_FAMILY": am.M_FAMILY},
        "boundary_discipline": "only top-k (k=10) feature-index lists are used past the per-row "
                                "aggregation step -- no SHAP magnitude, no raw data, no feature "
                                "statistics enter the parity/deviation computation or this CSV",
        "silo_deviation": f"mean over {N_DRAWS} independent GradientExplainer draws of "
                          "[1 - Jaccard@10(silo top-10, leave-one-out consensus of other eligible "
                          "silos IN THE SAME DRAW)] -- consensus never mixes feature indices across draws",
        "threshold_method": "modified z-score (median/MAD) on the draw-averaged deviation, per "
                             f"(tag, round), flagged if z > {MODIFIED_Z_CUTOFF} (Iglewicz & Hoaglin 1993)",
        "why_averaged": "single-draw version flagged 2 silos (fedavg_a0.1_s1337 round 5) that did not "
                        "reproduce under independent re-explanation -- traced to single-draw MAD "
                        "collapse from coarse top-k vote ties; see tools/parity_noise_floor.py and "
                        "module docstring 'v2' section",
        "elapsed_minutes": round(elapsed_min, 1),
        "n_rows": len(df),
    }
    OUT_META.write_text(json.dumps(meta, indent=2))
    print(f"Written: {OUT_META}")

    if len(df):
        make_figure(df)

        print("\nMean fleet parity by (alpha, round):")
        per_tag = df.groupby(["alpha", "seed", "round"])["fleet_parity"].first().reset_index()
        print(per_tag.groupby(["alpha", "round"])["fleet_parity"].mean().to_string())

        if n_flagged:
            print("\nFlagged rows:")
            print(df[df.flagged][["tag", "round", "silo_id", "silo_deviation"]].to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
