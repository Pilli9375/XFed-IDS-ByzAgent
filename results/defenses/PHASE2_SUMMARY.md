# ByzAgent Phase 2 — Krum / Multi-Krum / Trimmed-Mean — Summary

**Status: CODE BUILT, VERIFIED, AND THE FULL 9-RUN MATRIX EXECUTED.**
Build-and-regression-check work completed 2026-08-26; the 9-run experiment
matrix (3 strategies x {f=3 {0,3,5}, f=2 {0,3}, clean control}, seed 42,
20 rounds) completed 2026-08-27. Seeds 1337/2024 remain the Phase 5
obligation, not run here. Phase 3 (LLM agent), Phase 4 (rolling history),
Phase 5 (eval harness) are NOT started. **This document reports numbers
only, per 01_Planning's explicit instruction — interpretation of what these
numbers mean routes to 01_Planning, not decided here.**

## Library verification (STEP 1, read-only)

Installed `flwr==1.33.0` (`C:\Users\nagaa\anaconda3\envs\xfed\Lib\site-packages\flwr`)
ships `flwr.serverapp.strategy.{krum,multikrum,fedtrimmedavg}` alongside
`fedavg`. Read the actual source (not just docstrings):

- `Krum(MultiKrum)` fixes `num_nodes_to_select=1`; `MultiKrum.aggregate_train`
  computes squared-L2 distance in the full flattened weight-parameter space
  (`compute_distances`), scores each client by sum-of-distances to its
  `n - num_malicious_nodes - 2` nearest neighbors, keeps the
  `num_nodes_to_select` lowest-scoring clients, weighted-means only those.
  Matches textbook Blanchard et al. Krum/Multi-Krum.
- `FedTrimmedAvg.aggregate_train` computes, per layer array, a per-coordinate
  trimmed mean (`np.partition` along the client axis) with `beta` = fraction
  cut per tail (default 0.2). Matches textbook coordinate-wise trimmed mean.
- Neither exposes per-round selection/trim identity in its return value
  (`(ArrayRecord | None, MetricRecord | None)` only) — side-channel logging
  had to be built, same pattern as Phase 1's `client_stats.py`.
- `configure_train`/`aggregate_evaluate`/`configure_evaluate` are NOT
  overridden by any of Krum/MultiKrum/FedTrimmedAvg — inherited from FedAvg
  unchanged, so the Phase 0/1 `LoggingFedAvg` side-channel logic (previous-
  round weight caching, per-silo checkpointing, Phase 1 behavioral stats)
  transplants onto these strategies without modification.
