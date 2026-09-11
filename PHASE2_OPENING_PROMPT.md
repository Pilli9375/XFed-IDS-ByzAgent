PROJECT: XFed-IDS-ByzAgent, Contribution B (ByzAgent). Repo root:
C:\Pilli\Capstone\xfed-ids\. Conda env: xfed. Windows 11, RTX 4050 6GB
VRAM (HARD CEILING). `conda activate` is a no-op in cmd.exe — spawn
PowerShell explicitly.

This is a NEW session with NO memory of prior sessions. Everything below
is restated in full, not referenced. Treat it as ground truth, not as
something to re-derive or re-verify from scratch — but DO verify
schemas/library internals empirically before writing code against any
of them, per standing project rule.

You own CODE ONLY. You do not make research decisions. If you find
yourself about to change scope, alter a locked parameter, or "improve"
the design — STOP and report. Decisions route to 01_Planning.

==========================================================================
READ FIRST, IN FULL, BEFORE ANYTHING ELSE:
  - results/attacks/PHASE0_SUMMARY.md
  - results/monitoring/PHASE1_SUMMARY.md (includes the f=2 {0,3}
    secondary-condition addendum near the end — read that section too,
    not just the original {0,3,5} gate)

These are your primary source of truth for what exists, what's locked,
and what's already measured. Everything below is a condensed restatement
for convenience; the files above are authoritative if anything here ever
looks inconsistent with them.

==========================================================================
GROUND TRUTH — MODEL / DATA (LOCKED):
  - 82 input features, dropout 0.1, LayerNorm (not BatchNorm),
    GradientExplainer (not KernelExplainer/DeepExplainer) — the last of
    these is Phase 3's concern, not Phase 2's, but stays locked regardless
  - 10 silos, 9-class (8 attack families + Benign)
  - macro-F1 is FLOOR-EXCLUDED: Infiltration + Heartbleed reported
    per-class only, excluded from headline macro-F1 (7 families)
  - Model: XFedMLP, [128,64], StandardScaler, effective-number
    class weighting beta=0.999, 3 local epochs, best-by-validation
    checkpoint SELECTION (selection and reporting are DIFFERENT things,
    see the dual-statistic rule below — do not conflate them)
  - ALL parameters in YAML config. No config.py.
  - Validation: existing data/processed/val_mask.parquet. Never build a
    second split.
  - Test set: touched exactly once per configuration, ALREADY SPENT for
    every locked baseline. Phase 0's poisoned runs NEVER touched it
    (hard guard, see below) and Phase 1's work was validation-only
    throughout. Preserve this discipline in Phase 2 as well — no Krum/
    trimmed-mean run should touch test_global.parquet without an
    explicit, separate sign-off; default to the same hard-guard pattern.
  - AUTHORITATIVE FL HARNESS: federated/xfed_federated/ (NOT
    src/federated/ — that tree is unused for ByzAgent; a prior session
    verified src/federated/server_app.py lacks best-by-validation
    checkpoint selection entirely and cannot produce comparable numbers.
    Do not touch src/federated/.)
  - federated/xfed_federated/server_app.py has a HARD, unconditional
    test-evaluation guard when attack.enabled=true in
    configs/attack.yaml: it writes val-only artifacts then RAISES before
    reaching test_global.parquet. This guard is load-bearing. Do not
    weaken, remove, or bypass it under any circumstance.
  - Sequential-GPU note (Phase 1 close-out TODO, binding from here
    onward): before launching any REAL (non-smoke-test) `flwr run`,
    explicitly verify/set `--federation-config` to guarantee sequential
    client execution. The legacy `options.` fields in
    `~/.flwr/config.toml` were observed NOT to carry over automatically
    in this flwr version during Phase 1's smoke test — a silent fallback
    to parallel client execution on a real 20-round/10-silo job risks an
    OOM crash well into the run, not at the start. Confirm before
    launching, not after a crash.

==========================================================================
GROUND TRUTH — PHASE 0 RESULTS (COMPLETE, CLOSED, DO NOT RE-RUN):

Built src/attacks/label_flip.py (vendored into
federated/xfed_federated/_vendored/, re-exported via task.py), a
PoisonedClient wrapper doing TARGETED label-flip (attack-family ->
Benign), two modes (sudden/gradual), wired into
federated/xfed_federated/client_app.py.

