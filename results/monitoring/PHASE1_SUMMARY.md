# ByzAgent Phase 1 — Per-Client Behavioral Statistics — Summary

**Verdict: PASS** (criterion: at least one of the 5 stats shows a clear,
numerically-stated malicious-vs-clean separation in the poisoned run, absent
or much smaller in the clean run). **Live wiring separately confirmed via a
2-round smoke test — CLOSED.** 2026-08-26. Phase 2 (Krum / trimmed-mean),
Phase 3 (LLM agent), Phase 4 (rolling-history detection), Phase 5 (eval
harness) are NOT started.

**No live training was required for this gate.** Both the clean baseline
(`fedavg_a0.5_s42`) and the locked-primary poisoned run
(`fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5`) had already saved every
round's global model (`round_checkpoints/round_{r:03d}.pt`) and every
client's post-training model (`silo_checkpoints/round_{r:03d}_silo_{s}.pt`)
from Phase 0. `scripts/replay_client_stats.py` reconstructs `client_stats.jsonl`
for a completed run from those checkpoints alone, with zero retraining.

## What was built

- `src/monitoring/client_stats.py` (canonical) / vendored copy at
  `federated/xfed_federated/_vendored/client_stats.py` — pure, architecture-
  agnostic stat functions (`flatten_state_dict`, `state_dict_delta`, `l2_norm`,
  `cosine_similarity`) plus `ClientStatsRecorder`, the per-round accumulation
  + JSONL history-buffer writer.
- `federated/xfed_federated/server_app.py` — `LoggingFedAvg` extended with a
  `configure_train` override (caches the previous-round global ArrayRecord,
  the only point in Flower's `strategy.start()` loop it's available from) and
  an `aggregate_train` extension that computes all 5 stats per client, per
  round, before FedAvg's own aggregation discards the individual replies.
  Both overrides still call `super()` unchanged — the actual federated result
  (weights, aggregation) is untouched; only a side channel is added, same
  discipline as the existing Chat 04 silo-checkpoint side channel.
- `scripts/replay_client_stats.py` — retrospective replay for any already-
  completed run (used here for both gate runs; will not be needed for future
  runs, which produce `client_stats.jsonl` live).
- `scripts/phase1_verification_gate.py` — the gate analysis below.

## The 5 stats, and how each was resolved

