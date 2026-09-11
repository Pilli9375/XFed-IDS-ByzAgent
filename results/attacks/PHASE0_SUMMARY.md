# ByzAgent Phase 0 — Label-Flip Attack — Summary

**Verdict: PASS.** Closed 2026-08-26, signed off by `01_Planning`. Two
close-out items executed after sign-off (f=2 secondary condition run;
dual-statistic reporting locked into ground truth) — see final sections
below. Phase 1 (per-client behavioral stats), Phase 2 (Krum/trimmed-mean),
Phase 3 (LLM agent), Phase 4 (rolling history), Phase 5 (eval harness) are
NOT started.

## Locked attack configuration

| parameter | value |
|---|---|
| alpha (partition) | 0.5 |
| partition seed | 42 |
| f (malicious silos) | 3 |
| malicious silos | **{0, 3, 5}** |
| mode | sudden |
| flip_fraction | 0.40 |
| strategy | targeted_to_benign (target_class: Benign) |
| attack_seed | 9001 |
| n_silos | 10 |

Source: `configs/attack.yaml`. Resolved list is written into every run's
`results/attacks/{tag}/attack_config.json`, not re-derived at call time.

## Adversary framing — verbatim, mandatory in every downstream reference

> Worst-case/upper-bound adversary with full knowledge of federation
> composition. Selected by enumerating all C(10,3)=120 malicious-silo triples
> at alpha=0.5 seed=42 against the global per-silo family composition and
> maximizing the minimum per-family coverage across the 6 non-Benign headline
> families at flip_fraction=1.0 (achieved: 38.60% min, on DoS). NOT a
> realistic or naturalistic attacker -- no real attacker has this global
> view. Retired rule: size-representative-by-total-training-rows (silos
> [0,1,9]), which achieved only 13.98% federation-wide attack-row coverage
> because it sized against a denominator the targeted flip does not modify
> (Benign rows).

**{0,3,5} must never be presented as a realistic attack scenario.** It is
the strongest feasible silo-level attacker under this threat model, used to
establish an upper bound: if rolling-history detection (Phase 4) cannot
catch this, it cannot catch a weaker, more realistic one.

## Measured per-family attack-row coverage vs. frontier prediction

Frontier ceiling (flip_fraction=1.0) scaled to the actual flip_fraction=0.4,
compared against the coverage actually measured from `flip_log.csv` (round 1
replay of the deterministic RNG selection):

| family | predicted (ceiling × 0.4) | measured |
|---|---|---|
| Bot | 23.02% | 22.68% |
| BruteForce | 16.83% | 18.21% |
| DDoS | 20.73% | 20.48% |
| DoS | 15.44% | 15.44% |
| PortScan | 17.87% | 17.97% |
| WebAttack | 19.68% | 18.44% |

Matches within ~1-2pp on every family — confirms the flip mechanic scales
linearly with `flip_fraction` as designed, no discrepancy found.

For comparison, the retired rule ({0,1,9}) achieved only 13.98% coverage
overall, unevenly distributed (2.17%–24.33%, three of six families under
5%). Full detail: `results/inspection/attack_row_flip_diagnostic_a0.5_s42_f3_sudden.csv`.

## Gate result — all four statistics, paired same-seed vs. clean_s42

**Report all four every time. Never report final-5 alone** — that is what
prevents this from reading as post-hoc selection of a flattering statistic.

| statistic | clean_s42 | poisoned {0,1,9} | Δ | poisoned {0,3,5} | Δ |
|---|---|---|---|---|---|
| mean (all 20 rounds) | 0.8535 | 0.8180 | **−0.0355** | 0.8236 | **−0.0299** |
| median (all 20 rounds) | 0.8487 | 0.8436 | **−0.0051** | 0.8438 | **−0.0048** |
| **final-5 mean (rounds 16-20)** | **0.9513** | **0.9143** | **−0.0370** | **0.8746** | **−0.0766** |
| max (best-by-validation — MODEL SELECTION statistic, unchanged) | 0.9760 | 0.9710 | −0.0049 | 0.9763 | +0.0004 |

Full round-by-round series for both runs plus 3 clean seeds:
`results/inspection/round_history_comparison_a0.5_s42.json`.

## Verdict reasoning

The gate question is "is the attack strong enough to be worth detecting."
**Yes.** Mean drops ~3pp, final-5 mean drops 3.7–7.7pp, in both independently
selected malicious-silo triples, always in the same (negative) direction.
Dose response is in the correct direction: {0,3,5}'s broader, more even
attack-row coverage produces the *larger* final-5 drop (−0.0766 vs. {0,1,9}'s
−0.0370), which the max statistic completely missed.