LOCKED ATTACK CONFIGS (both closed, both on disk, both PASS):
  PRIMARY:   f=3, malicious_silos=[0,3,5], flip_fraction=0.4,
             mode=sudden, attack_seed=9001, alpha=0.5, seed=42
             tag: fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5
  SECONDARY: f=2, malicious_silos=[0,3], flip_fraction=0.4,
             mode=sudden, attack_seed=9001, alpha=0.5, seed=42
             tag: fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3
  CLEAN BASELINE: results/federated/fedavg_a0.5_s42/ (alpha=0.5, seed=42,
  no attack).

  Both {0,3,5} and {0,3} are WORST-CASE / FULL-KNOWLEDGE ADVERSARIES.
  NEVER present either as a naturalistic attack scenario in any report.

  DUAL-STATISTIC REPORTING — locked ground truth, binding through every
  future phase:
    - MODEL SELECTION remains best-by-validation MAX. Locked, unchanged.
    - Every attack-vs-clean comparison (Phase 2 included, from this
      point forward) must report ALL FOUR of: mean, median, final-5-round
      MEAN, and max of val_macro_f1_headline — never just one. A
      divergence between max and final-5-mean under attack is itself a
      reportable finding.

  Locked numbers, paired same-seed vs. clean_s42 (all four statistics):

  | statistic | clean_s42 | poisoned f=3 {0,3,5} | Δ | poisoned f=2 {0,3} | Δ |
  |---|---|---|---|---|---|
  | mean (all 20 rounds) | 0.8535 | 0.8236 | −0.0299 | 0.8253 | −0.0282 |
  | median (all 20 rounds) | 0.8487 | 0.8438 | −0.0048 | 0.8489 | +0.0003 |
  | **final-5 mean (rounds 16-20)** | **0.9513** | **0.8746** | **−0.0766** | **0.8787** | **−0.0726** |
  | max (best-by-validation) | 0.9760 | 0.9763 | +0.0004 | 0.9867 | +0.0107 |

  f=2 {0,3} is the PRIMARY Krum-margin-clean evidence (de-confounds
  Krum's n≥2f+3 margin — zero margin at f=3, since 9≤10); f=3 {0,3,5} is
  secondary/confirmatory. Both are valid attack conditions to test Krum/
  trimmed-mean against; test BOTH, do not pick just one.

==========================================================================
GROUND TRUTH — PHASE 1 RESULTS (COMPLETE, CLOSED, DO NOT RE-RUN):

Built src/monitoring/client_stats.py (vendored, re-exported via task.py):
5 per-client behavioral stats computed server-side every round, before
aggregation — `update_norm`, `cosine_to_global`, `cosine_to_peer_mean`,
`train_loss`, `val_accuracy`. Wired into federated/xfed_federated/
server_app.py's `LoggingFedAvg` (`configure_train` caches previous-round
global weights; `aggregate_train` computes all 5 stats per client before
calling `super()` unchanged — side channel only, FedAvg's actual result
is untouched). JSONL history buffer (`client_stats.jsonl`, one row per
round/silo), mirroring the existing `silo_metrics.jsonl` convention.
Live wiring confirmed via a 2-round smoke test (10/10 clients, 0
failures, both rounds; hard test-guard fired correctly).

`scripts/replay_client_stats.py` retrospectively computes `client_stats.jsonl`
for any already-completed run from its saved `round_checkpoints/`/
`silo_checkpoints/` — no retraining needed. `scripts/phase1_verification_gate.py`
computes the separation analysis below (now takes `--poisoned-dir`/
`--attack-manifest`/`--out`, reusable for any condition).

**Separation measure, locked and reused for direct comparability:**
Glass's delta, `(mean_malicious − mean_clean) / std_clean`, computed
per round, malicious-silos-vs-rest, in the poisoned run AND in the clean
run (same grouping applied as a control — are these particular silos
just naturally different, independent of any attack?).

**Result — mean |Glass's delta| across all 20 rounds, both tested
conditions, corroborating each other:**