| stat | source |
|---|---|
| update_norm | L2 distance, flattened client post-training state_dict vs. flattened previous-round global state_dict |
| cosine_to_global | cos(client update, this round's actual FedAvg aggregate update) |
| cosine_to_peer_mean | cos(client update, **unweighted** mean of all clients' updates this round) |
| train_loss | last-epoch local training loss, already present in the client's own reply (`metrics["train_loss"]`) — zero new computation |
| val_accuracy | client's post-training model run against the CENTRALIZED clean validation set (`val_mask.parquet`, positional against `train_pool.parquet`), server-side — never the client's own local data |

**PEER_MEAN_IS_UNWEIGHTED — locked, do not drift toward sample-weighting.**
A sample-weighted peer mean would let a large malicious silo partially define
its own baseline, shrinking the very deviation this stat exists to catch.
Deliberately inconsistent with FedAvg's own aggregation weighting, on
purpose. See the docstring in `src/monitoring/client_stats.py`.

**Storage:** JSONL, one row per (round, silo_id), mirroring the existing
`silo_metrics.jsonl` convention exactly — trivial groupby/filter for Phase
4's rolling-history read, no new storage technology.

**Fail-loud guard, as required:** `ClientStatsRecorder.record_client` /
`finalize_round` raise `RuntimeError` immediately if called without a
preceding `start_round` (i.e. no cached previous-round global weights) —
never silently computes against `None`/zero/stale state.

## Verification gate — all four numeric requirements, locked-primary poisoned run vs. clean baseline

Both runs' `client_stats.jsonl`: `results/federated/fedavg_a0.5_s42/client_stats.jsonl`,
`results/federated/fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5/client_stats.jsonl`.
Full per-round data: `results/inspection/phase1_gate_a0.5_s42_f3_sudden_silos0-3-5.json`.

**Separation measure (applied consistently across all 5 stats):** Glass's
delta, `(mean_malicious − mean_clean) / std_clean`, computed per round from
the 3 malicious silos {0,3,5} vs. the other 7, **in both runs** — the clean
run gets the identical {0,3,5}-vs-rest grouping applied as a control (are
these particular silos just naturally different, independent of any attack?
alpha=0.5 non-IID partitioning alone could produce that).

**Sample-count gating check (val_accuracy):** does not apply. Every client's
validation accuracy is measured against the same fixed 143,513-row
centralized validation set, every round, regardless of silo — there is no
small client-local eval set here to gate.

### Summary — mean |Glass's delta| across all 20 rounds

| stat | poisoned run | clean-run control (same {0,3,5} grouping, no attack) | ratio | verdict |
|---|---|---|---|---|
| **train_loss** | **140.9** | **4.17** | **33.8x** | **clear separation, PASS** |
| cosine_to_peer_mean | 1.78 | 1.59 | 1.11x | no separation beyond natural variance |
| update_norm | 1.32 | 1.19 | 1.12x | no separation beyond natural variance |
| cosine_to_global | 1.56 | 1.67 | 0.93x | no separation (poisoned run *smaller*) |
| val_accuracy | 0.97 | 3.17 | 0.31x | attack *narrows* the natural gap, not widens it |

**Only 1 of 5 stats clearly passes. This is reported in full per the "always
report all four/all five, never smooth over a divergence" standing rule —
see below for each stat's actual round-by-round behavior, not just the
summary ratio.**

### train_loss — the clear signal

Glass's delta, round 1 → 20:

- **Poisoned:** 16.2, 89.6, 114.7, 130.1, 143.0, 149.4, 153.4, 164.8, 162.9,
  168.0, 159.9, 156.4, 149.4, 155.8, 151.6, 159.1, 152.6, 150.8, 145.5, 144.7
- **Clean control:** 1.4, 4.2, 2.1, 2.2, 2.3, 2.3, 2.6, 3.0, 3.3, 4.0, 4.2,
  4.6, 4.7, 4.7, 4.8, 5.2, 5.7, 6.2, 7.6, 8.2

Raw numbers at round 10 (representative): poisoned run malicious mean loss
0.710 (std 0.075) vs. clean mean 0.007 (std 0.004) → delta 168.0. Clean-run
control at round 10: silos {0,3,5} mean loss 0.022 (std 0.012) vs. rest mean
0.007 (std 0.004) → delta 4.0. **Classification: immediate onset (visible
already at round 1, consistent with `sudden` mode's constant flip_fraction
from round 1), then widening/plateauing** — clean silos' loss keeps
converging toward ~0, malicious silos' loss plateaus at an irreducible floor
set by the 40%-flip label noise, so the gap *grows* through the run rather
than appearing once and fading. Zero sign flips across all 20 rounds in
either run — this is a stable, monotonic pattern, not a one-shot spike or
noise.

### The other four stats — reported honestly, not buried

- **update_norm, cosine_to_global, cosine_to_peer_mean:** the poisoned run's
  per-round Glass's-delta trajectory is nearly indistinguishable in shape and
  magnitude from the clean-run control's trajectory for the *same three
  silos* (e.g. cosine_to_peer_mean: poisoned −2.21→2.40 across 20 rounds;
  clean control −2.77→1.85 — the same rising trajectory, present with or
  without any attack). Silos {0,3,5} are evidently just naturally different
  from the rest under this alpha=0.5 non-IID partition (plausibly a size/
  composition effect independent of poisoning), and the label-flip attack
  adds no measurable increment on top of that for these three stats at this
  attack strength.
- **val_accuracy:** malicious silos lag clean silos in raw validation
  accuracy in *both* runs (delta stays negative throughout), but the gap is
  **consistently smaller** in the poisoned run (−1.45→−0.55) than in the
  clean-run control (−5.08→−2.83), every single round. This is not noise —
  it is a clean, monotonic pattern in the *opposite* direction from what a
  naive "bigger gap = more suspicious" reading would expect. Reading:
  {0,3,5} appear to be smaller/harder-to-generalize silos whose local models
  already score poorly on the centralized validation set even without any
  attack; flipping their local labels toward Benign (the majority class,
  ~75% of validation rows) nudges their raw accuracy score *up*, partially
  masking rather than revealing their local weirdness on this particular
  metric. **A raw-accuracy-only detector would be actively misled by this
  attack, not alerted by it.**

## Interpretation (observation, not a scope decision — routes to 01_Planning)

Of the 5 Phase 1 stats, only `train_loss` shows a strong, attack-attributable
signal against this locked-primary configuration (f=3, sudden,
flip_fraction=0.4, {0,3,5}). The other four are dominated by natural
non-IID silo heterogeneity at alpha=0.5, or (val_accuracy) move in the
attack-masking direction. This satisfies the stated PASS bar (only one stat
is required), but it is a much narrower result than "5 stats give 5
independent detection signals" would suggest, and should inform how Phase 2
(Krum/trimmed-mean distance metric choice) and Phase 3/4 (which stats the
agent should weight) get designed — a decision for Planning, not made here.

## Two findings that MUST carry forward into Phase 3/4 ground truth

**(a) `train_loss`'s 33.8x separation is the EASY case, and validates the
instrumentation, not that all 5 stats carry independent signal.**
Label-flipping directly inflates the loss function that produced this
number — a malicious client is quite literally training against noisier
labels, so elevated loss is close to definitional, not a subtle detection
win. This PASS proves the stats-computation pipeline works end to end; it
does **not** establish that `update_norm`, `cosine_to_global`, and
`cosine_to_peer_mean` carry independent signal — this run's evidence says
they don't, at this attack strength. **The real test is Phase 4's `gradual`
mode**, where the flip fraction ramps slowly by design specifically to stay
under any single-round threshold long enough to accumulate before being
caught. If the three geometry-based stats show near-zero separation there
too (as they did here), the agent may end up **effectively loss-threshold-
only despite having 5 input features** — Phase 3 should not design a prompt
that treats all 5 stats as independently informative without first checking
this against `gradual` mode.

**(b) VAL_ACCURACY INVERSION is a design hazard, not merely a non-pass — flag
it as such, do not file it under a routine limitation.** The attack
*reduces* the malicious-vs-clean validation-accuracy gap, every single round
(poisoned −1.45→−0.55 vs. clean-control −5.08→−2.83, monotonically smaller
in magnitude throughout) — because flipping attack-family labels to Benign
directly improves raw accuracy on a validation set that is ~75% Benign. A
detector, or an LLM agent, handed `val_accuracy` **without this context**
could read a malicious client's rising/higher-than-expected accuracy as
evidence of trustworthiness, not suspicion — exactly backwards for this
attack family. **This must be stated explicitly in Phase 3's agent prompt**
(the 1-2 sentences of per-stat context the plan already calls for), so the
agent is never handed this feature as if it points the same direction as the
other four. Flagged now specifically so it cannot be silently rediscovered
as a bug during Phase 3.

## Secondary condition check — f=2 {0,3}, same 5-stat analysis, numbers only

Read-only, same as above: `scripts/replay_client_stats.py` against the f=2
{0,3} run's already-existing `round_checkpoints/`/`silo_checkpoints/`
(Phase 0, `results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3/`,
21 round + 200 silo checkpoints, both confirmed complete before running).
No retraining, no new attack runs. Same separation measure as the {0,3,5}
gate above: **Glass's delta**, `(mean_malicious − mean_clean) / std_clean`,
same clean-baseline run, same {malicious silos}-vs-rest grouping applied to
both the poisoned run and the clean run as a control. Sample-count gating
on `val_accuracy`: confirmed still not applicable — same fixed 143,513-row
centralized validation set every round, no small client-local eval set here
(unchanged from the {0,3,5} check).

`scripts/phase1_verification_gate.py` was made reusable for this (`--poisoned-dir`,
`--attack-manifest`, `--out`; default invocation reproduces the original
{0,3,5} gate byte-for-byte, verified by diff before this addition). Full
per-round data: `results/inspection/phase1_gate_a0.5_s42_f2_sudden_silos0-3.json`.

### Summary — mean |Glass's delta| across all 20 rounds, both conditions side by side

| stat | f=3 {0,3,5}: poisoned | f=3 {0,3,5}: clean-control | f=3 ratio | f=2 {0,3}: poisoned | f=2 {0,3}: clean-control | f=2 ratio |
|---|---|---|---|---|---|---|
| **train_loss** | 140.9 | 4.17 | 33.8x | **51.8** | **0.34** | **154.3x** |
| cosine_to_peer_mean | 1.78 | 1.59 | 1.11x | 1.24 | 1.06 | 1.17x |
| update_norm | 1.32 | 1.19 | 1.12x | 1.18 | 0.71 | 1.67x |
| cosine_to_global | 1.56 | 1.67 | 0.93x | 0.95 | 1.10 | 0.86x |
| val_accuracy | 0.97 | 3.17 | 0.31x | 0.45 | 1.44 | **0.31x** |

### train_loss, f=2 {0,3} — full round-by-round Glass's delta

- **Poisoned:** 9.9, 24.7, 59.0, 72.7, 77.3, 80.1, 74.6, 71.3, 63.8, 60.4,
  59.4, 55.9, 53.1, 48.5, 48.0, 42.6, 39.7, 35.4, 31.5, 28.0
- **Clean control:** 0.02, 0.34, 0.37, 0.41, 0.46, 0.52, 0.40, 0.47, 0.50,
  0.44, 0.48, 0.45, 0.40, 0.38, 0.33, 0.30, 0.23, 0.13, 0.07, 0.03

Zero sign flips in either series across all 20 rounds. Shape differs from
{0,3,5}'s (which rose then plateaued near its peak through round 20): f=2's
delta rises to a peak at round 6 (80.1) then declines monotonically through
round 20 (28.0) — a rise-then-fall pattern rather than rise-then-plateau.
Magnitude at every round remains at least ~55x the clean-control value at
the same round (e.g. round 10: 60.4 vs 0.44; round 20: 28.0 vs 0.03).

### The other four stats, f=2 {0,3} — round 1 / 10 / 20 raw numbers

| stat | round | poisoned mean_mal (std) | poisoned mean_clean (std) | poisoned Glass's Δ | clean-control Glass's Δ |
|---|---|---|---|---|---|
| update_norm | 1 | 3.343 (0.587) | 4.046 (1.068) | −0.658 | −0.460 |
| update_norm | 10 | 3.271 (0.080) | 2.539 (0.611) | 1.198 | 0.679 |
| update_norm | 20 | 3.734 (0.186) | 2.526 (0.644) | 1.875 | 1.156 |
| cosine_to_global | 1 | 0.418 (0.098) | 0.653 (0.215) | −1.093 | −1.257 |
| cosine_to_global | 10 | 0.187 (0.059) | 0.410 (0.233) | −0.961 | −1.131 |
| cosine_to_global | 20 | 0.178 (0.092) | 0.365 (0.224) | −0.833 | −1.088 |
| cosine_to_peer_mean | 1 | 0.551 (0.076) | 0.681 (0.139) | −0.930 | −1.134 |
| cosine_to_peer_mean | 10 | 0.525 (0.012) | 0.431 (0.067) | 1.408 | 1.090 |
| cosine_to_peer_mean | 20 | 0.567 (0.021) | 0.363 (0.122) | 1.673 | 1.341 |
| val_accuracy | 1 | 0.721 (0.225) | 0.785 (0.280) | −0.227 | −1.367 |
| val_accuracy | 10 | 0.857 (0.056) | 0.907 (0.127) | −0.394 | −1.350 |
| val_accuracy | 20 | 0.851 (0.063) | 0.919 (0.109) | −0.627 | −1.595 |

All four series' sign-flip counts and first-half/second-half means are in
`results/inspection/phase1_gate_a0.5_s42_f2_sudden_silos0-3.json` alongside
the per-round numbers above, in the same structure as the {0,3,5} gate file.

## Live wiring — smoke-test result

The `configure_train`/`aggregate_train` wiring in `server_app.py` (untested
by the checkpoint-replay gate above, since that used retrospective replay by
design) was separately exercised with a real 2-round `flwr run`:

- **Config:** alpha=0.5, seed=42 (existing partition, no new Dirichlet draw
  needed), mu=0.0 (confirmed inert — `mu>0` activates a real, separate
  FedProx code path in `local_train_epochs`, so a nonzero value was
  correctly avoided as a tag differentiator per review). `attack.yaml`
  temporarily set to `enabled: true, f: 0, malicious_silos: []` — enough to
  invoke the existing hard test-guard (so `test_global.parquet` is never
  touched, honoring "all Phase 1 work is validation-only"), while
  `resolve_malicious_silos` resolves to an empty list so **zero actual label
  flips occur anywhere** (confirmed via `flip_log.csv`: `n_rows_flipped=0`
  for every silo, every round). Tag `fedavg_a0.5_s42_poisoned_f0_sudden_silos`
  — confirmed collision-free against every existing `results/federated/`
  directory before running.
- **Result: PASS.** Both rounds' `aggregate_train` completed with "10
  results and 0 failures"; `client_stats.jsonl` was written live with 20
  sane rows (2 rounds × 10 silos, no unexpected NaNs); the hard-stop
  `RuntimeError` fired exactly as designed
  ("`HARD STOP: configs/attack.yaml has attack.enabled: true (f=0,
  mode='sudden')...`"), after writing validation-only artifacts
  (`attack_val_summary.json` etc.) and before any test-set evaluation —
  confirmed by the absence of `final_metrics.json`/`config.json` in the
  scratch output directory (those are only written past the guard).
- `configs/attack.yaml` reverted to its exact locked resting state
  immediately after (verified byte-for-byte via checksum:
  `dff0d8a7f2eaaf8ea25b5dbbe1d2c3ce`, matching the pre-edit backup). Scratch
  output (`results/federated/fedavg_a0.5_s42_poisoned_f0_sudden_silos/`,
  `results/attacks/a0.5_s42_f0_sudden_silos/`) deleted after verification —
  nothing from this smoke test remains on disk.
- Environment note, not a Phase 1 blocker: this flwr version reports
  `Federation @none/default` with a `FutureWarning` about `num_gpus=0/None`
  when invoked via `flwr run federated local-simulation` directly — the
  legacy `options.` fields in `~/.flwr/config.toml` appear not to carry over
  automatically. Harmless for this tiny 2-round smoke test; worth an
  explicit `--federation-config` override for any future *real*, larger
  live run to guarantee the intended sequential single-GPU-per-client
  resource pattern Phase 0 relied on.

## Known limitations / forward pointers — do not lose these

- **TODO, binding starting with Phase 2's baseline runs:** before launching
  any future REAL (non-smoke-test) `flwr run` — Phase 2's baseline runs
  onward — explicitly verify/set `--federation-config` to guarantee
  sequential client execution (one client training at a time on the single
  GPU), and do not rely on `~/.flwr/config.toml`'s legacy `options.` fields
  to carry this over automatically (see the smoke-test environment note
  below — they did not, in this exact setup). This is not cosmetic: the 6GB
  VRAM ceiling this whole project is designed against depends on training
  staying sequential rather than parallelized across the GPU. A silent
  fallback to parallel/concurrent client execution on a real 20-round,
  10-silo job would surface as an OOM crash, potentially well into the run
  rather than at the start. Confirm sequential execution before launching,
  not after discovering it via a crash.
- **`configs/monitoring.yaml`: deliberately NOT created.** YAGNI — Phase 1
  has no thresholds or detection logic to configure. Create it when Phase 2's
  Krum threshold or Phase 4's rolling-window size N are real values, following
  the `configs/attack.yaml` separate-file convention (Contribution B stays
  visibly distinct from Contribution A).
- **Live wiring:** confirmed via the 2-round smoke test above — no longer an
  open gap.
- **n=1 seed**, same limitation Phase 0 already logged as a Phase 5
  obligation — this gate is evidence from one paired (alpha=0.5, seed=42)
  comparison, not a cross-seed result.
- Only the **locked-primary** {0,3,5} condition was checked here. The f=2
  {0,3} and retired {0,1,9} conditions were not re-verified against Phase 1's
  stats — not required by this phase's scope, logged here in case a future
  phase wants that cross-check.
- `results/federated/fedavg_a0.1_s9999/`: known repo artifact of unknown
  origin, alpha=0.1, no collision risk with any locked or planned config,
  not touched. Future sessions should not spend time investigating this.

## Artifact index

- `src/monitoring/client_stats.py` (canonical) / `federated/xfed_federated/_vendored/client_stats.py` (vendored)
- `federated/xfed_federated/{server_app.py,task.py}` — `LoggingFedAvg` extension, re-export
- `scripts/replay_client_stats.py` — retrospective replay from checkpoints
- `scripts/phase1_verification_gate.py` — gate analysis (Glass's delta, all 5 stats); now takes
  `--poisoned-dir`/`--attack-manifest`/`--out` (default = original {0,3,5} gate, unchanged)
- `results/federated/fedavg_a0.5_s42/client_stats.jsonl` — clean run, replayed
- `results/federated/fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5/client_stats.jsonl` — f=3 {0,3,5} poisoned run, replayed
- `results/federated/fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3/client_stats.jsonl` — f=2 {0,3} poisoned run, replayed
- `results/inspection/phase1_gate_a0.5_s42_f3_sudden_silos0-3-5.json` — full per-round gate data, f=3 {0,3,5}
- `results/inspection/phase1_gate_a0.5_s42_f2_sudden_silos0-3.json` — full per-round gate data, f=2 {0,3}
