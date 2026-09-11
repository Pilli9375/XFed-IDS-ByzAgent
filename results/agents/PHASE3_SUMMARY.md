# ByzAgent Phase 3 — LLM-Based Trust Agent — Summary

**Status: BUILT, LIVE-WIRED, AND VERIFIED AGAINST REAL DATA (Steps 1–3b
complete). Phase 3 is CLOSED on the numbers below plus the structural
finding in "Compositionally-matched attacks are not constructible in
this partition." Step 3c (live outcome-level re-run) will NOT be run —
see that section.** Phase 4 (rolling history) and Phase 5 (eval harness)
are NOT started. This document reports numbers per the project's
standing "report rather than interpret" instruction; verdicting routes to
01_Planning.

## FORWARD-REFERENCE — READ THIS TOO, NOT JUST THE CAVEAT BELOW

**`results/agents/MULTISEED_VALIDATION_SUMMARY.md` (multi-seed validation session, seeds 1337/2024) BOUNDS the headline caveat immediately below — it does not retract it, but it changes what can be concluded from it.** That session found the seed-42 "malicious silos show ~zero lift" result was partly a **ceiling effect**: at seed 42, all three malicious silos already sat at 0.95–1.00 in the CLEAN run, mathematically capping how much further their flag rate could rise under attack. At seeds 1337 and 2024, where malicious silos mostly are *not* pre-saturated, the same agent shows real, substantial attack-responsive lift (silo 5: +0.95 at 1337, +0.75 at 2024; silo 3: +0.40 at 1337) — behavior seed 42 was structurally incapable of showing, whether or not the agent would have produced it there too. **Read this document's HEADLINE CAVEAT below as an accurate description of seed 42 specifically, not as "ByzAgent detects compositional extremity, not attacks" as a general claim** — the corrected, project-wide version of that claim is stated in full in `MULTISEED_VALIDATION_SUMMARY.md`'s "THE CEILING EFFECT" section. Do not cite the paragraph below in isolation.

## HEADLINE CAVEAT — READ THIS BEFORE ANY OTHER NUMBER IN THIS DOCUMENT

**ByzAgent's malicious-silo flag rate of 1.00 (vs. Krum's 0.0000, Phase 2)
is CONFOUNDED by compositional extremity and must never be quoted alone.**
Checked directly (§3, "compositional-extremity confound"), not assumed
away: the same three malicious silos ({0,3,5}) are flagged at 0.95–1.00
under a **clean, no-attack control** using the identical stats pipeline —
essentially the same rate as under real attack (+0.05/+0.00/+0.00 over
their own no-attack baseline). A fourth silo (8), **never malicious in any
condition tested**, is flagged at the same 0.95–1.00 rate throughout. All
four are the four lowest-Benign-share silos in the fleet (9.2%/0.3%/0.1%/
12.3% Benign, vs. 81.5–98.0% for every other silo). ByzAgent's geometry-
reliant reasoning (see §3c) is substantially tracking **compositional
extremity**, not attack behavior — it correlates with the locked
malicious-silo selection only because Phase 0's worst-case-adversary rule
selects on the same axis (attack-family concentration = low Benign
share). This is the same confound Phase 2 found for Krum/trimmed-mean
(PHASE2_SUMMARY.md, "OPEN ITEM FOR 01_PLANNING"), now shown to extend to
ByzAgent's own decision mechanism. This is not a fixable-by-reselection
scope limitation — see "Compositionally-matched attacks are not
constructible in this partition" below, which demonstrates the confound
is structural to the dataset under Dirichlet partitioning, not an
artifact of one attacker-selection run.

**IMPORTANT — this paragraph describes seed 42 correctly, but the "+0.05/+0.00/+0.00" lift numbers above are now known (see the forward-reference above `results/agents/MULTISEED_VALIDATION_SUMMARY.md`) to be partly a ceiling effect: all three malicious silos were already at 0.95–1.00 in the clean run, leaving mathematically little room for lift regardless of the agent's actual attack-responsiveness. Do not read this paragraph as showing the agent generally fails to respond to attack behavior — at seeds where the ceiling is absent, it does.**