The two earlier FAIL verdicts (against the max/best-by-validation statistic)
were a **measurement failure, not an attack failure**. Max is a maximum over
a noisy ~20-round series (std 0.064–0.117 across all 5 runs on file) and is
close to blind to a uniform-ish level shift — exactly what a constant
`sudden`-mode attack produces. It was the wrong instrument for detecting
this attack's effect, though it remains the correct instrument for its own
purpose (see below).

## Evaluation-statistic decision — two different questions, do not conflate

- **Model selection** (which checkpoint is deployed) stays **best-by-validation
  MAX. Locked. Unchanged.** Every Contribution A number (`results/aggregated/`,
  `round_lottery.csv`) keeps its existing meaning. Nothing has been re-scored.
- **Attack-effect reporting** uses **final-5-round mean** of
  `val_macro_f1_headline`, paired same-seed, as the primary level statistic —
  reported alongside mean/median/max, never alone. Rationale: final-5 measures
  converged behavior (what a deployed system actually experiences), while
  max is provably insensitive to level shifts and mean-over-all-rounds
  dilutes the signal with early-round convergence noise where the model
  isn't trained yet.

If any future reference conflates "the gate statistic changed" with "model
selection changed," that is an error.

## Quantization caveat — standing rule from this phase forward

Any headline family with validation support under ~500 gets its sample
count printed alongside any recall delta, before the delta is discussed as
signal.

| family | validation support | 1 sample = Δrecall |
|---|---|---|
| Benign | 108,067 | 0.00001 |
| Bot | **353** | **0.0028** |
| BruteForce | 523 | 0.0019 |
| DDoS | 7,136 | 0.0001 |
| DoS | 13,312 | 0.0001 |
| PortScan | 13,962 | 0.0001 |
| WebAttack | **154** | **0.0065** |

**Retracted finding:** per-family recall deltas on Bot (−0.0453 / +0.0141,
sign-flipped across the two triples) and WebAttack (−0.0260 / −0.0259,
literally the same 4 misclassified validation samples both times, despite
4.5x different attack-row coverage on WebAttack) were read as "damaged
families" in an earlier turn of this investigation. That reading is wrong
and is retracted. With supports of 353 and 154, these deltas are near-quantized
and do not carry dose-response information — they must never be read as
signal without the sample-count column above. The PASS verdict in this
document rests entirely on the headline-metric statistics (mean/median/final-5/max),
not on per-family recall.

## Known limitation — logged as a Phase 5 obligation, not fixed now

The dose-response finding rests on **one paired seed (42)**. The clean-seed
spread on the mean-across-rounds statistic (0.834–0.923 across seeds
42/1337/2024) is comparable in magnitude to the observed attack effect
(~0.03–0.036 on the same statistic). The paired same-seed design controls
for this, and the cross-triple corroboration (two independently-selected
malicious-silo sets, consistent direction, correct dose-response ordering)
is real evidence — but n=1 seed is not defensible as a headline result.

**Obligation for Phase 5:** run seeds 1337 and 2024 at the locked attack
config ({0,3,5}, f=3, sudden, flip_fraction=0.4) before any final write-up.
Not done now, per explicit instruction.

## Post-sign-off close-out item 1 — f=2 secondary condition

Pre-registered spec, locked before running: `malicious_silos=[0,3]` (best
worst-case pair from the f=2 frontier, ceiling 16.73% min per-family
coverage at flip_fraction=1.0, same worst-case/full-knowledge-adversary
framing and `selection_note` convention as {0,3,5}), `flip_fraction=0.4`,
`mode=sudden`, `attack_seed=9001`, `alpha=0.5`, `seed=42` — paired-comparable
with both f=3 runs. Same harness, same hard test-guard, same collision-safe
tagging; no new code, config change only.

**All four statistics, paired same-seed vs. clean_s42:**

| statistic | clean_s42 | f=3 {0,1,9} | Δ | f=3 {0,3,5} | Δ | f=2 {0,3} | Δ |
|---|---|---|---|---|---|---|---|
| mean | 0.8535 | 0.8180 | −0.0355 | 0.8236 | −0.0299 | 0.8253 | −0.0282 |
| median | 0.8487 | 0.8436 | −0.0051 | 0.8438 | −0.0048 | 0.8489 | **+0.0003** |
| final-5 mean | 0.9513 | 0.9143 | −0.0370 | 0.8746 | −0.0766 | 0.8787 | **−0.0726** |
| max | 0.9760 | 0.9710 | −0.0049 | 0.9763 | +0.0004 | 0.9867 | +0.0107 |