- The hard test-set guard in `server_app.py::main()` is plain
  `if attack_enabled: ... raise RuntimeError(...)` control flow, independent
  of which `Strategy` subclass is constructed — confirmed strategy-agnostic
  by construction (it doesn't inspect `strategy` at all) and confirmed live
  by firing correctly in every smoke test below.

## 01_Planning decisions (locked before any code was written)

1. **Build both Multi-Krum and classical Krum. Multi-Krum is PRIMARY.**
   `num_nodes_to_select = n_silos - f` (7 at f=3, 8 at f=2) is the headline
   Krum-family comparison against trimmed-mean and later ByzAgent. Classical
   Krum (`num_nodes_to_select=1`, deploys one raw client's local model as the
   next global model) is built too, but ONLY as a secondary sanity check
   ("does raw single-client selection agree with Multi-Krum's selection
   direction") — **never plotted or reported as a standalone baseline**
   comparable to ByzAgent or to Multi-Krum. See `LoggingKrum`'s docstring in
   `server_app.py`.
2. **Oracle f, both defenses, disclosed explicitly every time.**
   `num_malicious_nodes` = the TRUE f from `configs/attack.yaml` for the
   condition under test (3 for {0,3,5}, 2 for {0,3}) — a deliberate,
   documented advantage given to Krum/MultiKrum/trimmed-mean. ByzAgent
   (Phase 3+) will not be given this number. Every run writes
   `defense_config.json` stating this explicitly, and it must be repeated
   wherever results are first shown, not left implicit.
3. **`beta = f / n_silos` per condition, not a fixed value.** f=3 -> 0.3,
   f=2 -> 0.2. Computed at runtime from `num_malicious_nodes`, never
   hand-set per run — a stale hand-set `beta` mismatched to the actual `f`
   under test was judged a real risk (same failure class as the scaler-drift
   incident noted in `configs/model.yaml`'s own docstring).
4. **Trim-rate logging: per-round, per-silo trim COUNT/RATE summary**, not
   raw per-coordinate identity. Finer granularity is regenerable later from
   `round_checkpoints`/`silo_checkpoints` if ever needed (same pattern as
   Phase 0/1's checkpoint-then-replay).

## What was built

- `federated/xfed_federated/server_app.py` — refactored. The single
  `LoggingFedAvg(FedAvg)` class from Phase 0/1 is now `LoggingMixin`, a
  strategy-agnostic side channel (previous-round weight caching, per-silo
  checkpoints + `silo_metrics.jsonl`, Phase 1's 5 behavioral stats via
  `ClientStatsRecorder`), plus a `_log_mechanism` no-op hook for
  strategy-specific mechanism logging. Four concrete classes:
  - `LoggingFedAvg(LoggingMixin, FedAvg)` — unchanged behavior from before
    this refactor (see regression check below).
  - `LoggingMultiKrum(_KrumMechanismLogging, LoggingMixin, MultiKrum)` —
    **PRIMARY** headline Krum comparison.
  - `LoggingKrum(_KrumMechanismLogging, LoggingMixin, Krum)` — classical
    Krum, **secondary sanity check only**.
  - `LoggingFedTrimmedAvg(LoggingMixin, FedTrimmedAvg)` — trimmed-mean.
- `_KrumMechanismLogging`: reimplements `select_multikrum`'s exact scoring
  (using the library's own `compute_distances`, not a re-derivation of the
  distance math) as a side channel that runs BEFORE `super().aggregate_train()`
  — deterministic, no randomness, so it cannot diverge from what the library
  actually selects. Logs `results/federated/{tag}/krum_selection.jsonl`:
  one row per (round, silo), with `krum_score` and `selected` (bool).
- `LoggingFedTrimmedAvg._log_mechanism`: reimplements the same per-coordinate
  ranking `trim_mean` uses internally, via `np.argsort` instead of
  `np.partition` (partition only exposes trimmed VALUES; argsort recovers
  client INDICES). Runs on non-destructive reads (`record[key]`, never
  `.pop()`) before the library's own destructive-pop-based trimming, so it
  cannot starve the real aggregation. Logs
  `results/federated/{tag}/trim_rate.jsonl`: one row per (round, silo), with
  `trim_count`/`total_coords`/`trim_rate`.
- Both reimplementations were empirically checked against the library's own
  functions on synthetic data before being wired in (`compute_distances` +
  hand-rolled scoring vs. `select_multikrum`: identical selected set;
  hand-rolled argsort-based trim-index recovery vs. `trim_mean`: identical
  trimmed-value set) — see the STEP 1 report exchange for the exact
  verification script.
- `configs/defense.yaml` — new, mirrors `configs/attack.yaml`'s convention.
  `defense.strategy: fedavg | multikrum | krum | trimmed_mean`,
  `defense.num_malicious_nodes` (oracle f). Resting state: `fedavg`, `0` —
  zero effect on any existing clean/attack run.
- `server_app.py::main()`: derives `algo` tag / `num_nodes_to_select` / `beta`
  from `configs/defense.yaml` + `configs/attack.yaml`'s `n_silos`; writes
  `defense_config.json` unconditionally (before training starts, survives
  the attack hard-guard) stating the strategy and the oracle-f disclosure
  verbatim.

## Verification — byte-for-byte FedAvg regression check

Required by 01_Planning before any Krum/TrimmedAvg code was written: prove
the `LoggingMixin` refactor did not change FedAvg's behavior.

Re-ran the clean baseline (alpha=0.5, seed=42, 20 rounds, `defense.strategy:
fedavg`) through the refactored `server_app.py`, into the SAME output
directory as the existing locked `results/federated/fedavg_a0.5_s42/`
(backed up first). Sequential single-GPU execution forced via
`--federation-config "num-supernodes=10 client-resources-num-cpus=2
client-resources-num-gpus=1.0"` (the `~/.flwr/config.toml` legacy `options.`
fields are silently ignored once `--federation-config` is passed at all —
confirmed by reading `flwr/cli/run/run.py`, matches the Phase 1 TODO this
was meant to close out).

**Result: exact match, every artifact:**

| artifact | check | result |
|---|---|---|
| `round_history.json` | every shared scalar key, all 21 rounds (0-20) | 0 mismatches |
| `final_metrics.json` | full deep-equality (incl. nested per-class test metrics) | **identical** |
| `config.json` | pre-existing keys | identical (2 new additive keys: `defense_strategy`, `num_malicious_nodes_oracle`) |
| `silo_metrics.jsonl` | row content (200 train + 200 eval rows) | **identical** (see note) |
| `client_stats.jsonl` | row content (200 rows) | **identical** (see note) |
| `model_best.pt`, `model_last.pt` | md5 checksum | **identical** |
| `round_checkpoints/*.pt` (21 files) | md5 checksum | **identical**, 0/21 mismatched |
| `silo_checkpoints/*.pt` (200 files) | md5 checksum | **identical**, 0/200 mismatched |
| best round / val macro-F1 | printed summary | round 18, 0.9760 — matches the locked `max` statistic in `PHASE0_SUMMARY.md` exactly |

Note: `silo_metrics.jsonl`/`client_stats.jsonl` are append-mode (accumulate
across a single run's own rounds); re-running into the same directory
doubled their line count (existing 400/200 lines + this run's own 400/200
appended after). Verified the appended half is byte-for-byte identical to
the original half (`new[:N] == old` and `new[N:] == old` both `True`) —
confirms the duplication is a pure test-methodology artifact of reusing the
output directory, not a computation difference. The directory was restored
to its original (non-duplicated) state from the backup afterward, since the
backup was already proven equivalent to a fresh run.

Determinism note: the pipeline reseeds `torch.manual_seed(seed)` /
`torch.cuda.manual_seed_all(seed)` inside `build_model()`, called immediately
before every client's local training and every server-side evaluation each
round — this is what makes exact reproduction possible on the same GPU/
driver/library versions, not an accident.

## Verification — live smoke tests, all three new strategies

2-round smoke tests, same pattern Phase 1 used to confirm live wiring:
`configs/attack.yaml` temporarily set to `enabled: true, f: 0,
malicious_silos: []` (fires the hard test-guard, zero actual label flips —
confirmed by Phase 1 already, reused verbatim here) so no smoke test ever
touches `test_global.parquet`. `configs/defense.yaml` set per strategy,
`num_malicious_nodes: 3` (exercises non-trivial selection/trimming even with
no live attack). All three ran to completion (guard fired as designed after
round 2, not a crash), scratch output deleted after inspection, both config
files reverted and verified byte-for-byte via md5 against their pre-test
checksums (`attack.yaml`: `dff0d8a7f2eaaf8ea25b5dbbe1d2c3ce`, matching the
checksum Phase 1 itself recorded — confirms no drift since Phase 1's close;
`defense.yaml`: `2e216d3e234373dd8ba393f792e0ecff`).

| strategy | rounds | `aggregate_train` | mechanism log | sanity check |
|---|---|---|---|---|
| `multikrum` (f=3, select=7) | 2/2 completed | 10 results, 0 failures both rounds | `krum_selection.jsonl` | exactly 7/10 `selected: true` every round |
| `krum` (classical, f=3) | 2/2 completed | 10 results, 0 failures both rounds | `krum_selection.jsonl` | exactly 1/10 `selected: true` every round |
| `trimmed_mean` (beta=0.3) | 2/2 completed | 10 results, 0 failures both rounds | `trim_rate.jsonl` | `sum(trim_count)` = 119,094 = `2 * lowercut * total_coords` (`lowercut=3`, `total_coords=19,849` — matches the locked MLP's exact parameter count from `configs/model.yaml`) both rounds |

## Real Phase 2 experiments — results, seed 42, 20 rounds each

**Clean-control design decision (01_Planning, made before these runs):** the
3 clean-control runs (one per strategy, no actual attack present) use
`num_malicious_nodes=3` — i.e. each defense is configured as if defending
against the primary f=3 threat even though the fleet is fully honest. This
answers "what does this defense cost when configured for the worst case but
nobody is attacking," not "what if it assumes zero attackers" (which would
make Multi-Krum/TrimmedAvg near-duplicates of the already-locked clean
FedAvg baseline). Not run at f=2 — judged not to test a materially
different question.

**ORACLE f DISCLOSURE — true for every attack-condition and clean-control
run below:** Multi-Krum, classical Krum, and FedTrimmedAvg were all given
`num_malicious_nodes` = the TRUE attack strength (3 for f=3 runs, 2 for f=2
runs, 3 for all clean-control runs) — not estimated, not inferred. This is
a documented advantage given to these baselines; ByzAgent (Phase 3+) will
not be given this number.

**Operational incident:** the first submission of classical-Krum-vs-f=2
crashed silently ~1m38s into round 1 (no Python traceback; Ray/Windows-level
process fault, root cause not diagnosed). Retried with the identical
unchanged config; the retry completed normally in ~25.6 min. The number
below is from the successful retry. `flwr ls --run-id <id> --format json`
was needed to see the crash's true status (`finished:failed`) — `flwr log`
alone did not surface it after the process died.

### Outcome-level: all four statistics + recovery_fraction

Locked anchors (`PHASE0_SUMMARY.md`, final-5-round mean): f=3 clean=0.9513,
poisoned-FedAvg=0.8746 (gap 0.0767); f=2 clean=0.9513, poisoned-FedAvg=0.8787
(gap 0.0726). `recovery_fraction >= 0.5` = succeeds, `< 0.5` = fails, raw
value always reported.

| strategy | condition | mean | median | final5mean | max | recovery_fraction | verdict | note |
|---|---|---|---|---|---|---|---|---|
| Multi-Krum (PRIMARY) | f=3 {0,3,5} | 0.7716 | 0.8018 | 0.8534 | 0.8633 | **-0.2766** | FAILS | — |
| Multi-Krum (PRIMARY) | f=2 {0,3} | 0.8368 | 0.8474 | 0.9766 | 0.9812 | **1.3490** | SUCCEEDS | **recovery driven by exclusion of silos {2,7} (largest, >90% Benign) in both runs, unrelated to attack — malicious silos excluded 0/20 rounds in either condition. See diagnostic below; do not cite as attack mitigation.** |
| Multi-Krum (PRIMARY) | clean (oracle f=3) | 0.8223 | 0.8508 | 0.9086 | 0.9300 | n/a | test=0.9261 | — |
| FedTrimmedAvg | f=3 {0,3,5} | 0.8046 | 0.8351 | 0.8696 | 0.8839 | **-0.0647** | FAILS | — |
| FedTrimmedAvg | f=2 {0,3} | 0.8294 | 0.8274 | 0.9419 | 0.9631 | **0.8702** | SUCCEEDS | mechanism-level excess over malicious silos is smaller than the same silo-size/Benign-skew confound seen in Multi-Krum — see corrected mechanism section below; not confirmed as attack-attributable |
| FedTrimmedAvg | clean (oracle f=3) | 0.8388 | 0.8565 | 0.9221 | 0.9616 | n/a | test=0.9590 | — |
| classical Krum (SECONDARY ONLY) | f=3 {0,3,5} | 0.7014 | 0.6957 | 0.7738 | 0.8466 | **-1.3139** | FAILS | — |
| classical Krum (SECONDARY ONLY) | f=2 {0,3} | 0.7536 | 0.7495 | 0.7651 | 0.8817 | **-1.5652** | FAILS | — |
| classical Krum (SECONDARY ONLY) | clean (oracle f=3) | 0.5792 | 0.5983 | 0.6405 | 0.7474 | n/a | test=0.7480 | — |

A reader must not be able to conclude Multi-Krum detected or mitigated this
attack from the table alone: its only outcome-level SUCCEED is annotated
in-row, not left to a footnote.

Clean-control test-set macro-F1 (7 headline families, best-by-validation
checkpoint; first and only test touch for each of these 3 new
configurations, per the per-configuration-once-touched discipline): clean
FedAvg (already locked) = 0.9753; Multi-Krum(f=3-oracle) = 0.9261;
FedTrimmedAvg(f=3-oracle) = 0.9590; classical Krum(f=3-oracle) = 0.7480.

### Mechanism-level: malicious-silo selection/trim rate vs. chance

**Krum family** (per-round exclusion rate of the TRUE malicious silos —
`selected: false` — from `krum_selection.jsonl`):

| strategy | condition | observed malicious exclusion rate | chance baseline (locked, f/n) | mechanically-correct chance baseline |
|---|---|---|---|---|
| Multi-Krum | f=3 {0,3,5} | **0.0000** | 0.30 | 0.30 (num_excluded=f by construction — f/n IS correct here) |
| Multi-Krum | f=2 {0,3} | **0.0000** | 0.20 | 0.20 (num_excluded=f by construction — f/n IS correct here) |
| classical Krum | f=3 {0,3,5} | **1.0000** | 0.30 | **0.900** (num_excluded=9 always, independent of f — f/n is NOT the correct baseline for classical Krum) |
| classical Krum | f=2 {0,3} | **1.0000** | 0.20 | **0.900** (same caveat) |

**Headline finding, locked 2026-08-27 (01_Planning), replaces the weaker
"near-zero/null exclusion rate" framing:** Krum's distance-based selection
is **dominated by silo size/composition, not by attack-relevant behavior.**
It consistently excludes the same two large (30.3%/23.0% of the fleet),
Benign-heavy (>90%) silos regardless of attack condition, attack strength,
or which silos are actually malicious — 0/20 rounds of malicious exclusion
in both the f=3 and f=2 runs. The apparent f=2 "recovery" is a direct side
effect of this unrelated exclusion mechanically shifting the malicious
silos' share of the surviving aggregate's weight upward (9.8% -> 21.0% of
the fleet), not evidence of attack detection or mitigation. Full evidence
chain below.

### Diagnostic — what actually produced Multi-Krum's f=2 recovery_fraction=1.35

Requested 2026-08-27 (01_Planning), before this number is cited anywhere:
a `recovery_fraction` this high sitting next to a 0.0000 malicious-exclusion
rate (identical to the f=3 run that FAILED) cannot mechanistically be
credited to attack detection. Read-only investigation against
`krum_selection.jsonl` and the existing Phase 0/1 silo-composition table
(`results/inspection/silo_family_composition_a0.5_s42.csv`), no retraining.

**(a) Which silos were excluded, per round:** In the f=2 {0,3} run, Multi-
Krum excluded the exact same 2 silos — **{2, 7}** — in **all 20 of 20
rounds**, with no variation whatsoever. In the f=3 {0,3,5} run (`num_excluded=3`),
it excluded **{2, 7, 8}** in round 1 only, then **{2, 7, 9}** in every one
of the remaining 19 rounds. Silos {2, 7} are excluded in literally every
round of both runs; silo 9 joins from round 2 onward in the f=3 run. The
true malicious silos (0, 3 in the f=2 run; 0, 3, 5 in the f=3 run) were
excluded **zero times, in any round, in either run.**

**(b) Cross-reference against silo composition (Phase 0/1 table, pre-attack,
unrelated to which silos are malicious):**

| silo | total rows | % of fleet | % Benign | chronically excluded? |
|---|---|---|---|---|
| 2 | 390,729 | 30.3% | 90.4% | **YES, both runs, every round** |
| 7 | 297,370 | 23.0% | 91.0% | **YES, both runs, every round** |
| 9 | 148,959 | 11.5% | 81.5% | **YES, f=3 only, 19/20 rounds** |
| 0 (malicious) | 88,102 | 6.8% | 9.2% | never |
| 3 (malicious) | 38,827 | 3.0% | 0.3% | never |
| 5 (malicious, f=3 only) | 21,478 | 1.7% | 0.1% | never |

Silos 2 and 7 are, by a wide margin, the two **largest** silos in the
10-silo fleet (30.3% and 23.0% of all training rows — more than half the
federation combined) and are overwhelmingly **Benign-skewed** (>90% Benign).
The malicious silos are the opposite profile: small-to-mid-sized (1.7%-6.8%
of the fleet) and overwhelmingly **non-Benign** (attack-family-loaded by
Phase 0's deliberate worst-case selection criterion). These are two
essentially orthogonal axes — size/Benign-skew vs. maliciousness — and
Krum's weight-space distance metric is tracking the former, not the latter,
in this partition.

**(c) Overlap between the two attack conditions:** Silos {2, 7} are
excluded in **every single round of both the f=2 and f=3 runs**, regardless
of which silos are actually malicious and regardless of attack strength.
This is strong evidence of a property of the (alpha=0.5, seed=42) partition
and Krum's distance geometry — large, Benign-skewed silos are geometric
outliers under Krum's weight-space distance regardless of the attack
condition — not a property of either specific result.

**(d) Does this explain the recovery WITHOUT invoking attack detection?
Yes — directly, with numbers, not by assertion:**

Excluding {2, 7} from the f=2 aggregate does not touch the malicious
silos' contribution at all (they are still fully weighted-averaged in) —
but it mechanically changes the *composition* of the surviving aggregate.
Computed from the same silo-size table: with {2, 7} excluded, the
surviving 8 silos total 603,514 rows, of which the 2 malicious silos
(0, 3) contribute 126,929 rows — **21.0% of the surviving aggregate's
weight**, versus their 9.8% share of the full fleet under plain FedAvg
(no exclusion). Excluding two enormous, extremely Benign-skewed silos
mechanically shifts the aggregate's effective label balance away from
Benign-domination — a plausible, independent driver of a headline
macro-F1 improvement (which weights all 7 headline families equally, so
is sensitive to exactly this kind of rebalancing), unrelated to whether
any poisoning is present. That the resulting recovery_fraction (1.35)
*exceeds 1.0* — outperforming the clean-FedAvg anchor itself, which faced
no poisoning and no exclusion at all — is consistent with this: a defense
cannot outperform "no attack, no defense" by successfully removing an
attack that is still fully present in the aggregate's weights.

The same mechanism runs in the opposite direction at f=3: excluding
{2, 7, 9} removes more clean weight, and with all 3 malicious silos
(0, 3, 5) still fully included, their share of the surviving aggregate
rises to **32.6%** (vs. 11.5% of the full fleet) — a larger compositional
shift toward the malicious silos than at f=2, which plausibly outweighs
whatever Benign-rebalancing benefit the exclusion of large clean silos
provides, netting the observed FAIL.

**Bottom line, stated plainly:** (a)-(c) explain the f=2 recovery_fraction
without invoking attack detection — the 0.0000 malicious-exclusion rate
already ruled out attack detection as the mechanism, and (a)-(c) supply a
concrete, numbers-backed alternative (a silo-size/Benign-skew-driven
compositional side effect of Krum's geometry, identical across both attack
conditions, that happens to net favorably at f=2 and unfavorably at f=3).
This is the more likely and more reportable explanation. **Multi-Krum's
f=2 recovery_fraction=1.35 must not be cited as evidence Multi-Krum
detected or mitigated this attack** — the mechanism-level data directly
contradicts that reading. The f=3 result is untouched by this diagnostic
and is not reinterpreted here.

**FedTrimmedAvg** (per-(round,silo) trim rate from `trim_rate.jsonl`,
malicious silos vs. clean silos vs. two different candidate chance
baselines):

| condition | malicious trim rate | clean-silo trim rate | **CORRECTED chance baseline (2*beta)** | superseded: f/n |
|---|---|---|---|---|
| f=3 {0,3,5}, beta=0.3 | **0.6551** | 0.5764 | **0.60** | ~~0.30~~ |
| f=2 {0,3}, beta=0.2 | **0.4556** | 0.3861 | **0.40** | ~~0.20~~ |

**CORRECTION, 2026-08-27 (01_Planning review), locked going forward:** the
original pre-registration text (still verbatim in the "PHASE 2 PRE-
REGISTRATION" section of this project's ground truth) stated trimmed-mean's
mechanism-level chance baseline as `f/n`, by direct analogy to Krum's `f/n`
baseline. **That analogy does not hold, and `f/n` was wrong for
trimmed-mean.** Why the analogy fails: Krum's exclusion count is pinned to
`f` *by construction* (Multi-Krum's `num_nodes_to_select = n - f` makes
`num_excluded` exactly equal `f`, so `f/n` is the exact hypergeometric
chance rate a specific client gets excluded under uninformative selection).
Trimmed-mean has no equivalent construction: its per-coordinate trim count
is pinned to `beta` (`2*lowercut = 2*int(beta*n)` values discarded per
coordinate, both tails), which is chosen as `f/n` for oracle-sizing reasons
but is otherwise **unrelated to `f` as an exclusion count** — every client,
malicious or clean, is symmetrically exposed to a `2*beta` chance of being
in either discarded tail at any given coordinate under a trim mechanism
carrying no information about maliciousness. **The corrected, locked
chance baseline for trimmed-mean's mechanism check is `2*beta`, not `f/n`.**

**Recomputed headline mechanism number under the corrected baseline:**
malicious-vs-baseline gap is **modest and positive in both conditions,
consistent in direction:** f=3 malicious trim rate 0.6551 vs. baseline 0.60
(+0.0551); f=2 malicious trim rate 0.4556 vs. baseline 0.40 (+0.0556).
Clean-silo rates (0.5764, 0.3861), *aggregated across all 7-8 clean silos*,
sit below their respective corrected baselines in both conditions. **This
aggregated comparison is superseded by the per-silo breakdown below — it
was masking a confound, not showing clean signal.**

**Per-silo confound check, requested 2026-08-27 (01_Planning), before this
number is locked as genuine signal:** does the same silo-size/Benign-skew
confound that dominates Krum's result (silos {2, 7, 9}: largest in the
fleet, >90%/>90%/81% Benign) also show up in trimmed-mean's PER-SILO trim
rates, independent of maliciousness? Broken out per individual silo (not
aggregated malicious-vs-clean):

| silo | f=3 trim rate | f=2 trim rate | role |
|---|---|---|---|
| 2 | 0.7263 | 0.5788 | large/Benign-heavy (clean both runs) |
| 7 | 0.6886 | 0.5177 | large/Benign-heavy (clean both runs) |
| 9 | 0.6080 | 0.3968 | large/Benign-heavy (clean both runs) |
| 3 | 0.7148 | 0.5238 | MALICIOUS both runs |
| 5 | 0.6596 | 0.4994 | MALICIOUS at f=3 only (clean, but naturally extreme composition, at f=2) |
| 0 | 0.5909 | 0.3874 | MALICIOUS both runs |
| 1, 4, 6, 8 | 0.4441/0.4409/0.5493/0.5775 | 0.2254/0.2169/0.3299/0.3238 | ordinary clean, unremarkable size/composition |

Isolating the true "ordinary clean" baseline (silos 1, 4, 6, 8 — small,
unremarkable composition, never malicious) from both the malicious group
and the large/Benign-heavy group:

| condition | ordinary-clean baseline | malicious excess over baseline | large/Benign-heavy-clean excess over baseline |
|---|---|---|---|
| f=3 | 0.5030 | **+0.1522** | **+0.1714** |
| f=2 | 0.3191 | **+0.1365** | **+0.1787** |

**Finding, stated with the same honesty as the Krum result: the confound is
present, and it is LARGER than the malicious-attribution signal, in both
conditions.** The large/Benign-heavy clean silos {2, 7, 9} — the same silos
Krum's geometry chronically excludes for reasons unrelated to attack —
also show elevated per-coordinate trim rates under trimmed-mean, and that
elevation exceeds the malicious silos' own elevation (+0.171 vs. +0.152 at
f=3; +0.179 vs. +0.137 at f=2). This is a genuine, partial size/composition
confound on trimmed-mean's mechanism-level result, not a clean signal.
Additionally, silo 5 — malicious at f=3 but ordinary-clean at f=2 — shows an
elevated trim rate (0.4994) at f=2 *despite not being attacked in that run*,
close to or above the truly-malicious silos' own rates; silo 5's underlying
data is naturally extreme (99.9% non-Benign, concentrated in 1-2 attack
families per Phase 0's composition table), suggesting per-coordinate
trimming is also sensitive to a silo's natural compositional extremity, a
third confounding axis distinct from both size and actual poisoning.

**Revised conclusion, replacing the earlier "real, weak, direction-consistent
signal" framing:** the malicious-vs-baseline excess reported above cannot be
read as attack-detection signal on its own — the same partition property
that explains Krum's f=2 result (large, Benign-skewed silos are outliers
under this partition/architecture, independent of attack condition) is
present here too, and is the larger of the two effects. Whatever genuine
attack-attributable component exists in trimmed-mean's per-coordinate
trimming, if any, is not separable from this confound using the data
collected so far.

### Closing confirmation — the confound tested against zero malicious silos

Requested 2026-08-27 (01_Planning): every data point above supporting
"silos {2,7,9}'s elevated behavior is attack-independent" came from
attack-condition runs, where those silos coexist with actual malicious
silos in the same aggregation rounds. The 3 clean-control runs (no
malicious silo present anywhere in the fleet) are the only place this claim
can be tested with the confound fully isolated from any attack. Read-only,
against `krum_selection.jsonl`/`trim_rate.jsonl` already on disk from the
clean-control runs — no retraining.

**Multi-Krum clean control:** excludes **exactly {2, 7, 9} in all 20 of 20
rounds**, with zero variation — even more consistent than the f=3
attack-condition run (which had one round of {2,7,8} before settling into
{2,7,9} for the remaining 19). This is the same exact trio, produced with
literally no malicious silo anywhere in the fleet.

**Classical Krum clean control:** selects (keeps) only silos **{4, 5}**,
alternating 10/10 across the 20 rounds. Silos {2, 7, 9} are selected
**0/20 rounds** — same as in both attack-condition runs (f=3: only {1,4}
selected, 11/9; f=2: only {4} selected, 20/20). Across all three classical-
Krum conditions (clean, f=3, f=2), {2,7,9} were never once selected — fully
attack-independent.

**FedTrimmedAvg clean control:** per-silo trim rate for {2,7,9} averages
**0.6650** against an ordinary-clean baseline (silos 1,4,6,8) of **0.4924**
— an excess of **+0.1726**. This is within 0.002-0.006 of the excess
measured in BOTH attack-condition runs (f=3: +0.1714; f=2: +0.1787) — the
three numbers are effectively the same value, attack condition or not.

**Verdict: CONFIRMED.** All three strategies show the identical {2,7,9}
elevation with zero malicious silos present, at magnitudes matching their
respective attack-condition runs almost exactly. The confound is
attack-independent — a property of the (alpha=0.5, seed=42) partition and
each defense's geometry, not an artifact of either specific attack
condition. This closes the evidence chain for both the Krum and
trimmed-mean mechanism-level findings above; neither needs to be reopened.

**Additional finding, surfaced by running this check, reported with the
same honesty:** in the FedTrimmedAvg clean control, silos 3 and 5 — NOT
malicious in this run (no attack is present) — show trim rates of 0.7606
and 0.7216 respectively, *higher* than {2,7,9}'s own 0.6650 average. Silos
3 and 5 are the two most extreme-composition silos in the fleet by their
TRUE (pre-attack) label mixture (0.3% and 0.1% Benign respectively, per
`silo_family_composition_a0.5_s42.csv` — these are the same two silos
Phase 0 selected as malicious at f=3 specifically because of this extreme
composition). This indicates the confound on trimmed-mean's mechanism is
broader than "large/Benign-heavy silos" alone: per-coordinate trimming
appears sensitive to compositional distance from the fleet's typical label
mixture **in either direction** (very Benign-heavy silos like {2,7,9} and
very non-Benign-heavy silos like {3,5} both trim-elevated), independent of
attack. Since Phase 0's worst-case-adversary selection criterion
deliberately picks the most attack-family-concentrated silos as malicious,
this means trimmed-mean's malicious-silo trim-rate excess (reported above)
is confounded not only by size but plausibly by the SAME selection
criterion that made these silos attractive as attack targets in the first
place — worth carrying into any future write-up of why this attack's
victim-silo selection interacts with trimmed-mean's mechanism.

## Artifact index (per-run)

Each run directory (`results/federated/{tag}/`) contains: `round_history.json`,
`defense_config.json`, `attack_val_summary.json` (attack conditions) or
`final_metrics.json`+`config.json` (clean conditions), `client_stats.jsonl`,
`silo_metrics.jsonl`, and either `krum_selection.jsonl` (Multi-Krum/classical
Krum) or `trim_rate.jsonl` (FedTrimmedAvg). Tags:
`multikrum_f3_a0.5_s42_poisoned_f3_sudden_silos0-3-5`,
`multikrum_f2_a0.5_s42_poisoned_f2_sudden_silos0-3`, `multikrum_f3_a0.5_s42`
(clean), `trimmedmean_f3_a0.5_s42_poisoned_f3_sudden_silos0-3-5`,
`trimmedmean_f2_a0.5_s42_poisoned_f2_sudden_silos0-3`, `trimmedmean_f3_a0.5_s42`
(clean), `krumclassical_f3_a0.5_s42_poisoned_f3_sudden_silos0-3-5`,
`krumclassical_f2_a0.5_s42_poisoned_f2_sudden_silos0-3`, `krumclassical_f3_a0.5_s42`
(clean). Analysis reproducible via `scripts/phase2_analysis.py`.

## OPEN ITEM FOR 01_PLANNING — compositional-extremity confound is entangled with the attack-selection criterion itself

Flagged 2026-08-27, routed to 01_Planning as a new, higher-priority open
item before Phase 2 is treated as fully finished. Not acted on here —
report only, per scope.

**Phase 0's malicious-silo selection criterion (maximize attack-family
coverage across the worst-case/full-knowledge adversary) and this phase's
confound axis (compositional extremity driving spurious Krum/trimmed-mean
signal) are NOT independent — both select on the same underlying property,
unusual family composition.** Every malicious silo used in this project's
primary and secondary attack configs was chosen partly *because* it is
compositionally extreme: silo 3 (0.3% Benign) and silo 5 (0.1% Benign) are
themselves two of the three most compositionally extreme silos in the
fleet by true label mixture, and Phase 0's selection rule explicitly
maximized attack-family concentration when picking them.

**Consequence:** it is not yet established whether Krum/trimmed-mean's
failure to detect these specific attacks reflects a *general* property of
these defenses against label-flip attacks, or is *entangled* with the
specific worst-case selection rule — i.e., whether it produces attackers
that happen to look like {2,7,9}/{3,5} on the exact axis
(compositional extremity) these mechanisms are already shown to be
sensitive to, independent of any attack. A different attacker-selection
rule (e.g., one that does not correlate malicious-silo choice with
compositional extremity) could plausibly produce a different mechanism-
level result from either defense — untested here.

**This does not change anything already reported.** The diagnostic chain
above is sound for the configs actually tested (both attack conditions'
malicious silos genuinely were never detected, and the confound was
confirmed attack-independent via the clean-control runs). But it bounds
how far that finding can be generalized: it is evidence about Krum/
trimmed-mean against *this project's specific worst-case attacker
selection rule*, not yet evidence about these defenses against label-flip
attacks in general.

**This is a live, unresolved question for Phase 4's design, not settled by
anything in Phase 2.** If Phase 4's rolling-history detection work (or any
future attacker-selection choice) is designed assuming Krum/trimmed-mean
are generally geometry-blind to label-flip attacks, that assumption should
be checked against this entanglement first.

## NOT YET DONE

- Multiple seeds (1337, 2024) per the standing Phase 0 obligation, not yet
  closed out for ANY configuration including the clean FedAvg baseline
- Phase 5's full eval-harness verdict (this document reports the raw
  signatures; verdicting/interpretation is explicitly out of scope here)
- The compositional-extremity/attack-selection entanglement above, pending
  01_Planning resolution before Phase 4 locks its own design

## Artifact index — code

- `federated/xfed_federated/server_app.py` — `LoggingMixin`, `LoggingFedAvg`,
  `_KrumMechanismLogging`, `LoggingMultiKrum`, `LoggingKrum`,
  `LoggingFedTrimmedAvg`, defense-config-driven strategy selection in `main()`
- `configs/defense.yaml` — new, resting state `fedavg` / `0`
- `scripts/phase2_analysis.py` — the 4 statistics, recovery_fraction,
  mechanism-level signatures; reproduces every number in this document