## What was built

- [`src/agents/byz_agent.py`](../../src/agents/byz_agent.py) (canonical) /
  `federated/xfed_federated/_vendored/byz_agent.py` (vendored) — the
  locked prompt, exact JSON schema (enforced via Ollama's `format` field,
  not manual retry-parsing), `decide_round()` (one batched call per round,
  current-round stats only), `decisions_to_weights()`, `log_decisions()`.
  Fails loudly (`AgentResponseError`) after 1 retry on a malformed
  response — never silently defaults a corrupted round.
- [`configs/agent.yaml`](../../configs/agent.yaml) — new, mirrors
  `attack.yaml`/`defense.yaml`'s separate-file convention.
- `federated/xfed_federated/server_app.py` — new `LoggingByzAgent`
  strategy, selected via `configs/defense.yaml: strategy: byzagent`.
- One additive change to already-verified Phase 1 code:
  `ClientStatsRecorder.finalize_round()` now returns the row dicts it
  writes (previously returned `None`) — same file writes, same 5 stat
  definitions, zero behavior change for existing callers. Applied
  identically to the canonical and vendored copies.
- `scripts/phase3_verification_gate.py` (20-round × 3-condition
  retrospective replay + decision-variance check), `scripts/
  phase3_analysis.py` (all metrics below), `scripts/
  phase3_compositional_check.py` (the confound diagnostic).

## Step 1 — model selection (empirical, not assumed)

Three candidates pulled and tested: `llama3.1:8b-instruct-q4_K_M`,
`qwen2.5:7b-instruct-q4_K_M`, `phi3.5:latest` (the literal
`phi3.5:3.8b-instruct-q4_K_M` tag does not exist on the registry;
substituted the default tag, Q4_0 not Q4_K_M — noted, did not change the
outcome).

**VRAM (1b):** all 3 fit the 6GB ceiling with margin (3.7–4.8GB
resident). `keep_alive: 0` confirmed empirically (nvidia-smi + `ollama
ps` before/after, not assumed from docs) to unload each model back to
baseline (~688MiB) within 3–8s — this is why `AgentConfig.keep_alive`
defaults to `0` and every live call in this project uses it, so nothing
stays resident in VRAM during a training round.

**Structured-output reliability (1c), 22 synthetic cases × 3 models:**

| model | JSON parse | id-coverage | explanations citing actual numbers |
|---|---|---|---|
| **llama3.1:8b-instruct-q4_K_M** | 100% | 100% | **65.1%** (84/129) |
| qwen2.5:7b-instruct-q4_K_M | 100% | 100% | 0.8% (1/129) |
| phi3.5:latest | 100% | **59.1%** (disqualifying) | 0% |

llama3.1:8b-instruct-q4_K_M selected: only candidate combining perfect
JSON/id-coverage with explanations that cite real numbers rather than
qualitative-only reasoning; phi3.5 additionally corrupted client_id
values in 9/22 rounds (e.g. `org_3` → `orgs_3`), disqualifying on
reliability grounds alone regardless of its smaller VRAM footprint.
Direct Ollama HTTP call chosen over LangChain — the raw `format=<schema>`
mechanism already gave 100% valid JSON with zero framework needed.

**Prompt-iteration check (pre-Step-2):** adding "cite the specific
numeric value(s) that informed this decision" to the prompt raised the
grounded-explanation rate to **91.6%** (65/71) on a 12-case held-out
synthetic subset, with JSON/id-coverage unaffected. Kept; not iterated
further against synthetic data (01_Planning's explicit instruction — the
real gate is 3a/3b against actual data, not further synthetic tuning).

## Step 2 — build, live-wired, smoke-tested