| stat | f=3 {0,3,5} poisoned | f=3 clean-control | f=3 ratio | f=2 {0,3} poisoned | f=2 clean-control | f=2 ratio |
|---|---|---|---|---|---|---|
| **train_loss** | 140.9 | 4.17 | **33.8x** | 51.8 | 0.34 | **154.3x** |
| cosine_to_peer_mean | 1.78 | 1.59 | 1.11x | 1.24 | 1.06 | 1.17x |
| update_norm | 1.32 | 1.19 | 1.12x | 1.18 | 0.71 | 1.67x |
| cosine_to_global | 1.56 | 1.67 | 0.93x | 0.95 | 1.10 | 0.86x |
| val_accuracy | 0.97 | 3.17 | 0.31x | 0.45 | 1.44 | 0.31x |

**Only `train_loss` clearly separates malicious from clean silos, at
BOTH attack strengths independently.** `update_norm`, `cosine_to_global`,
and `cosine_to_peer_mean` — the three WEIGHT-SPACE GEOMETRY stats — show
ratios of 0.86x–1.67x at both f=3 and f=2: statistically indistinguishable
from the natural non-IID silo-to-silo variance already present in the
clean run. `val_accuracy` shows the attack *narrowing* the malicious-vs-
clean gap (ratio 0.31x at both conditions, identically) rather than
widening it — a label-flip-to-Benign attack raises raw accuracy on a
~75%-Benign validation set, the opposite of what a naive detector would
expect.

Sample-count gating on `val_accuracy`: does not apply — same fixed
143,513-row centralized validation set every round, no small client-
local eval set.

**Two findings carried forward as binding ground truth (verbatim from
PHASE1_SUMMARY.md, do not re-litigate):**

(a) `train_loss`'s separation is the EASY case — label-flipping directly
inflates the loss function that produced it, so this validates the
instrumentation pipeline, not that all 5 stats carry independent signal.
The weight-space geometry stats show near-zero separation at BOTH tested
attack strengths under this SUDDEN-mode attack.

(b) VAL_ACCURACY INVERSION is a design hazard: this attack reduces,
not widens, the raw-accuracy gap between malicious and clean clients,
consistently, at both attack strengths. Any future component (Phase 3's
agent, eventually) handed `val_accuracy` without this context could read
a malicious client's accuracy as evidence of trustworthiness — exactly
backwards for this attack family.

==========================================================================
PHASE 2 PRE-REGISTRATION — LOCKED, WRITE THIS DOWN BEFORE BUILDING
ANYTHING, NOT AFTER SEEING RESULTS:

**Krum's expectation.** Krum computes, for each client's update, a score
based on the sum of squared Euclidean distances to its nearest neighbors
among the other clients' updates (in full weight-parameter space), and
selects the update(s) with the lowest score as the ones most "central" /
least anomalous. This is a WEIGHT-SPACE GEOMETRY method: its entire
defense mechanism depends on malicious updates being geometric outliers
in parameter space relative to clean updates.