**Measured attack-row coverage vs. frontier prediction** (round-1 replay;
predicted = ceiling × 0.4):

| family | measured | predicted |
|---|---|---|
| Bot | 6.30% | 6.69% |
| BruteForce | 14.43% | 13.41% |
| DDoS | 11.17% | 11.34% |
| DoS | 14.26% | 14.27% |
| PortScan | 17.61% | 17.54% |
| WebAttack | 15.35% | 16.34% |

Matches within ~1pp on every family, as with both f=3 runs — no discrepancy.
Coverage is meaningfully lower than {0,3,5} throughout (especially Bot,
6.30% vs. 22.68%), consistent with f=2's lower ceiling.

**Pre-registered interpretation, applied as locked (not chosen after seeing
the result):** the criterion was "a detectable final-5-mean signal
comparable to the f=3 runs." f=2's final-5-mean delta (−0.0726) is
comparable in magnitude to {0,3,5}'s (−0.0766) and larger than {0,1,9}'s
(−0.0370), despite f=2 having a much lower coverage ceiling (16.73% vs.
38.60%) and only two malicious silos. **By this criterion: f=2 becomes the
PRIMARY Krum-margin-clean evidence for Phase 4; f=3 becomes
secondary/confirmatory.**

**Full transparency per the "always report all four" rule — this is not
unanimous:** median shows essentially no effect for f=2 (+0.0003, versus
consistent ≈−0.005 for both f=3 runs), and max again shows nothing (as
expected). Two of four statistics (mean, final-5-mean) support the
pre-registered promotion criterion; one (median) does not corroborate; one
(max) is expected to show nothing regardless of attack strength. This
divergence itself should travel with the promotion decision, not be
smoothed over.

**Sample-count-gated per-family check** (best round 16; clean values from
`results/inspection/retro_replay_val_metrics_a0.5_s42.json`, clean run's own
best round 18):

| family | val support | clean recall | f=2 recall | Δ | ≈ samples |
|---|---|---|---|---|---|
| Benign | 108,067 | 0.9993 | 0.9993 | 0.0000 | 2.0 |
| Bot | **353** | 0.7904 | 0.9348 | **+0.1445** | **+51.0** |
| BruteForce | 523 | 0.9847 | 0.9847 | 0.0000 | 0.0 |
| DDoS | 7,136 | 1.0000 | 1.0000 | 0.0000 | 0.0 |
| DoS | 13,312 | 0.9997 | 0.9996 | −0.0001 | −1.0 |
| PortScan | 13,962 | 0.9972 | 0.9966 | −0.0006 | −8.0 |
| WebAttack | **154** | 0.9545 | 0.9286 | −0.0260 | **−4.0** |

Per the standing rule, Bot (353) and WebAttack (154) carry their
sample-count column and are not read as signal on their own. Notable: this
is the **third** independent run (after both f=3 triples) in which
WebAttack's delta resolves to exactly **−4 validation samples** — strong
further evidence this is a fixed artifact of this seed/model/round-selection
combination, not a dose-responsive attack effect. Bot's +51-sample swing is
larger than anything seen in the f=3 runs (±5 to ±16 samples) but still
carries the sub-500-support caveat and is not treated as corroborating or
contradicting the headline-metric result.

**Post-close-out verification (identity check, not just count):** diffed the
actual predicted labels for all 154 WebAttack validation examples across all
four runs. All three independently-configured poisoned runs ({0,1,9},
{0,3,5}, {0,3} — different silos, different f, different measured coverage)
misclassify the **exact same 11 examples** (row indices 89603, 95295, 95713,
96806, 99324, 99738, 100658, 106275, 110432, 111163, 111895) — the same 7
that clean_s42 already gets wrong, plus the identical additional 4 (96806,
99738, 110432, 111163) in every poisoned run. This is a fixed model
characteristic — a small set of WebAttack examples sitting exactly at this
architecture's decision boundary, which essentially any perturbation to
training pushes across — not evidence of non-independent runs, shared
eval-time randomness, or a stale-prediction artifact (a caching bug would
not produce this clean "same 7 baseline errors, same 4 additional errors"
superset structure across three differently-configured, independently
trained models). Confirms Diagnostic 1's conclusion from the other
direction: this is definitively noise/boundary behavior, not signal.
Full row-level diff: `results/inspection/webattack_prediction_diff.json`.

Benign false-negative rate: clean 0.361% vs. f=2 0.251% (lower, not higher —
consistent with Bot/WebAttack noise dominating this particular statistic
rather than a clean monotonic attack signature).