**Prompt contents (locked):** one-sentence definitions of all 5 Phase 1
stats; the val_accuracy Benign-skew caveat, worded to match 01_Planning's
exact specification — *"this specific attack biases val_accuracy upward
for malicious clients on this Benign-heavy validation set — do not read
high val_accuracy alone as evidence of trustworthiness"*; a brief,
non-specific description of Byzantine/label-flipping behavior; the
citation instruction. **Never included:** any hint that train_loss is
the strongest signal or that the geometry stats show near-null
separation in prior phases; ground-truth malicious-silo identity in any
form; oracle f (the true attack strength) — unlike Multi-Krum/Krum/
trimmed-mean (Phase 2), which are all given the true `num_malicious_nodes`
as a documented advantage, ByzAgent receives none of this. This asymmetry
is written into `agent_config.json` on every run, verbatim, so it cannot
be omitted from a downstream comparison.

> **Correction (2026-09-06, added during the Phase 6 dashboard build):**
> the claim above is wrong as stated. `agent_config.json` does not exist
> anywhere in this repository — checked repo-wide (`find . -iname
> agent_config.json`, zero results) before writing this note. No run,
> past or present, ever produced this file. This is a documentation-vs-
> reality discrepancy in what was otherwise a closed phase summary; it
> is being disclosed rather than quietly fixed. **It changes no result**
> — the underlying fact (ByzAgent was never given oracle `f` or
> malicious-silo identity, per the locked prompt in
> `src/agents/byz_agent.py`) is independently true and correctly
> documented in prose, here and in `docs/contribution_b_results.md`; only
> the claim that it was *also* written to a JSON artifact is false. The
> file is deliberately **not** being created now — generating it at this
> point would backdate a claim into truth, which is worse than leaving
> the discrepancy visible.

**cosine_to_global counterfactual-aggregate methodology (structural
design choice, documented per 01_Planning's explicit instruction not to
bury it):** Phase 1 defines `cosine_to_global` as cosine similarity to
*this round's actual aggregated update* (`src/monitoring/client_stats.py`).
That definition is circular for a strategy that must decide aggregation
weights *before* the aggregate exists. `LoggingByzAgent.aggregate_train`
resolves this by computing a **diagnostic probe aggregate** — a plain,
un-adjusted FedAvg weighted mean, via `FedAvg.aggregate_train()` called
directly (not through `LoggingMixin`, to avoid double-logging) — used
*solely* to feed `ClientStatsRecorder.finalize_round()` the same
`cosine_to_global` definition Phase 1 used, so `client_stats.jsonl` stays
semantically continuous with the Phase 0–2 runs already on disk for
Phase 4's rolling-history read. **The probe aggregate is never shipped as
the round's actual global model.** Once ByzAgent's decisions return, a
*separate* weighted mean (`decisions_to_weights`: trust=1.0×,
downweight=0.3×, quarantine=0×, by sample count) is computed from the
same replies and returned instead. Consequence, stated explicitly per
01_Planning: **under ByzAgent, `cosine_to_global` is computed against a
counterfactual unadjusted-FedAvg aggregate, not against the model
ByzAgent actually ships this round; this differs subtly from how the same
stat behaves in FedAvg/Krum/trimmed-mean runs, and is a necessary
consequence of the agent needing to decide weights before an aggregate
exists.**

**Zero-weight edge case (deliberate design choice, not a gap):** if
ByzAgent quarantines/zero-weights every client in a round, `aggregate_train`
raises `RuntimeError` rather than falling back to an unweighted average
of everyone (which would include the just-quarantined clients) or
silently reusing the previous round's global model. Per 01_Planning:
quarantining all 10 clients is either a genuine catastrophic scenario or
an agent malfunction, and both must surface loudly — a silent fallback
would mask an agent failure as a normal round, the same principle as
Phase 0's test-guard and Phase 1's cached-weights assertion. Not
triggered in any run to date; if it ever fires, that is a finding to
report, not a bug to paper over.