**Trimmed-mean's expectation — stated explicitly, not left to be
inferred from proximity to the Krum paragraph.** Trimmed-mean operates
coordinate-wise on the weight update itself: for each individual
parameter coordinate, across all clients, it discards the top-k and
bottom-k values at that coordinate before averaging the rest. This is
ALSO a weight-space geometry method — it assumes malicious updates are
coordinate-wise magnitude outliers. It inherits the IDENTICAL dependency
on weight-space separation as Krum, via the identical underlying
mechanism (this attack's signal lives in loss-space, not weight-space),
even though the specific algorithm (per-coordinate trimming vs.
neighbor-distance ranking) differs.

**The pre-registered expectation, for BOTH Krum and trimmed-mean, at
BOTH locked attack conditions (f=3 {0,3,5} and f=2 {0,3}), sudden mode:**
Phase 1 measured the exact weight-space-geometry quantities both defenses
implicitly rely on (`update_norm`, `cosine_to_global`, `cosine_to_peer_mean`)
and found them statistically indistinguishable between malicious and
clean silos (ratios 0.86x–1.67x vs. the clean run's own natural
variance, at both f=3 and f=2). Neither Krum nor trimmed-mean has access
to `train_loss` — the one stat that DID show strong separation
(33.8x–154.3x) — because both operate purely on the received weight
update, never on a client's self-reported training loss. **On this
basis, both Krum and trimmed-mean are expected to fail to reliably
distinguish the malicious silos from the clean ones, at both tested
attack strengths, under this specific attack family (targeted sudden-mode
label-flip-to-Benign).**

**This is a two-sided, falsifiable commitment, for both methods
independently:**
  - If Krum and/or trimmed-mean ALSO fail (as expected): that is
    CORROBORATION of the geometry-blindness hypothesis Phase 1 already
    established, not a second surprise to re-derive from scratch.
  - If either one SUCCEEDS where the geometry stats predicted failure:
    that is a genuine, reportable divergence, worth its own note —
    e.g., Krum's neighbor-distance ranking or trimmed-mean's per-
    coordinate trimming could in principle capture a different geometric
    signature than the specific norm/cosine stats Phase 1 measured, even
    within weight-space. Do not force this into "confirmed the
    hypothesis" if the numbers say otherwise.
  - If Krum and trimmed-mean DIVERGE from EACH OTHER (one fails, one
    succeeds): that is itself a reportable finding — a real difference
    between two geometry-based methods that both nominally rely on the
    same weight-space assumption, worth its own note, not smoothed into
    a single "baselines" verdict.

**"FAILS AS EXPECTED" — OPERATIONAL DEFINITION, LOCKED NOW, BEFORE ANY
COMPARISON CODE IS WRITTEN:**

Both signatures will be measured and reported, as separate things, for
every (attack config, defense method) pair. This is a direct application
of the already-locked dual-statistic-reporting principle (Phase 0: report
all four of mean/median/final-5/max, never just one; a divergence
between statistics is itself a finding) extended to a new instance of
the same situation — two numbers CAN diverge, and if they do, that
divergence is data, not noise to average away. Do not later collapse
this to reporting only one signature because the other one is
inconvenient or because results turned out mixed.

  **(a) OUTCOME-LEVEL signature.** Krum/trimmed-mean's post-aggregation
  performance under attack, reported via the SAME locked dual-statistic
  convention as everything else (mean / median / final-5-mean / max of
  `val_macro_f1_headline`), paired same-seed against both the clean
  baseline and poisoned-FedAvg's own already-measured numbers (table
  above). Primary number: **final-5-mean**, per the locked rationale
  (converged behavior, not early-round noise, not level-shift-blind).

  **Metric: gap-recovery fraction, NOT a flat midpoint** (a fixed
  numeric midpoint between two anchors has no mechanistic meaning and
  doesn't use poisoned-FedAvg as the floor it's meant to be). Paired
  same-seed, on final-5-mean, per attack condition — do not average
  across the two conditions:

  ```
  recovery_fraction = (defense_final5mean - poisoned_FedAvg_final5mean)
                       / (clean_final5mean - poisoned_FedAvg_final5mean)
  ```

  where `poisoned_FedAvg_final5mean` and `clean_final5mean` are the SAME
  seed-42 anchors already on disk, taken separately per condition:
    - f=3 {0,3,5}: clean 0.9513, poisoned-FedAvg 0.8746, gap = 0.0767
    - f=2 {0,3}: clean 0.9513, poisoned-FedAvg 0.8787, gap = 0.0726

  **THRESHOLD: recovery_fraction ≥ 0.5 = succeeds** (recovers at least
  half the gap toward clean). **Below 0.5 = fails as pre-registered.**
  Standard shape for a robustness-recovery threshold, defensible on its
  own terms — not an arbitrary split point chosen because it happened to
  sit between two already-measured numbers.

  **Always report the raw `recovery_fraction`, never just the pass/fail
  label** — a defense at 0.48 and a defense at 0.05 are both "fails"
  under the threshold but are very different results and must not be
  flattened into the same bucket in any table.

  **(b) MECHANISM-LEVEL signature.** Does the defense's own internal
  selection/trimming process preferentially act on the known-malicious
  silos, above the rate chance alone would produce?
    - **Krum:** per round, does Krum's lowest-score selection exclude
      the malicious silo(s) at a rate above chance? Chance baseline =
      the malicious silos' share of all silos (3/10 for f=3, 2/10 for
      f=2) — if Krum's selection carried no information about which
      silos are malicious, malicious silos would be excluded from the
      kept set at exactly this base rate on average. "Succeeds"
      (mechanism-level) = malicious-silo exclusion rate reliably above
      this chance baseline across rounds. "Fails as expected" = exclusion
      rate statistically indistinguishable from chance.
    - **Trimmed-mean:** analogous per-coordinate check — across all
      (coordinate, round) trims, does a malicious silo's value appear
      among the discarded top-k/bottom-k values at a rate above the same
      chance baseline (f/n)? Same succeeds/fails-as-expected framing.
  Log whatever is needed for this to be computable in Phase 5 (which
  silo(s) Krum kept/excluded each round; which silos' values got trimmed
  at which coordinates, or a summary sufficient to reconstruct that rate
  without re-running the whole experiment) — additive logging is Phase 2
  scope; computing and reporting the actual signature-(b) numbers is
  Phase 5's eval-harness job, same division of labor as Phase 0's
  checkpoint-then-replay pattern.

  **These two signatures CAN diverge** (Krum could correctly avoid
  selecting malicious silos most rounds — (b) succeeds — while the
  surviving aggregate still doesn't recover much — (a) fails — or vice
  versa). Report both, explicitly, for every (attack config, defense
  method) pair. A divergence between (a) and (b) is itself a reportable
  finding, not to be resolved into a single verdict.