Artifacts: `results/attacks/a0.5_s42_f2_sudden_silos0-3/`,
`results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3/`.

## Post-sign-off close-out item 2 — dual-statistic reporting, locked ground truth

Effective from this point through Phase 5, carried into any future phase's
opening ground truth:

- **Model selection remains best-by-validation MAX. Locked. Unchanged.**
  This requirement does not touch which checkpoint deploys, in this phase or
  any future one.
- Every future attack-vs-clean comparison (Phase 4's rolling-history result,
  Phase 5's eval harness) **must report both (a) best-by-validation MAX and
  (b) final-5-round MEAN, side by side** — not one or the other. In
  practice this means continuing to report all four (mean/median/final-5/max)
  as already established.
- **If MAX and final-5-mean diverge under attack, that divergence is itself
  a standalone methodological finding** about best-by-validation as a
  reporting convention under Byzantine conditions — reportable independent
  of whether ByzAgent beats Krum, never buried as a footnote inside another
  table.
- If a future session's ground truth does not carry this requirement
  forward, that is a gap to flag back to `01_Planning`, not to silently
  work around by reporting only one statistic.

## Final repo-state confirmation

- `configs/attack.yaml`: `attack.enabled: false`, resting state = LOCKED
  PRIMARY (`f=3`, `malicious_silos=[0,3,5]`) — reverted back to this after
  the f=2 run completed; f=2's own config is preserved unchanged in that
  run's `attack_config.json`, not lost by the revert.
- Hard test-guard intact in `federated/xfed_federated/server_app.py`
  (`raise RuntimeError("HARD STOP: ...")`, unconditional when
  `attack.enabled: true`, fires before any `test_global.parquet` computation).
  Verified present and fired correctly on all three poisoned runs (f=3
  {0,1,9}, f=3 {0,3,5}, f=2 {0,3}).
- All three poisoned run directories preserved under distinct,
  collision-proof tags — none overwrote another or the clean baselines:
  - `results/federated/fedavg_a0.5_s42_poisoned_f3_sudden/` (retired rule, {0,1,9})
  - `results/federated/fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5/` (locked primary, {0,3,5})
  - `results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3/` (f=2 secondary, {0,3})
- `per_class` instrumentation in `round_history.json` is additive: the
  original 4 scalar fields (`val_macro_f1_headline`, `val_macro_f1_all`,
  `val_false_positive_rate`, `val_attack_recall`) are unchanged; `per_class`
  is a new key alongside them, present in both the {0,3,5} and f=2 {0,3}
  runs' history, absent from the {0,1,9} run's and both clean runs' (all
  three predate the instrumentation) — recovery path for those is
  inference-only replay against the saved `model_best.pt`
  (`results/inspection/retro_replay_val_metrics_a0.5_s42.json`).

## Artifact index

- `configs/attack.yaml` — attack config, resting at LOCKED PRIMARY (f=3, {0,3,5})
- `src/attacks/label_flip.py` (canonical) / `federated/xfed_federated/_vendored/label_flip.py` (vendored)
- `federated/xfed_federated/{client_app.py,server_app.py,task.py}` — integration, hard guard, tag collision fix, per_class instrumentation
- `results/attacks/a0.5_s42_f3_sudden/` — {0,1,9} flip log + manifest
- `results/attacks/a0.5_s42_f3_sudden_silos0-3-5/` — {0,3,5} flip log + manifest
- `results/attacks/a0.5_s42_f2_sudden_silos0-3/` — f=2 {0,3} flip log + manifest
- `results/federated/fedavg_a0.5_s42_poisoned_f3_sudden/` — {0,1,9} validation-only run artifacts
- `results/federated/fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5/` — {0,3,5} validation-only run artifacts
- `results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3/` — f=2 {0,3} validation-only run artifacts
- `results/inspection/silo_family_composition_a0.5_s42.csv` — per-silo family composition
- `results/inspection/frontier_f3_a0.5_s42.csv`, `frontier_f2_a0.5_s42.csv` — combinatorial coverage frontier
- `results/inspection/attack_row_flip_diagnostic_a0.5_s42_f3_sudden.{csv,json}` — retired-rule coverage diagnostic
- `results/inspection/retro_replay_val_metrics_a0.5_s42.json` — inference-only per-family replay
- `results/inspection/round_history_comparison_a0.5_s42.json` — full round-by-round series, all statistics, all 5 runs (pre-f=2)
- `results/inspection/attack_gate_a0.5_s42_f2_sudden_silos0-3.log` — full f=2 run log