**Live smoke test (2 rounds, f=0, zero real flips, same pattern Phase
1/2 used):** both rounds completed (`aggregate_train: Received 10
results and 0 failures` ×2), `agent_decisions.jsonl` written with 20
sane rows, hard test-guard fired correctly before any test-set touch,
val macro-F1 progressed 0.13→0.48→0.67 (sane, not corrupted — confirms
the custom weighted aggregation genuinely trains). `configs/attack.yaml`/
`defense.yaml` reverted and verified byte-for-byte via md5 afterward.

## Step 3a — manual single-round check, real {0,3,5} data (round 10)

Exact prompt and exact raw response reproduced in full in the session
transcript; not re-quoted here for length. **10/10 explanations cited an
actual numeric value from that client's own row (100% grounding on real
data)** — higher than the 91.6% synthetic-batch average. Decisions this
one round: all 3 truly-malicious silos flagged (0→downweight,
3→quarantine, 5→quarantine); 6/7 clean silos trusted, 1/7 (silo_8) a
false positive. **No prompt revision triggered** — grounding on real data
was not weak.

## Step 3b — full 20-round × 3-condition retrospective replay

69 live Ollama calls (60 base + 9 decision-variance), 56.0 min total, no
retraining — read from `client_stats.jsonl` already on disk for `clean`
(`fedavg_a0.5_s42`), `f3_{0,3,5}` (`fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5`),
`f2_{0,3}` (`fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3`).

### Outcome-level: decision distribution, correct-flag rate, false-positive rate

Aggregated counts, 200 (silo, round) observations per condition:

| condition | malicious flagged (dw\|q) | malicious quarantined-only | clean flagged (dw\|q) | clean quarantined-only |
|---|---|---|---|---|
| clean (no attack) | n/a | n/a | 86/200 = **0.43** | 44/200 = 0.22 |
| f=3 {0,3,5} | **60/60 = 1.00** | 43/60 = 0.717 | 21/140 = **0.15** | 10/140 = 0.071 |
| f=2 {0,3} | **40/40 = 1.00** | 20/40 = 0.500 | 41/160 = **0.256** | 22/160 = 0.1375 |

Krum's mechanism-level malicious-silo exclusion rate (Phase 2) was
0.0000 at both f=3 and f=2. ByzAgent's malicious-silo flag rate is 1.00
at both — **but see the compositional-extremity confound below before
reading this as detection.**

### Compositional-extremity confound (the headline caveat, quantified per-silo)