==========================================================================
SCOPE LOCK — PHASE 2 ONLY. Build nothing else.

Phase 2 = Krum and trimmed-mean baseline aggregation strategies, wired
into the SAME authoritative harness (federated/xfed_federated/), run
against BOTH locked attack conditions (f=3 {0,3,5}, f=2 {0,3}) plus the
clean baseline, with sufficient additive logging for Phase 5 to later
compute both failure signatures without re-running anything.

OUT OF SCOPE, DO NOT BUILD: the LLM agent (Phase 3), rolling-history
feeding (Phase 4), the eval harness that computes and verdicts the two
failure signatures end-to-end (Phase 5 — Phase 2 only needs to log
enough for this to be possible later), the dashboard (Phase 6). Also
permanently rejected, same as Phase 0/1: causal discovery, multi-attack-
type classification, confidence-based human-in-loop, attack types beyond
label-flip.

==========================================================================
STEP 1 — VERIFY SCHEMAS/LIBRARY INTERNALS EMPIRICALLY BEFORE WRITING ANY
CODE. Read-only where possible.

A prior session found, while exploring the installed flwr package for
Phase 1's `configure_train`/`aggregate_train` wiring, that
`flwr.serverapp.strategy` ALREADY SHIPS `krum.py`, `multikrum.py`, and
`fedtrimmedavg.py` alongside `fedavg.py`. This was NOT verified in depth
(Phase 1 only needed FedAvg) — confirm empirically, before writing
anything:
  - Do these library implementations match the textbook Krum/trimmed-
    mean formulations this pre-registration assumes (Euclidean distance
    in full weight-parameter space for Krum; per-coordinate top-k/bottom-k
    trimming for trimmed-mean)? Read the actual source, don't assume from
    the filename.
  - What are their constructor parameters (Krum's `f` / number to select;
    trimmed-mean's `beta`/trim fraction or count)? Do they expose
    per-round selection/trim information in a way that can be captured
    via the same side-channel-subclass pattern `LoggingFedAvg` already
    uses (override the relevant aggregate method, log, call `super()`
    unchanged)? Or do they need to be reimplemented to get that logging?
  - Confirm whether reusing these library strategies changes any part of
    the byte-for-byte-preservation discipline the LoggingFedAvg pattern
    established for FedAvg — the actual aggregation result must not be
    altered by adding a logging side channel.
  - Confirm the hard test-guard in server_app.py (attack.enabled=true →
    stop before test_global.parquet) is strategy-agnostic and will fire
    correctly regardless of which Strategy subclass is used.

Report findings and a build plan. Wait for go before writing the Krum/
trimmed-mean wiring.

==========================================================================
REPORT-BACK FORMAT — every stopping point:

Done:
Numbers:
Decided:
Blocked-unsure:
Next:

Be brutally honest in "Blocked-unsure." I have to defend all of this
orally. Tell me what isn't done, not what looks done.

Start with STEP 1. Read-only where possible. Report and wait.
