# ByzAgent Phase 4 — Rolling-History Detection — Summary

**Status: CLOSED. Negative result, exactly as pre-registered before any
Step 3 data existed.** Rolling-history stat presentation (N=5-round trend
per stat, replacing Phase 3's current-round scalar) does **not** separate
temporal attack onset from static compositional atypicality. This is
reported as a pre-registered, legitimate negative result, not a failure —
the interpretation rule that produced this verdict was written and locked
*before* Step 3 ran (see "Pre-registered interpretation," Step 1 gate
exchange), specifically so the framing could not be chosen after seeing
where the numbers landed. This closes the ByzAgent single-round /
rolling-history detection track. Phase 5 (eval harness) is NOT started.

## Headline, in one paragraph

Phase 3 found ByzAgent's malicious-silo flag rate was confounded by
compositional extremity, not attack behavior (a never-malicious silo, 8,
flagged at the same 0.95–1.00 rate as the real attackers). Phase 4 tested
whether feeding the agent each client's own 5-round trend, instead of a
single current-round scalar, could separate "always unusual" from
"recently turned." It does not. Two of three malicious silos (3, 5) are
flagged at a saturated 1.00 in **every** cell tested — clean, sudden,
gradual, both agent modes — zero lift, zero information. The third (silo 0)
does show a larger lift under rolling-history (+0.15 sudden, +0.45 gradual,
vs current-round's +0.05/+0.05) — but the never-malicious canary (silo 8)
shows an equal-or-larger lift under the identical conditions (+0.60 sudden,
+0.45 gradual), which is exactly the pre-registered failure condition. A
follow-up diagnostic further found that rolling-history mode's decisions
are far less correlated with the stats that mattered most in Phase 3
(cosine_to_global's |ρ| fell from 0.78 to 0.21; train_loss from 0.75 to
0.21; val_accuracy from 0.73 to 0.23) and that the model's own trend
characterizations ("increasing," "decreasing," "stable") are factually
wrong against the sequences it was given 45% of the time — direct evidence
that at least part of the negative result is this model reasoning worse
over a denser prompt, a distinct claim from "rolling history as an
approach doesn't work," and the two are now told apart with numbers rather
than left entangled.

## Step 1 — gradual-mode attack gate

Gradual mode had never been run before this phase. Verified read-only
first, then run once.

**Ramp schedule, as implemented** ([label_flip.py](../../src/attacks/label_flip.py),
`compute_flip_fraction`): `flip_fraction(round) = min(start_fraction +
increment_per_round × (round − 1), max_fraction)`, recomputed fresh every
round. Config ([attack.yaml](../../configs/attack.yaml)):
`start_fraction=0.05, increment_per_round=0.05, max_fraction=1.0`. Over 20
rounds this is a genuine linear ramp — 0.05, 0.10, ..., 0.95, 1.00 — cap
reached exactly on the final round, not before. `flip_log.csv` confirmed
the measured flip fraction matched the configured schedule exactly, every
round, for all three malicious silos — no discrepancy, same clean linear
scaling Phase 0 found for sudden mode.

**One live run**: plain FedAvg, no defense, {0,3,5}, alpha=0.5, seed=42, 20
rounds, attack_seed=9001. Hard test-guard fired correctly (deliberate stop,
not a crash — validation-only artifacts written, `test_global.parquet`
never touched).

**All four statistics, paired same-seed vs. clean_s42:**

| statistic | clean_s42 | sudden {0,3,5} | Δ | gradual {0,3,5} | Δ |
|---|---|---|---|---|---|
| mean (20 rounds) | 0.8535 | 0.8236 | −0.0299 | 0.7958 | −0.0577 |
| median | 0.8487 | 0.8438 | −0.0048 | 0.7993 | −0.0494 |
| final-5 mean (rounds 16-20) | 0.9513 | 0.8746 | −0.0766 | 0.8104 | −0.1408 |
| max (best-by-validation) | 0.9760 | 0.9763 | +0.0004 | 0.9758 | −0.0002 |

**MANDATORY CAVEAT, carries into every table above and any future
reference to these numbers**: gradual mode's final-5 window (rounds
16-20) sits at flip_fraction 0.80–1.00 — 2–2.5× **stronger** than sudden
mode's constant 0.40. Gradual's larger final-5/mean/median deltas
therefore reflect a **stronger attack in that window**, not greater
detection difficulty. These four statistics are not a fair
detectability comparison between gradual and sudden mode; they establish
only that the gradual attack has a genuine, non-trivial effect by the end
of the run.

**Pre-registered strength-matched window: rounds 1-8.** Gradual reaches
sudden's constant 0.40 flip_fraction exactly at round 8; before that,
gradual is a strictly weaker attack than sudden ever ran. This is the
**only** regime where "does slow onset get missed by single-round methods
but caught by trends" is a fair question, and is the window Step 3's
rounds-to-detection metric is evaluated against. Per-round val_macro_f1
delta in this window (gradual − clean) is small and non-monotonic (−0.001
to −0.041) — no clean separation from round-to-round noise at the
macro-F1 level alone, which is exactly why the behavioral-stat trajectory
(not macro-F1) is the right place to look for early separation, and why
this phase exists.

## Step 2 — rolling-history build

Extended [`src/agents/byz_agent.py`](../../src/agents/byz_agent.py):
`build_client_history()` (pure window-slicing function over
`client_stats.jsonl`-shaped rows), `build_prompt_history()` /
`PROMPT_TEMPLATE_HISTORY`, `decide_round_history()`. `decide_round()` /
`build_prompt()` / `PROMPT_TEMPLATE` are byte-for-byte unchanged — the
current-round path selectable via
[`configs/agent.yaml`](../../configs/agent.yaml)'s new `agent.history: {mode:
current_round | rolling_history, window: 5}` block, resting state
`current_round` (Phase 3 behavior, unchanged by default).

**Partial-window handling (explicit, not silent)**: round *r* gets
`min(window, r)` real rows per client — never padded with a fabricated
value, never skipped. `window_size` is disclosed in the prompt itself
("last *k* rounds, oldest to newest") so the agent is never told "last 5
rounds" while seeing fewer numbers. Verified via a no-LLM pure-function
check (window sizes 1/3/5 at rounds 1/3/8, exact sequence content
cross-checked against raw rows) and a live 2-round smoke test (`f=0`, zero
real flips): 20/20 decisions valid, `window_size`=1 at round 1, =2 at
round 2, explanations genuinely referencing the sequence ("update_norm has
decreased over the last two rounds (4.00 to 3.08)...").

Two changes beyond a literal scalar→sequence swap, both mechanically
required and both flagged before use: the prompt's intro sentence had to
change (the original "computed for the current round only" would
otherwise describe the client block inaccurately) and each client's block
became multi-line (5 sequences don't fit legibly on one comma-joined
line). Everything else — 5 stat definitions, the val_accuracy Benign-skew
caveat (verbatim), citation instruction, JSON schema, trust/downweight/
quarantine semantics and weights — is untouched.

## Step 3 — 6-cell verification matrix

3 conditions (clean, sudden {0,3,5}, gradual {0,3,5}) × 2 agent modes
(current_round, rolling_history N=5), all rounds, retrospective replay
against `client_stats.jsonl` already on disk — no retraining. 138 live
Ollama calls (120 base + 18 decision-variance), 129.2 min.
[`scripts/phase4_verification_gate.py`](../../scripts/phase4_verification_gate.py) /
[`scripts/phase4_analysis.py`](../../scripts/phase4_analysis.py).

**Regression check, free**: current-round mode's replay closely reproduces
Phase 3's on-disk numbers (clean silo 0 = 0.95 exact match; sudden silo 0 =
1.00 exact match; silos 3/5 = 1.00 exact match in every condition tested;
canary silo 8 clean = 0.90 vs Phase 3's 0.95 — close, not identical, as
expected at temperature=0.2, not a code regression).

### Per-silo flag rate table (not aggregated malicious-vs-clean)

| silo | clean·cur | clean·hist | sudden·cur | sudden·hist | gradual·cur | gradual·hist |
|---|---|---|---|---|---|---|
| 0 | 0.95 | **0.00** | 1.00 | 0.15 | 1.00 | 0.45 |
| 1 | 0.05 | 0.45 | 0.00 | 0.30 | 0.10 | 0.10 |
| 2 | 0.25 | 0.75 | 0.05 | 0.80 | 0.10 | 0.70 |
| **3** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| 4 | 0.00 | 0.05 | 0.00 | 0.15 | 0.00 | 0.05 |
| **5** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| 6 | 0.00 | 0.00 | 0.00 | 0.10 | 0.05 | 0.00 |
| 7 | 0.05 | 0.50 | 0.00 | 0.50 | 0.15 | 0.35 |
| **8 (canary)** | **0.90** | **0.35** | **1.00** | **0.95** | **1.00** | **0.80** |
| 9 | 0.05 | 0.15 | 0.00 | 0.10 | 0.05 | 0.10 |

### Lift over clean baseline — the only defensible detection measure

| silo | condition | current_round lift | rolling_history lift |
|---|---|---|---|
| 0 | sudden | +0.0500 | **+0.1500** |
| 3 | sudden | +0.0000 | +0.0000 |
| 5 | sudden | +0.0000 | +0.0000 |
| 0 | gradual | +0.0500 | **+0.4500** |
| 3 | gradual | +0.0000 | +0.0000 |
| 5 | gradual | +0.0000 | +0.0000 |
| **8 (canary, never malicious)** | sudden | +0.10 | **+0.60** |
| **8 (canary, never malicious)** | gradual | +0.10 | **+0.45** |

**The canary's rolling-history lift (+0.60 sudden, +0.45 gradual) equals
or exceeds every real malicious silo's rolling-history lift.**
Rolling-history didn't just fail to fix the compositional-extremity
confound Phase 3 found — for the canary specifically, it produced a larger
false attack-response than current-round mode ever did (+0.60/+0.45 vs
+0.10/+0.10).

### Rounds-to-detection, gradual, pre-registered rounds-1-8 window

| mode | silo 0 | silo 3 | silo 5 |
|---|---|---|---|
| current_round | round 1 | round 1 | round 1 |
| rolling_history | round 2 | round 1 | round 1 |

**The bare first-flagged-round number is misleading on its own** — full
per-round sequences (round 1→20, t=trust/d=downweight/q=quarantine):

- current_round silo 0: `ddddqddqqqdddddddddq` — flagged **every single
  round**, attack or not (matches its 1.00 flat rate; "round 1 detection"
  is the saturated confound firing, not attack-responsive detection).
- rolling_history silo 0: `tdttttddttddtddtttdd` — round 2's flag is an
  **isolated single-round blip**; rounds 3-6 revert to trust; the first
  *sustained* (back-to-back) flag is rounds 7-8, at the very edge of the
  locked window.
- rolling_history silos 3/5: `ddddddddddqdqddddqdq` / `dddddddddqdddddddqdq`
  — flagged essentially every round, same saturated-confound pattern as
  current-round mode.
- rolling_history canary (silo 8, gradual): `ddddddttttdddddddddq` —
  flagged in 6 of the first 8 rounds, **indistinguishable in timing from
  the real attackers.**

### Decision-variance stability (round 10, 3× independent calls)

| cell | exact-match | trust/flagged-boundary |
|---|---|---|
| clean · current_round | 10/10 (1.00) | 10/10 (1.00) |
| clean · rolling_history | 6/10 (0.60) | 8/10 (0.80) |
| sudden · current_round | 8/10 (0.80) | 10/10 (1.00) |
| sudden · rolling_history | **4/10 (0.40)** | 7/10 (0.70) |
| gradual · current_round | 6/10 (0.60) | 10/10 (1.00) |
| gradual · rolling_history | 8/10 (0.80) | 8/10 (0.80) |

Every current-round cell has 100% boundary stability (matches Phase 3:
no trust↔flagged crossings on identical input). Rolling-history's boundary
stability regresses to 70-80% — a real stability degradation, not present
in Phase 3's original current-round result.

### Early-rounds informativeness proxy (ordinary-clean FP rate, clean condition, silos {1,2,4,6,7,9})

- current_round, rounds 1-20: `0.17 0.17 0.50 0.00 0.17 0.17 0.00 0.00 | 0.00 0.00 0.00 0.00 0.17 0.00 0.00 0.00 0.00 0.00 0.00 0.00` — noisy rounds 1-3, **settles to ~0.00 from round 4 onward**.
- rolling_history, rounds 1-20: `0.67 0.17 0.33 0.67 0.67 0.33 0.17 0.33 | 0.33 0.17 0.17 0.17 0.33 0.50 0.33 0.33 0.00 0.33 0.17 0.17` — **never settles**. Window-fill at round 5 produces no inflection point; rounds 5-8 are among the noisiest, round 14 still hits 0.50.

## Pre-registered verdict, applied mechanically

Locked before Step 3 ran: *"If rolling-history's lift over clean baseline
is comparable to current-round-only's (i.e. both near zero), or if silo 8
rises alongside the malicious silos → rolling history does NOT separate
them, and the Phase 3 structural finding extends to the temporal case."*

Silos 3/5: lift is 0.00 in both modes, both attack conditions — comparable,
both near zero. Silo 0: rolling-history's larger lift (+0.15/+0.45)
satisfies the positive branch's first clause alone, but the positive
branch requires **both** "a lift current-round doesn't show" **and** "silo
8 does not rise correspondingly" — silo 8's lift (+0.60/+0.45) equals or
exceeds silo 0's own, so the conjunction fails. **Verdict: negative
branch, confirmed.** Rolling history does not separate temporal attack
onset from static compositional atypicality. Phase 3's structural finding
— single-round (and now, rolling-window) behavioral-statistic detection
cannot distinguish "is attacking" from "is unusual" in this partition,
because the silos worth attacking are exactly the unusual ones — extends
to the temporal case.

## Closing diagnostic — why rolling-history got worse, not just neutral

Three independent signals in Step 3 pointed the same direction: several
ordinary-clean silos' baseline flag rate rose under rolling-history with
**zero attack present** (silo 1: 0.05→0.45; silo 2: 0.25→0.75; silo 7:
0.05→0.50), the early-rounds informativeness proxy never settled across 20
rounds where current-round drops to ~0.00 by round 4, and decision-variance
boundary stability regressed 100%→70-80%. This motivated one closing,
report-only diagnostic (no prompt tuning performed or planned in response)
to separate two entangled claims: **(A)** rolling history as an approach
fails to separate composition from attack — already confirmed above, does
not change — versus **(B)** this specific agent's reasoning degrades over
the denser, sequence-formatted prompt, a claim about the model, not the
method.
[`scripts/phase4_diagnostic_reasoning_audit.py`](../../scripts/phase4_diagnostic_reasoning_audit.py),
reusing Phase 3's exact citation-accuracy/frequency/correlation methodology
against the same Step 3 data, plus one new check specific to sequences.

### (a) Citation accuracy (loose / strict, pooled clean+sudden+gradual, this replay)

| mode | n citations | loose error | strict error (excl. ambiguous) |
|---|---|---|---|
| current_round (this replay) | 1417 | 17.93% | 14.13% |
| rolling_history | 200 | 23.00% | 16.77% |
| *(Phase 3 published, different condition set — see caveat below)* | — | — | 11.7% |

Modest degradation (+2.6pp strict vs this replay's own current-round
column), not a collapse. Per-stat is mixed, not uniform: update_norm's
accuracy *improved* under rolling-history (27.68%→6.45% strict error)
while cosine_to_global (5.21%→22.73%) and train_loss (10.71%→29.41%) got
markedly worse. Caveat: rolling-history's citation count (200) is much
lower than current-round's (1417) for the same 600 explanations each —
the model shifted its citation *style* toward trend language rather than
"high/low + value" phrasing when given sequences, which check (d) below
was built specifically to audit. Phase 3's published 11.7% was computed
over {clean, f3_{0,3,5}, f2_{0,3}}, not {clean, sudden_{0,3,5},
gradual_{0,3,5}} — not an identical condition set, flagged rather than
treated as directly comparable.

### (c) Decision-stat correlation (Spearman ρ, decision severity vs. within-round percentile) — the clearest signal

| stat | current_round (this replay) | rolling_history | Phase 3 published |
|---|---|---|---|
| cosine_to_global | **−0.7789** | **−0.2091** | −0.808 |
| train_loss | **+0.7510** | **+0.2105** | +0.793 |
| val_accuracy | **−0.7265** | **−0.2250** | −0.745 |
| update_norm | +0.3998 | +0.4893 | +0.419 |
| cosine_to_peer_mean | +0.2686 | +0.2535 | +0.298 |

This replay's current-round column reproduces Phase 3's published
correlations closely (within 0.02-0.04 on every stat — further confirming
no code regression). Under rolling-history, the three stats that were
**strongest** in both Phase 3 and this replay's own current-round column
collapse by 60-72% in magnitude (cosine_to_global 0.78→0.21, train_loss
0.75→0.21, val_accuracy 0.73→0.23), while the two stats that were always
**weakest** stay essentially unchanged (update_norm 0.40→0.49,
cosine_to_peer_mean 0.27→0.25). Rolling-history decisions are far less
coherently tied to any individual stat's value than current-round
decisions are — a direct, quantified sign the agent's reasoning process
does not carry over cleanly to the sequence-formatted prompt.

### (d) Trend-language factual-consistency check (rolling_history only, new)

Method: for each stat a rolling-history explanation describes with a trend
word (increasing/decreasing/stable-family) within 90 characters, compare
the cited direction against the actual direction computed from the
sequence itself (endpoint comparison, 5%-relative-tolerance for "stable" —
documented as a simple rule, not a regression fit).

| stat | n trend claims | error rate |
|---|---|---|
| update_norm | 335 | 32.24% |
| cosine_to_global | 223 | 56.05% |
| cosine_to_peer_mean | 96 | 60.42% |
| **train_loss** | 67 | **62.69%** |
| val_accuracy | 199 | 40.70% |
| **overall** | **920** | **45.00%** |

Nearly half of all trend characterizations the model volunteers are
factually wrong against the sequence it was just given — worst for
train_loss (62.69% wrong) and cosine_to_peer_mean (60.42%), best for
update_norm (32.24%, consistent with (a) and (c) both showing update_norm
held up better than the other stats under rolling-history). Zero claims
were made at `window_size < 2` (no spurious early-round trend
hallucination observed) — every error is a genuine sequence
misreading, not a claim made from insufficient data.

### Reading (a)+(c)+(d) together

(c) and (d) point the same direction with real magnitude: the model's
decisions decouple from the stats that mattered most (c), and its
explicit trend claims about those same sequences are wrong close to half
the time (d). This is independent, quantified evidence for **claim (B)**
— this agent (llama3.1:8b-instruct-q4_K_M) reasons measurably worse over
the denser, sequence-formatted prompt — **distinct from claim (A)**, which
was already settled by the lift/canary analysis above and does not change.
Both are true simultaneously: rolling history does not separate
composition from attack in this partition (A, structural/method-level,
confirmed), and this specific agent's reasoning coherence measurably
degrades under the sequence prompt on top of that (B, model-level,
newly evidenced) — a different model or prompt design might change (B)
without rescuing (A), since (A)'s failure mode (the canary rising as much
as the real attacker) is present even where the agent's citations are
accurate.

## What was NOT run, and why

- **Krum/trimmed-mean under gradual mode**: explicitly not run. 01_Planning
  judged that with ByzAgent already failing to detect above its own
  confound baseline, a baseline comparison number could not change the
  verdict — two ~25-30 min live runs were skipped rather than spent on a
  number that couldn't move the result.
- **Prompt tuning in response to the diagnostic**: explicitly not done.
  Report only, per instruction — whatever the diagnostic found, the Step 3
  verdict does not change; it only determines how the negative result is
  worded.
- Multiple seeds (1337, 2024) — standing Phase 0 obligation, still not
  closed for any configuration.

## Repo-state confirmation

`configs/attack.yaml` (`dff0d8a7f2eaaf8ea25b5dbbe1d2c3ce`) and
`configs/defense.yaml` (`4104840815148b19e8c47ee7379e3c16`) match their
locked pre-phase checksums exactly — verified after every live run in this
phase (Step 1's gradual run, Step 2's smoke test), never left mid-edit.
`configs/agent.yaml` carries a new checksum
(`d5b88a14858858437c8a4cb4d977e23a`) by design — the `agent.history` block
is the new permanent resting state (`mode: current_round`, reproducing
Phase 3 byte-for-byte by default), the same kind of additive, disclosed
change Phase 2 made to `defense.yaml` when `byzagent` was added as an
option. All Step 3/diagnostic work was read-only replay against existing
`client_stats.jsonl` — no config edits, no retraining, no test-set touch.

## Artifact index

- `src/agents/byz_agent.py` (canonical) / `federated/xfed_federated/_vendored/byz_agent.py` (vendored) — `build_client_history`, `build_prompt_history`, `PROMPT_TEMPLATE_HISTORY`, `decide_round_history`, `AgentConfig.history_mode`/`history_window`
- `configs/agent.yaml` — new `agent.history` block, resting `current_round`
- `federated/xfed_federated/{server_app.py,task.py}` — `LoggingByzAgent` history-mode branching, `agent_config.json` provenance
- `scripts/phase4_verification_gate.py` — 6-cell replay harness
- `scripts/phase4_analysis.py` — per-silo flag rates, lift, canary, rounds-to-detection, variance
- `scripts/phase4_diagnostic_reasoning_audit.py` — closing (a)/(c)/(d) diagnostic
- `results/attacks/a0.5_s42_f3_gradual_silos0-3-5/flip_log.csv` — gradual attack audit log
- `results/federated/fedavg_a0.5_s42_poisoned_f3_gradual_silos0-3-5/` — gradual run artifacts (validation-only, guard-stopped)
- `results/federated/{clean,sudden,gradual}/agent_decisions_phase4_{current_round,rolling_history}.jsonl` — 6-cell replay decision logs (never overwrote Phase 3's original `agent_decisions.jsonl`)
- `results/inspection/attack_gate_a0.5_s42_f3_gradual_silos0-3-5.log` — Step 1 run log
- `results/inspection/phase4_step2_smoke_rolling_history.log` — Step 2 smoke-test log
- `results/inspection/phase4_gate_raw_a0.5_s42.json` — full 6-cell replay data (138 calls)
- `results/inspection/phase4_gate_analysis_a0.5_s42.json` — per-silo/lift/canary/rounds-to-detection/variance numbers
- `results/inspection/phase4_diagnostic_reasoning_audit.json` — citation accuracy/frequency, correlation, trend-language check