Krum has no `f/n`-style chance baseline that transfers to ByzAgent
(ByzAgent's decisions are a free 3-way choice per client, not a
fixed-count selection — same category of correction Phase 2 already had
to make for trimmed-mean's own `f/n`→`2β` baseline). The honest
baseline is the same silo's own flag rate under **no attack at all**:

| silo | malicious in | clean-condition flag rate | f=3 flag rate | f=2 flag rate | Benign % / rows |
|---|---|---|---|---|---|
| 0 | f3, f2 | **0.95** | 1.00 | 1.00 | 9.2% / 88,102 |
| 3 | f3, f2 | **1.00** | 1.00 | 1.00 | 0.3% / 38,827 |
| 5 | f3 only | **1.00** | 1.00 | — | 0.1% / 21,478 |
| **8** | **never malicious, any condition** | **0.95** | **1.00** | **1.00** | 12.3% / 82,587 |
| 1,2,4,6,7,9 (ordinary clean) | never | 0.00–0.25 | 0.00–0.05 | 0.00–0.05 | 81.5–98.0% |

Silos {0,3,5,8} are the four lowest-Benign-share silos in the entire
fleet. For the truly-malicious silos, the flag rate under real attack is
at most 5 points above their own no-attack baseline (0/3/5: +0.05/+0.00/
+0.00). Silo 8 — never malicious in any condition — shows the identical
0.95–1.00 pattern from compositional extremity alone. Essentially the
entire "1.00 malicious flag rate" result already exists with zero attack
present, driven by the same axis (attack-family/label concentration)
Phase 2 found confounding Krum/trimmed-mean.

### Decision-variance stability (round 10, 3× independent calls)

Silo-level exact-decision stability: 27/30 = 90% (clean 10/10, f=3 9/10,
f=2 8/10). **Every flip, without exception, was a downweight↔quarantine
wobble — zero flips crossed the trust/flagged boundary** (binary
flagged-vs-trusted stability = 30/30 = 100%). The 3 flips: f=3 silo_0
(malicious) `[downweight, downweight, quarantine]`; f=2 silo_3
(malicious) and silo_8 (never malicious) both `[quarantine, downweight,
quarantine]`. Cited-stat sets across the 3 repeats overlap on a
`{cosine_to_global, update_norm}` core in every flip case; `train_loss`/
`val_accuracy` citation is inconsistent repeat-to-repeat.

### Reasoning-vs-outcome audit (preserved in full — stands independent of the confound above)

**Stat citation frequency** (fraction of 200 explanations per condition):

| condition | update_norm | cosine_to_global | cosine_to_peer_mean | **train_loss** | val_accuracy |
|---|---|---|---|---|---|
| clean | 93% | **99.5%** | 7% | **7.5%** | 43.5% |
| f=3 {0,3,5} | 73% | 86% | 11.5% | **39%** | 65% |
| f=2 {0,3} | 49% | 71.5% | 3% | **53%** | 57.5% |

**Citation accuracy** (does "low"/"high" match the cited value's actual
within-round percentile among that round's 10 silos?), loose (strict
median split) vs. strict (excludes the 0.4–0.6 ambiguous band):

| stat | n | loose error | strict error (excl. ambiguous) |
|---|---|---|---|
| update_norm | 420 | **28.1%** | **25.1%** |
| cosine_to_global | 504 | 6.3% | 4.4% |
| cosine_to_peer_mean | 11 | 45.5% | 50.0% (n too small to trust) |
| **train_loss** | 184 | 16.3% | **3.8%** |
| val_accuracy | 208 | 9.1% | 8.6% |
| **overall** | 1327 | **15.4%** | **11.7%** (12.7% ambiguous) |

Hand-checked 30-row sample confirmed both categories are real: genuine
unambiguous errors exist (e.g. `update_norm` at that round's 100th
percentile called "low"), and a real share of loose-rule "errors" are
boundary artifacts (percentile ≈0.44–0.56) — this is why `train_loss`'s
error rate collapses under the stricter rule (values cluster tightly
near zero late in training) while `update_norm`'s barely moves — its
errors are genuine, not boundary noise.

**Decision-stat correlation** (Spearman ρ, decision severity
[trust=0/downweight=1/quarantine=2] vs. each stat's within-round
percentile, pooled n=600, all p<1e-13):

| stat | ρ |
|---|---|
| cosine_to_global | **−0.808** |
| **train_loss** | **+0.793** |
| val_accuracy | −0.745 |
| update_norm | +0.419 |
| cosine_to_peer_mean | +0.298 (weak; sign runs opposite cosine_to_global) |

**Finding, quantified:** `train_loss` is the second-strongest actual
correlate of the agent's decisions (ρ=0.793, nearly tied with
`cosine_to_global`'s ρ=−0.808) but is cited in only 7.5–53% of
explanations — far less than `cosine_to_global` (71.5–99.5%) and often
less than `update_norm` (49–93%). `update_norm` is cited almost as often
as `cosine_to_global` despite being the weakest of the four strongly/
moderately-correlated stats (ρ=0.419) *and* having by far the worst
citation accuracy (25–28% genuinely wrong, not boundary noise). This is
"right answer, wrong stated reason," quantified in both directions:
`train_loss` under-cited relative to its real predictive power,
`update_norm` over-cited relative to both its predictive power and its
own accuracy when cited.

**Consequence for how this contribution's explanation claim should be
framed, stated explicitly per 01_Planning:** the claim narrows from
*"ByzAgent explains its reasoning"* to *"ByzAgent produces a decision
plus a natural-language rationale of measured fidelity — [these
numbers]"*. Weaker, honest, defensible; not tuned away.

## What Step 3c would have required, and why it will not be run

The outcome-level question ("what would final-5-mean macro-F1 look like
if ByzAgent's decisions had driven aggregation") requires a **live
re-run per condition** — quarantine/downweight change what every
subsequent round's global model and local training actually are, not
just what gets logged, so retrospective replay cannot answer it.
**Will not be run against {0,3,5}/{0,3}**: any number it produced would
inherit the compositional-extremity confound above, and per the
structural finding below, no compositionally-matched alternative config
is constructible to run it against instead. 01_Planning's determination:
this confound blocks (reversing an earlier "non-blocking scope
limitation" call on the same confound from Phase 2 — it was non-blocking
when it affected only the baselines; it blocks now that ByzAgent's own
headline is confounded). Phase 3 closes on the numbers already collected
(Steps 1–3b) plus the structural finding, rather than spending GPU time
on a live run that could not produce an interpretable number either way.

## Compositionally-matched attacks are not constructible in this partition (structural finding)

**Claim:** under Dirichlet-partitioned non-IID federated IDS, attack-family
concentration and low-Benign-share are the same property measured two
ways. A silo holding enough attack traffic to poison meaningfully is
necessarily compositionally atypical. Therefore a compositionally-ordinary
silo cannot be a strong attacker — not merely in this specific partition
run, but structurally, for this dataset under Dirichlet partitioning at
the alpha this project's entire non-IID story depends on. Consequence:
single-round behavioral-statistic detection (ByzAgent's mechanism, and by
extension Krum/trimmed-mean's) cannot separate "this silo is attacking"
from "this silo is unusual," because the silos worth attacking are
exactly the unusual ones.

**Evidence, not assertion — demonstrated structurally, not just empirically
by trying the best triple:**

- The high-Benign-share group ({1,2,4,6,7,9}, 81.5–98.0% Benign) holds
  **211 of the federation's 3,174 Bot rows (6.65%)** — hypothetically
  poisoning ALL SIX of these silos together, at flip_fraction=1.0, still
  caps Bot coverage at 6.65%. This is an absolute ceiling on the entire
  group, independent of which subset or how many silos are chosen from
  it — reselection cannot fix a shortfall that is about how many attack
  rows the group holds in total, not which member of the group is picked.
- **f=3:** the best achievable triple from this group, **(2,4,9)**,
  reaches min-coverage (Bot) = **5.42%** at flip_fraction=1.0 — already
  near the group's 6.65% ceiling, confirming the frontier search found
  the best available option, not a suboptimal one. Locked primary
  {0,3,5}: **38.60%** — a **7.1× stronger ceiling**.
- **f=2 (checked as a second, independent confirmation):** the best
  achievable pair, **(2,4)**, reaches min-coverage (Bot) = **4.35%** at
  flip_fraction=1.0. Locked secondary {0,3}: **16.73%** — a **3.85×
  stronger ceiling**. The same group-wide 6.65% Bot ceiling applies here
  too (it is a property of the group's total row holdings, not of f) —
  (2,4)'s 4.35% sits comfortably under it, same pattern as f=3.
- At the locked flip_fraction=0.4, (2,4,9)'s Bot coverage would scale to
  ≈2.2% — roughly **1/10th** of {0,3,5}'s measured 22.68%
  (PHASE0_SUMMARY.md), and weaker than every family in the *retired*
  {0,1,9} rule, which Phase 0 already found produced a barely-measurable
  headline effect (−0.005, "3 of 6 families under 5%") and failed its own
  attack-strength gate.

**Why no compositionally-matched control is constructible here, stated
explicitly so its absence is never later read as an oversight:** a
control attack needs to be simultaneously (a) drawn from compositionally-
ordinary silos and (b) strong enough that failure-to-detect is
interpretable as "detection failed" rather than "there was nothing to
detect." (a) and (b) are mutually exclusive in this dataset under this
partitioning — the structural ceiling above shows condition (b) is
unreachable once condition (a) is imposed, at both f=2 and f=3, and the
group-wide (not just best-triple) ceiling rules out fixing this by trying
harder to reselect. Alternative partitions were considered and rejected
(01_Planning): a lower alpha worsens the correlation, and an alpha high
enough to remove it (e.g. 5.0) removes the non-IID setting this project
exists to study — every locked number in this project is at alpha=0.5,
and Contribution A's entire story is heterogeneity. A weak-but-real
attack from this group was also rejected: its effect size would be
indistinguishable from noise (weaker than Phase 0's own already-rejected
retired rule), producing an uninterpretable null result rather than a
clean negative one.

**Why this is not a loss, and what it means for Phase 4 (motivation, not
a guarantee — Phase 4's job is to test this, not this document's):** this
is a negative result about *single-round* detection specifically, not
about behavioral-statistic detection in general. Composition is *static*
across rounds — an always-unusual silo looks the same in round 1 and
round 20. An attack that ramps or begins mid-training is a *change* — a
silo turning malicious should look like drift *relative to its own
history*, which single-round stats (this phase's entire input) cannot
see by construction. Phase 4's rolling-history design (already-collected
`client_stats.jsonl` history, deliberately not wired into Phase 3's
prompt) is the one design in this project that could plausibly separate
"always unusual" from "recently turned," because it is the only one that
looks across rounds at all. This finding is Phase 4's motivation, not a
threat to it — whether rolling history actually achieves that separation
is Phase 4's open question to test, not a claim this document is making
in advance of that test.

## Artifact index

- `src/agents/byz_agent.py` (canonical) / `federated/xfed_federated/_vendored/byz_agent.py` (vendored)
- `configs/agent.yaml`; `configs/defense.yaml` (added `byzagent` as a documented strategy option)
- `federated/xfed_federated/server_app.py` — `LoggingByzAgent`; `federated/xfed_federated/task.py` — re-exports
- `src/monitoring/client_stats.py` / vendored copy — `finalize_round` now returns rows (additive)
- `scripts/phase3_verification_gate.py`, `scripts/phase3_analysis.py`, `scripts/phase3_compositional_check.py`, `scripts/phase3_compositional_match_search.py`
- `results/inspection/phase3_gate_raw_a0.5_s42.json` — full replay data (69 calls)
- `results/inspection/phase3_gate_analysis_a0.5_s42.json` — all metrics in this document
- `results/inspection/phase3_compositional_check_a0.5_s42.json` — per-silo cross-condition flag-rate table
- `results/inspection/phase3_citation_accuracy_sample.json` — hand-check sample for the citation-accuracy automation
- `results/inspection/phase3_compositional_match_search.json` — the structural-ceiling and best-group-restricted-combo numbers behind "Compositionally-matched attacks are not constructible in this partition"
- `results/federated/{fedavg_a0.5_s42, fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5, fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3}/agent_decisions.jsonl` — retrospective replay logs, one per condition

## NOT YET DONE

- Step 3c (live outcome-level re-run) — will not be run; closed, not deferred (see "What Step 3c would have required" above).
- Compositionally-matched attack: concluded as a structural negative finding (no clean control is constructible in this partition), not carried forward as an open task — see the structural-finding section above.
- Phase 4 (rolling history), Phase 5 (eval harness) — not started. Phase 4 should be scoped with this document's structural finding as its explicit motivation (static compositional atypicality vs. temporal attack onset), not as a blocker to route around.
- Multiple seeds (1337, 2024) — standing Phase 0 obligation, not yet closed for any configuration including ByzAgent.
