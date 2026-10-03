# Trust check (ByzAgent) — Results

**This is the canonical narrative write-up of the trust check (ByzAgent: LLM-based
Byzantine-robustness for non-IID federated IDS).** It consolidates six
engineer-facing phase summaries — `results/attacks/PHASE0_SUMMARY.md`,
`results/monitoring/PHASE1_SUMMARY.md`, `results/defenses/PHASE2_SUMMARY.md`,
`results/agents/PHASE3_SUMMARY.md`, `results/agents/PHASE4_SUMMARY.md`, and
`results/agents/MULTISEED_VALIDATION_SUMMARY.md` — into one reading order.
Every number below is read from one of those six documents; nothing here is a
new computation, and nothing is strengthened, softened, or reinterpreted
beyond what those documents already say. Where a source states something as
bounded, mixed, or unresolved, it stays that way here. §11 maps every claim
back to its source file.

---

## 1. What the trust check is, and what it is not

The trust check asks whether a Byzantine-robust aggregation mechanism can
detect and mitigate a label-flipping attack in the same non-IID federated
IDS setting the explanation check studies (Dirichlet-partitioned CICIDS2017,
alpha=0.5, 10 silos), and whether an LLM-based trust agent (**ByzAgent**) can
do this while also producing a natural-language rationale for its decisions.

It is **not** a claim that ByzAgent outperforms classical Byzantine-robust
aggregation (Krum, Multi-Krum, coordinate-wise trimmed mean). Phase 3 and
Phase 4 are negative results on the agent's own headline metric, arrived at
honestly rather than avoided. It is **not** a claim that any of the four
detection mechanisms tested here (Multi-Krum, classical Krum, trimmed-mean,
ByzAgent — current-round or rolling-history) reliably separates "this silo is
attacking" from "this silo is unusual" in this partition — Phase 3 finds a
structural reason this may be impossible under this specific attacker-selection
rule, and Phase 4 tests and confirms the same failure extends to the temporal
case. And it is not a claim that ByzAgent **explains its reasoning** — the
locked, narrower wording is that ByzAgent **produces decisions plus a
rationale of measured fidelity**, and §8 states exactly what "measured" means
in numbers.

What the contribution does establish, stated plainly and without
overreach: a working, fail-loud, oracle-free LLM trust agent that ingests the
same behavioral telemetry a human operator would have, makes an auditable
three-way decision (trust / downweight / quarantine) per client per round, and
whose reasoning can be checked against the numbers it was given — checked, and
found to be partially but not fully trustworthy, in ways this document
quantifies rather than asserts. Two negative-but-real findings — the
compositional-extremity confound (§5) and rolling history's failure to resolve
it (§6) — are reported as legitimate results, not failures to route around;
one of them (§6) was pre-registered before the data existed specifically so it
could not be spun after the fact. A later multi-seed validation session (§7)
found that seed 42's headline "zero attack-responsive lift" result was
**partly** a ceiling artifact specific to that seed, not a clean absence of
detection — this **bounds** the Phase 3 finding; it does **not** retract it.

Every attack configuration used to test detection in this project — {0,3,5}
at f=3, {0,3} at f=2 — is a **worst-case, full-knowledge adversary**,
constructed by exhaustively searching the silo-composition space for the
strongest attacker this partition admits. **Neither configuration is ever a
naturalistic attack scenario**, and every comparison in this document that
uses them (against clean baselines, against Krum/trimmed-mean, against
ByzAgent) carries that qualifier forward. Every baseline defense
(Multi-Krum, classical Krum, FedTrimmedAvg) was additionally given the true
attack strength `f` as an **oracle** — a documented, deliberate advantage.
ByzAgent was given neither the oracle `f` nor any other privileged
information. This asymmetry is repeated at every point in this document where
ByzAgent is compared against a baseline, per the project's own instruction
that it must never be left implicit.

---

## 2. The attack: construction, worst-case framing, and why gradual matters

**Locked primary configuration** (`configs/attack.yaml`, Phase 0):

| parameter | value |
|---|---|
| partition | alpha=0.5, seed=42 |
| f (malicious silos) | 3 |
| malicious silos | **{0, 3, 5}** |
| mode | sudden |
| flip_fraction | 0.40 |
| strategy | targeted_to_benign (target_class: Benign) |
| attack_seed | 9001 |
| n_silos | 10 |

**Adversary framing, verbatim, mandatory wherever this attack is cited**
(`PHASE0_SUMMARY.md`):

> Worst-case/upper-bound adversary with full knowledge of federation
> composition. Selected by enumerating all C(10,3)=120 malicious-silo triples
> at alpha=0.5 seed=42 against the global per-silo family composition and
> maximizing the minimum per-family coverage across the 6 non-Benign headline
> families at flip_fraction=1.0 (achieved: 38.60% min, on DoS). NOT a
> realistic or naturalistic attacker — no real attacker has this global view.

The retired selection rule (size-representative-by-total-training-rows,
silos {0,1,9}) achieved only 13.98% federation-wide attack-row coverage,
unevenly distributed (three of six families under 5%), and was rejected for
being too weak a test of detection. A secondary, independently-selected
worst-case condition at **f=2, {0,3}** (ceiling 16.73% min per-family
coverage) was later run as a pre-registered close-out item, paired-comparable
with the f=3 runs. **Both {0,3,5} and {0,3} are worst-case/full-knowledge
adversaries — this framing never lapses, at either f.**

Measured attack-row coverage from `flip_log.csv` matched the frontier's
flip_fraction=1.0 ceiling scaled by 0.4 within ~1–2 percentage points on
every one of the six headline non-Benign families, for both f=3 and f=2 —
confirming the flip mechanic scales linearly as designed. (`PHASE0_SUMMARY.md`,
`results/inspection/attack_row_flip_diagnostic_a0.5_s42_f3_sudden.csv`)

**The gate: is the attack strong enough to be worth detecting?** Reported per
this project's standing "always report all four statistics, never final-5
alone" rule — mean and median over all 20 rounds, **final-5-round mean**
(rounds 16–20, the primary attack-effect statistic) and **max**
(best-by-validation, the statistic that **selects the deployed checkpoint and
never changes meaning across this whole project**):

| statistic | clean_s42 | poisoned {0,1,9} (retired) | poisoned {0,3,5} (locked primary) | poisoned {0,3} (f=2) |
|---|---|---|---|---|
| mean (20 rounds) | 0.8535 | 0.8180 (Δ−0.0355) | 0.8236 (Δ−0.0299) | 0.8253 (Δ−0.0282) |
| median | 0.8487 | 0.8436 (Δ−0.0051) | 0.8438 (Δ−0.0048) | 0.8489 (Δ+0.0003) |
| **final-5 mean** | **0.9513** | 0.9143 (Δ−0.0370) | **0.8746 (Δ−0.0766)** | **0.8787 (Δ−0.0726)** |
| max (model-selection stat) | 0.9760 | 0.9710 (Δ−0.0049) | 0.9763 (Δ+0.0004) | 0.9867 (Δ+0.0107) |

Source: `PHASE0_SUMMARY.md`, `results/inspection/round_history_comparison_a0.5_s42.json`.

**Reading, exactly as Phase 0 states it:** the attack is real and worth
detecting — final-5-mean drops 3.7–7.7 percentage points across all three
poisoned conditions, always in the same direction, with the correct
dose-response ordering ({0,3,5}'s broader coverage produces the larger
final-5 drop). The **max** statistic is almost blind to it in every condition
(Δ ranges from −0.0049 to +0.0107) — not because the attack is weak, but
because max is provably insensitive to a uniform-ish level shift, which is
exactly what a constant-fraction `sudden`-mode attack produces. **This
divergence between max and final-5-mean is itself a standalone methodological
finding about best-by-validation reporting under Byzantine conditions,
carried forward as a locked requirement**: every future attack-vs-clean
comparison in this project must report both, side by side, never one alone.
**Model selection (which checkpoint deploys) remains best-by-validation MAX,
unchanged by any of this — the two statistics answer different questions and
must never be conflated.**

**Why gradual mode matters, and why it exists at all:** Phase 3's structural
finding (§5) is that composition is *static* — an always-unusual silo looks
the same in round 1 and round 20. A `sudden`-mode attack (constant
flip_fraction from round 1) cannot separate "recently turned malicious" from
"was always compositionally unusual," because it never changes. `gradual`
mode ramps `flip_fraction(round) = min(0.05 + 0.05×(round−1), 1.0)` — a
genuine linear ramp reaching 1.0 exactly on round 20 (`PHASE4_SUMMARY.md`,
`src/attacks/label_flip.py`), confirmed to match its configured schedule
exactly in `flip_log.csv`. The **pre-registered strength-matched window is
rounds 1–8** — the only range in which gradual is a fair, not-yet-stronger
test than sudden, since gradual reaches sudden's constant 0.40 flip_fraction
exactly at round 8. Phase 4's rounds-to-detection metric (§6) is evaluated
only in this window.

One live gradual-mode run (plain FedAvg, no defense, {0,3,5}, alpha=0.5,
seed=42) confirms the attack has real effect by round 20, with a **mandatory
caveat that must travel with every gradual-mode number**: gradual's final-5
window (rounds 16–20) sits at flip_fraction 0.80–1.00, 2–2.5× *stronger* than
sudden's constant 0.40 — so gradual's larger deltas below reflect a stronger
attack in that window, not greater detection difficulty:

| statistic | clean_s42 | sudden {0,3,5} | gradual {0,3,5} |
|---|---|---|---|
| mean | 0.8535 | 0.8236 (Δ−0.0299) | 0.7958 (Δ−0.0577) |
| median | 0.8487 | 0.8438 (Δ−0.0048) | 0.7993 (Δ−0.0494) |
| final-5 mean | 0.9513 | 0.8746 (Δ−0.0766) | 0.8104 (Δ−0.1408) |
| max | 0.9760 | 0.9763 (Δ+0.0004) | 0.9758 (Δ−0.0002) |

Source: `PHASE4_SUMMARY.md`. In the strength-matched window (rounds 1–8),
per-round val-macro-F1 delta (gradual − clean) is small and non-monotonic
(−0.001 to −0.041) — no clean separation at the macro-F1 level alone, which
is exactly why the *behavioral-stat* trajectory (§3, §6), not macro-F1, is
where early separation would have to be found.

---

## 3. The behavioral statistics: what each does and doesn't carry

Five per-(round, silo) statistics feed every detection mechanism in this
project (`src/monitoring/client_stats.py`, `PHASE1_SUMMARY.md`):

| stat | definition |
|---|---|
| update_norm | L2 distance, client's post-training state_dict vs. previous-round global state_dict |
| cosine_to_global | cosine similarity to this round's actual FedAvg aggregate |
| cosine_to_peer_mean | cosine similarity to the **unweighted** mean of all clients' updates this round (locked: deliberately not sample-weighted, so a large malicious silo cannot partially define its own baseline) |
| train_loss | last-epoch local training loss (already in the client's own reply — zero new computation) |
| val_accuracy | client's post-training model evaluated against the fixed, centralized 143,513-row validation set |

**Verification gate** (locked-primary poisoned run vs. clean baseline,
Glass's delta `(mean_malicious − mean_clean) / std_clean`, applied to the
same {0,3,5}-vs-rest grouping in **both** the poisoned run and a clean-run
control — the control checks whether these three silos are just naturally
different under alpha=0.5 heterogeneity, independent of any attack):

| stat | f=3 poisoned | f=3 clean-control | f=3 ratio | f=2 poisoned | f=2 clean-control | f=2 ratio | verdict |
|---|---|---|---|---|---|---|---|
| **train_loss** | **140.9** | 4.17 | **33.8x** | **51.8** | 0.34 | **154.3x** | clear separation, PASS |
| cosine_to_peer_mean | 1.78 | 1.59 | 1.11x | 1.24 | 1.06 | 1.17x | no separation beyond natural variance |
| update_norm | 1.32 | 1.19 | 1.12x | 1.18 | 0.71 | 1.67x | no separation beyond natural variance |
| cosine_to_global | 1.56 | 1.67 | 0.93x | 0.95 | 1.10 | 0.86x | no separation (poisoned run *smaller*) |
| val_accuracy | 0.97 | 3.17 | 0.31x | 0.45 | 1.44 | 0.31x | attack *narrows* the natural gap |

Source: `PHASE1_SUMMARY.md`, `results/inspection/phase1_gate_a0.5_s42_f3_sudden_silos0-3-5.json`,
`results/inspection/phase1_gate_a0.5_s42_f2_sudden_silos0-3.json`.

**Only 1 of 5 stats clearly passes**, at both f=3 and f=2. Two findings from
this must carry forward into every later phase's design, and did:

**(a) `train_loss`'s separation is the easy case, not proof all 5 stats carry
independent signal.** Label-flipping directly inflates the loss function that
produced this number — elevated loss under label noise is close to
definitional. This validates the instrumentation pipeline end to end; it does
not establish that `update_norm`, `cosine_to_global`, and `cosine_to_peer_mean`
carry independent signal, which this run's evidence says they don't at this
attack strength.

**(b) The val_accuracy inversion is a design hazard, not a routine
non-pass.** The `targeted_to_benign` attack flips labels toward Benign
(~75% of the validation set), which directly *raises* raw accuracy for
malicious clients — the malicious-vs-clean accuracy gap is **consistently
smaller** under attack than under the clean-run control, every single round,
in both directions of f. A detector — or an LLM agent — handed `val_accuracy`
without this context could read a malicious client's higher accuracy as
evidence of trustworthiness, exactly backwards for this attack family. This
is why the ByzAgent prompt (§5) is required to state this caveat explicitly,
worded to specification: *"this specific attack biases val_accuracy upward
for malicious clients on this Benign-heavy validation set — do not read high
val_accuracy alone as evidence of trustworthiness."*

---

## 4. Baselines: Krum, Multi-Krum, trimmed-mean, and their compositional artifact

**Design, locked before any run (`PHASE2_SUMMARY.md`):** Multi-Krum
(`num_nodes_to_select = n − f`) is the **primary** headline Krum-family
comparison. Classical Krum (`num_nodes_to_select = 1`, ships one raw client's
model as the next global model) is built only as a secondary sanity check and
is **never plotted or reported as a standalone baseline** comparable to
ByzAgent or Multi-Krum. FedTrimmedAvg uses `beta = f / n_silos` (0.3 at f=3,
0.2 at f=2), computed at runtime, never hand-set. **All three baselines are
given `num_malicious_nodes` = the TRUE `f` as an oracle** — Multi-Krum,
classical Krum, and FedTrimmedAvg all know how many attackers to defend
against; ByzAgent (§5) is never given this number.

**Outcome-level results, seed 42, 20 rounds** (locked anchors: f=3 clean
final-5-mean=0.9513, poisoned-FedAvg final-5-mean=0.8746, gap 0.0767; f=2
clean=0.9513, poisoned-FedAvg=0.8787, gap 0.0726; `recovery_fraction ≥ 0.5`
succeeds):

| strategy | condition | mean | median | final5mean | max | recovery_fraction | verdict |
|---|---|---|---|---|---|---|---|
| Multi-Krum (PRIMARY) | f=3 {0,3,5} | 0.7716 | 0.8018 | 0.8534 | 0.8633 | −0.2766 | FAILS |
| Multi-Krum (PRIMARY) | f=2 {0,3} | 0.8368 | 0.8474 | 0.9766 | 0.9812 | **1.3490** | SUCCEEDS — **but see below: not attack mitigation** |
| Multi-Krum (PRIMARY) | clean (oracle f=3) | 0.8223 | 0.8508 | 0.9086 | 0.9300 | n/a | test=0.9261 |
| FedTrimmedAvg | f=3 {0,3,5} | 0.8046 | 0.8351 | 0.8696 | 0.8839 | −0.0647 | FAILS |
| FedTrimmedAvg | f=2 {0,3} | 0.8294 | 0.8274 | 0.9419 | 0.9631 | 0.8702 | SUCCEEDS — not confirmed as attack-attributable, see below |
| FedTrimmedAvg | clean (oracle f=3) | 0.8388 | 0.8565 | 0.9221 | 0.9616 | n/a | test=0.9590 |
| classical Krum (SECONDARY ONLY) | f=3 {0,3,5} | 0.7014 | 0.6957 | 0.7738 | 0.8466 | −1.3139 | FAILS |
| classical Krum (SECONDARY ONLY) | f=2 {0,3} | 0.7536 | 0.7495 | 0.7651 | 0.8817 | −1.5652 | FAILS |
| classical Krum (SECONDARY ONLY) | clean (oracle f=3) | 0.5792 | 0.5983 | 0.6405 | 0.7474 | n/a | test=0.7480 |

Source: `PHASE2_SUMMARY.md`, `scripts/phase2_analysis.py`. Clean-control
test-macro-F1 for reference: clean FedAvg (locked) = 0.9753; Multi-Krum
(f=3-oracle) = 0.9261; FedTrimmedAvg (f=3-oracle) = 0.9590; classical Krum
(f=3-oracle) = 0.7480.

**Mechanism-level: does the exclusion/trim actually target the malicious
silos?** No, at either f, for either Krum variant:

| strategy | condition | malicious exclusion rate | mechanically-correct chance baseline |
|---|---|---|---|
| Multi-Krum | f=3 {0,3,5} | **0.0000** | 0.30 (f/n is correct here — num_excluded=f by construction) |
| Multi-Krum | f=2 {0,3} | **0.0000** | 0.20 (same) |
| classical Krum | f=3 {0,3,5} | 1.0000 | **0.900** (f/n does NOT apply — num_excluded=9 always, independent of f) |
| classical Krum | f=2 {0,3} | 1.0000 | 0.900 (same caveat) |

**The headline finding, locked by 01_Planning, replacing an earlier "near-zero
exclusion" framing:** Krum's distance-based selection is **dominated by silo
size/composition, not by attack-relevant behavior.** It excludes the same two
large (30.3%/23.0% of the fleet), Benign-heavy (>90%) silos {2,7} in
literally every round of both the f=3 and f=2 runs, regardless of which silos
are actually malicious — 0/20 rounds of malicious exclusion in either
condition. The apparent f=2 recovery_fraction=1.35 is explained *without*
invoking detection: excluding {2,7} mechanically shifts the surviving
aggregate's malicious-silo weight share from 9.8% to 21.0% (still fully
included, never zeroed), which plausibly drives the macro-F1 improvement on
its own via label-balance rebalancing — a defense cannot legitimately
outperform "no attack, no defense" (recovery_fraction > 1.0) by removing an
attack still fully present in the aggregate's weights. **Multi-Krum's f=2
recovery_fraction=1.35 must never be cited as evidence of attack
detection or mitigation.** At f=3, the same mechanism (excluding {2,7,9})
raises malicious weight share to 32.6% — larger, netting the observed FAIL.

**Trimmed-mean's mechanism check required its own correction.** The original
pre-registered chance baseline (`f/n`, by analogy to Krum) was locked wrong:
Krum's exclusion count is pinned to `f` by construction, but trimmed-mean's
per-coordinate trim count is pinned to `beta` (chosen as `f/n` for
oracle-sizing reasons, but not itself an exclusion-count analog). **The
corrected, locked baseline is `2×beta`.** Under it, the raw malicious-vs-baseline
gap is modest and positive (f=3: +0.0551; f=2: +0.0556) — but a **per-silo
breakdown, isolating the true "ordinary clean" group (silos 1,4,6,8) from
both the malicious group and the large/Benign-heavy group**, found the same
{2,7,9} confound present here too, and **larger than the malicious-attribution
signal, in both conditions**:

| condition | ordinary-clean baseline | malicious excess | large/Benign-heavy-clean excess |
|---|---|---|---|
| f=3 | 0.5030 | +0.1522 | **+0.1714** |
| f=2 | 0.3191 | +0.1365 | **+0.1787** |

Silo 5 — malicious at f=3 but ordinary-clean at f=2 — shows an elevated trim
rate at f=2 (0.4994) *despite not being attacked in that run*, suggesting a
third confounding axis (natural compositional extremity) distinct from both
size and actual poisoning.

**Confirmation with zero malicious silos present.** Every one of the numbers
above came from attack-condition runs, where the large/Benign-heavy silos
coexist with real attackers. The 3 clean-control runs (no malicious silo
anywhere) isolate the confound fully: Multi-Krum clean-control excludes
**exactly {2,7,9} in all 20/20 rounds**; classical Krum clean-control selects
only {4,5}, never {2,7,9}, matching all three attack-condition runs exactly;
FedTrimmedAvg clean-control's {2,7,9} trim-rate excess (+0.1726) is within
0.002–0.006 of both attack-condition excesses. **Verdict: CONFIRMED.** The
confound is attack-independent, a property of the (alpha=0.5, seed=42)
partition and each defense's geometry, not an artifact of either attack
condition. (Additionally, the clean control found silos 3 and 5 — the true
label-mixture extremes, 0.3%/0.1% Benign, not malicious in this run — trim
*even higher* than {2,7,9}, 0.7606/0.7216, indicating the confound is
sensitive to compositional distance from typical in *either* direction, not
just Benign-skew.) Source for this whole section: `PHASE2_SUMMARY.md`.

**Open item, routed to 01_Planning, not resolved by Phase 2:** the silos
Phase 0's worst-case selection rule picks as malicious ({0,3,5}: 0.3%/0.1%
Benign) are, by construction, among the most compositionally extreme silos in
the fleet — the same axis Krum/trimmed-mean's confound tracks. It is
**not yet established** whether Krum/trimmed-mean's failure to detect these
attacks is a general property of these defenses against label-flip attacks,
or is entangled with this project's specific worst-case attacker-selection
rule. §5 shows this entanglement is structural, not incidental.

---

## 5. ByzAgent: the agent, the compositional confound, and the impossibility of a matched control

**Model selection (empirical, not assumed):** three candidates tested —
`llama3.1:8b-instruct-q4_K_M`, `qwen2.5:7b-instruct-q4_K_M`, `phi3.5:latest`.
All three fit the 6GB VRAM ceiling (3.7–4.8GB resident); `keep_alive=0`
confirmed via `nvidia-smi`/`ollama ps` to unload within 3–8s. On 22 synthetic
cases:

| model | JSON parse | id-coverage | explanations citing real numbers |
|---|---|---|---|
| **llama3.1:8b-instruct-q4_K_M** | 100% | 100% | **65.1%** |
| qwen2.5:7b-instruct-q4_K_M | 100% | 100% | 0.8% |
| phi3.5:latest | 100% | 59.1% (disqualifying — corrupted client IDs) | 0% |

llama3.1:8b was selected. Adding "cite the specific numeric value(s)" to the
prompt raised grounded-explanation rate to 91.6% on a held-out synthetic
subset. Source: `PHASE3_SUMMARY.md`.

**Build.** `src/agents/byz_agent.py`: locked prompt (5 stat definitions, the
val_accuracy Benign-skew caveat worded to specification, a citation
instruction), exact JSON schema enforced via Ollama's `format` field,
`decide_round()` fails loud (`AgentResponseError`) after 1 retry on a
malformed response — never silently defaults a corrupted round. **Never
included in the prompt:** ground-truth malicious-silo identity, oracle `f`,
or any hint about which stat is strongest — this asymmetry against
Krum/Multi-Krum/trimmed-mean (§4) is written verbatim into `agent_config.json`
on every run.

> **Correction (2026-09-06, added during the Phase 6 dashboard build):**
> `agent_config.json` does not exist anywhere in this repository —
> confirmed repo-wide before this note was added. No run ever produced
> this file, contrary to the claim above and the identical claim in
> `results/agents/PHASE3_SUMMARY.md` (corrected there with the same
> note). This changes no result: the asymmetry itself is real and
> independently documented in the prose of this document and of
> `PHASE3_SUMMARY.md` — only the claim that it was *also* persisted to a
> JSON artifact is false. The file is deliberately not being generated
> now, since doing so would backdate the claim into truth rather than
> disclose the discrepancy.

`cosine_to_global` is circular for a strategy that must decide weights
*before* an aggregate exists, so `LoggingByzAgent` computes a diagnostic
**counterfactual probe aggregate** (plain FedAvg, never shipped) solely to
feed this one stat into `client_stats.jsonl` consistently with Phase 0–2's
definition — the actual shipped model uses a separate weighted mean from
ByzAgent's own decisions. Consequence, disclosed rather than buried: under
ByzAgent, `cosine_to_global` is computed against a model that is not the one
actually deployed that round. If ByzAgent zero-weights every client in a
round, `aggregate_train` raises `RuntimeError` rather than silently falling
back to an unweighted average or reusing the previous global model — not
triggered in any run to date. Source: `PHASE3_SUMMARY.md`.

### The headline caveat — confounded, must never be quoted alone

**ByzAgent's malicious-silo flag rate of 1.00 (vs. Krum's 0.0000) is
confounded by compositional extremity.** The same three malicious silos
{0,3,5} are flagged at 0.95–1.00 under a **clean, no-attack control** using
the identical stats pipeline — essentially the same rate as under real
attack. A fourth silo (8), **never malicious in any condition tested**, is
flagged at the same 0.95–1.00 rate throughout. All four are the four
lowest-Benign-share silos in the fleet (9.2%/0.3%/0.1%/12.3% Benign, vs.
81.5–98.0% for every other silo). This is the same confound §4 found for
Krum/trimmed-mean, now shown to extend to ByzAgent's own decision mechanism
— and is not fixable by reselecting attackers (see the structural finding
below).

Outcome-level decision distribution (200 (silo, round) observations per
condition):

| condition | malicious flagged (downweight\|quarantine) | clean flagged |
|---|---|---|
| clean (no attack) | n/a | 86/200 = 0.43 |
| f=3 {0,3,5} | **60/60 = 1.00** | 21/140 = 0.15 |
| f=2 {0,3} | **40/40 = 1.00** | 41/160 = 0.256 |

Per-silo flag rate, honest baseline = the same silo's own no-attack rate
(since ByzAgent's free 3-way choice has no `f/n`-style chance baseline that
transfers from Krum):

| silo | role | clean-condition flag rate | f=3 flag rate | f=2 flag rate | Benign % |
|---|---|---|---|---|---|
| 0 | malicious, f3+f2 | 0.95 | 1.00 | 1.00 | 9.2% |
| 3 | malicious, f3+f2 | 1.00 | 1.00 | 1.00 | 0.3% |
| 5 | malicious, f3 only | 1.00 | 1.00 | — | 0.1% |
| **8** | **never malicious** | **0.95** | **1.00** | **1.00** | 12.3% |
| ordinary clean (1,2,4,6,7,9) | never | 0.00–0.25 | 0.00–0.05 | 0.00–0.05 | 81.5–98.0% |

At seed 42, the lift a malicious silo shows over its own no-attack baseline
is at most +0.05 (silos 0/3/5: +0.05/+0.00/+0.00) — essentially the entire
"1.00 malicious flag rate" result already exists with zero attack present.
Source: `PHASE3_SUMMARY.md`, `results/inspection/phase3_compositional_check_a0.5_s42.json`.
**§7 bounds, without retracting, the strong reading of this result.**

**Decision-variance stability** (round 10, 3× independent calls): 27/30
(90%) exact-decision match; **every flip was a downweight↔quarantine wobble
— zero flips crossed the trust/flagged boundary** (binary stability = 30/30 =
100%).

### The explainability claim, quantified — reasoning-vs-outcome audit

Stat citation frequency and the correlation between the agent's actual
decisions and each stat's within-round percentile (Spearman ρ, pooled n=600,
all p<1e-13):

| stat | citation frequency (clean / f3 / f2) | decision-severity ρ | citation strict error |
|---|---|---|---|
| cosine_to_global | 99.5% / 86% / 71.5% | **−0.808** | 4.4% (best) |
| **train_loss** | 7.5% / 39% / 53% | **+0.793** (2nd strongest) | 3.8% (best) |
| val_accuracy | 43.5% / 65% / 57.5% | −0.745 | 8.6% |
| update_norm | 93% / 73% / 49% | +0.419 (weakest of the four real correlates) | **25.1% (worst)** |
| cosine_to_peer_mean | 7% / 11.5% / 3% | +0.298 (weak, sign runs opposite cosine_to_global) | n too small to trust |

Overall citation strict error: **11.7%**. Source: `PHASE3_SUMMARY.md`,
`results/inspection/phase3_gate_analysis_a0.5_s42.json`.

**The pattern, quantified in both directions:** `train_loss` is the
second-strongest real correlate of the agent's decisions (ρ=0.793, nearly
tied with cosine_to_global) but is cited in only 7.5–53% of explanations —
far less than cosine_to_global or even update_norm. `update_norm` is cited
almost as often as cosine_to_global (49–93%) despite being the weakest of the
four real correlates *and* having by far the worst citation accuracy
(25–28% genuinely wrong, hand-checked, not boundary noise). This is "right
answer, wrong stated reason," quantified rather than asserted. **The locked
consequence for how this claim is worded:** the claim narrows from "ByzAgent
explains its reasoning" to "ByzAgent **produces decisions plus a rationale of
measured fidelity**" — these numbers are that measurement. §8 extends this
audit to two new seeds.

### Why Step 3c (a live outcome-level re-run) will not be run

The outcome-level question — what final-5-mean macro-F1 would look like if
ByzAgent's decisions actually drove aggregation — requires a live re-run,
since quarantine/downweight change every subsequent round's training, not
just what gets logged. It will **not** be run against {0,3,5}/{0,3}: any
number it produced would inherit the compositional-extremity confound above,
and per the structural finding below, no compositionally-matched alternative
attack is constructible to run it against instead. 01_Planning's
determination reversed an earlier "non-blocking" call on the same confound
from Phase 2 (non-blocking when it only affected the baselines; blocking now
that ByzAgent's own headline is confounded). **Phase 3 closes on the numbers
already collected plus this structural finding**, not on a live run that
could not produce an interpretable number either way.

### Compositionally-matched attacks are not constructible in this partition (structural finding)

**Claim:** under Dirichlet-partitioned non-IID federated IDS, attack-family
concentration and low-Benign-share are the same property measured two ways.
A silo holding enough attack traffic to poison meaningfully is necessarily
compositionally atypical — a compositionally-ordinary silo cannot be a strong
attacker, structurally, for this dataset under this partitioning, not merely
in this one run.

**Evidence:** the high-Benign-share group ({1,2,4,6,7,9}, 81.5–98.0% Benign)
holds only 211 of the federation's 3,174 Bot rows (6.65%) — an absolute
ceiling on that group regardless of which subset is chosen. At f=3, the best
achievable triple from this group, (2,4,9), reaches min-coverage (Bot) of
5.42% at flip_fraction=1.0 — near that 6.65% ceiling, confirming the search
found the best available option — versus the locked primary {0,3,5}'s 38.60%
(**7.1× stronger**). At f=2, the best achievable pair (2,4) reaches 4.35% vs.
{0,3}'s 16.73% (**3.85× stronger**). Scaled to the locked flip_fraction=0.4,
(2,4,9)'s Bot coverage would be ≈2.2% — roughly 1/10th of {0,3,5}'s measured
22.68%, and weaker than every family in the already-rejected retired
{0,1,9} rule. Source: `PHASE3_SUMMARY.md`,
`results/inspection/phase3_compositional_match_search.json`.

**Why no control is constructible, stated so its absence is never read as an
oversight:** a control attack needs to be simultaneously (a) drawn from
compositionally-ordinary silos and (b) strong enough that a failure to detect
it is interpretable as "detection failed" rather than "there was nothing to
detect." (a) and (b) are mutually exclusive here — the ceiling above rules out
(b) once (a) is imposed, at both f=2 and f=3, and it is a *group-wide* ceiling
(total row holdings), not fixable by reselecting which member of the group is
picked. Alternative partitions were considered and rejected: a lower alpha
worsens the correlation; an alpha high enough to remove it (e.g. 5.0) removes
the non-IID setting this entire project studies.

**Why this motivates, but does not guarantee, Phase 4:** this is a negative
result about *single-round* detection specifically. Composition is static
across rounds; an attack that ramps or begins mid-training is a *change* —
something a rolling-history view could, in principle, see that a single-round
snapshot structurally cannot. Whether rolling history actually achieves that
separation is Phase 4's open question to test, not a claim asserted here in
advance of that test.

---

## 6. Rolling history: the pre-registered negative result

**Status: CLOSED.** The interpretation rule that produced this verdict was
written and locked *before* Step 3's data existed, specifically so the
framing could not be chosen after seeing where the numbers landed.

**Build.** `build_client_history()`/`build_prompt_history()`/`decide_round_history()`
extend `byz_agent.py`, selectable via `configs/agent.yaml`'s
`agent.history: {mode: current_round | rolling_history, window: 5}` (resting
state `current_round`, byte-for-byte Phase 3 behavior by default). Partial
windows are disclosed explicitly in the prompt (`min(window, r)` real rows,
never padded, never silently short) — verified via pure-function checks and a
live smoke test. Source: `PHASE4_SUMMARY.md`.

**6-cell verification matrix** (3 conditions × 2 modes, retrospective replay,
138 live Ollama calls). Per-silo flag rate:

| silo | clean·cur | clean·hist | sudden·cur | sudden·hist | gradual·cur | gradual·hist |
|---|---|---|---|---|---|---|
| 0 | 0.95 | **0.00** | 1.00 | 0.15 | 1.00 | 0.45 |
| **3** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| **5** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| **8 (canary)** | **0.90** | **0.35** | **1.00** | **0.95** | **1.00** | **0.80** |

Lift over clean baseline, the only defensible detection measure:

| silo | condition | current_round lift | rolling_history lift |
|---|---|---|---|
| 0 | sudden | +0.0500 | **+0.1500** |
| 0 | gradual | +0.0500 | **+0.4500** |
| 3, 5 | sudden & gradual | +0.0000 | +0.0000 |
| **8 (canary)** | sudden | +0.10 | **+0.60** |
| **8 (canary)** | gradual | +0.10 | **+0.45** |

**The canary's rolling-history lift (+0.60 sudden, +0.45 gradual) equals or
exceeds every real malicious silo's rolling-history lift.** Rolling-history
did not just fail to fix the compositional confound — for the never-malicious
canary specifically, it produced a *larger* false attack-response than
current-round mode ever did. Full round-by-round sequences confirm this is
not an artifact of a summary statistic: current-round silo 0 is flagged
`ddddqddqqqdddddddddq` — every single round, attack or not (the saturated
confound firing, not attack-responsive detection) — while rolling-history's
canary (silo 8, gradual) is flagged in 6 of the first 8 rounds
(`ddddddttttdddddddddq`), **indistinguishable in timing from the real
attackers.** Source: `PHASE4_SUMMARY.md`.

Decision-variance stability regresses under rolling-history: boundary
stability falls from 100% (every current-round cell) to 70–80%. The
early-rounds informativeness proxy (ordinary-clean false-positive rate)
settles to ~0.00 by round 4 under current-round mode but **never settles**
under rolling-history across all 20 rounds (still 0.50 at round 14).

**Pre-registered verdict, applied mechanically:** *"If rolling-history's lift
over clean baseline is comparable to current-round-only's (both near zero),
or if silo 8 rises alongside the malicious silos → rolling history does NOT
separate them."* Silos 3/5: lift is 0.00 in both modes — comparable, both
near zero. Silo 0: rolling-history's larger lift satisfies the positive
branch's first clause, but the branch requires silo 8 to *not* rise
correspondingly, and silo 8's lift equals or exceeds silo 0's own — the
conjunction fails. **Verdict: negative branch, confirmed.** Phase 3's
structural finding — single-round (and now, rolling-window) behavioral-statistic
detection cannot distinguish "is attacking" from "is unusual" in this
partition — extends to the temporal case.

**Closing diagnostic — two entangled claims, told apart with numbers.** Three
signals (baseline flag-rate creep for ordinary-clean silos under zero attack,
an informativeness proxy that never settles, decision-variance stability
regression) motivated one report-only diagnostic separating **(A)** rolling
history as an approach fails to separate composition from attack (already
confirmed, does not change) from **(B)** this specific model's reasoning
degrades over the denser, sequence-formatted prompt (a claim about the
model, not the method):

| check | current_round | rolling_history | reading |
|---|---|---|---|
| decision-severity ρ, cosine_to_global | −0.7789 | **−0.2091** | collapses 60-72% |
| decision-severity ρ, train_loss | +0.7510 | **+0.2105** | collapses |
| decision-severity ρ, val_accuracy | −0.7265 | **−0.2250** | collapses |
| trend-language factual error (new check, rolling-history only) | — | **45.00%** (920 claims) | nearly half of volunteered trend claims are wrong against the sequence given |

Both (A) and (B) are true simultaneously: rolling history's failure mode (the
canary rising as much as the real attacker) is present even where the
agent's citations are accurate, and this agent's reasoning coherence
measurably degrades on top of that — a different model or prompt design
might change (B) without rescuing (A). Source: `PHASE4_SUMMARY.md`,
`results/inspection/phase4_diagnostic_reasoning_audit.json`. §8 reports a
hand-validation of the 45.00% trend-error figure's own reliability.

**Not run, and why:** Krum/trimmed-mean under gradual mode (01_Planning
judged a baseline number could not move an already-negative verdict); prompt
tuning in response to the diagnostic (report-only by instruction — the Step 3
verdict does not change regardless of what the diagnostic found).

---

## 7. The ceiling effect and the revised claim

A later multi-seed validation session (seeds 1337, 2024, both alpha=0.5) was
scoped to multi-seed exactly three findings: the compositional-confound/canary
finding, the explanation-fidelity audit (§8), and an owed hand-check of
Phase 4's trend-error heuristic (§8). Everything else in Phases 0–4 remains
seed-42-only, by deliberate scoping — see §10.

**Partitions confirmed hash-exact against `data/processed/partitions/manifest.json`.**
Neither new seed reproduces seed 42's clean bimodal composition gap (extreme
0.08–12.25% Benign vs. ordinary 81.5–98.0% Benign, a 69pp gap) — composition
is graded/continuous at both new seeds. At seed 1337, **only silo 5** of the
locked malicious triple is compositionally extreme; silo 3 is ordinary; and
**silo 0 is the single most compositionally ordinary silo in the entire
fleet (95.44% Benign)**. At seed 2024, silos 3 and 5 are extreme; silo 0 sits
right at the boundary (64.22% Benign, 5th of 10). This gives seed 1337 a
**dissociation design seed 42 could not produce**: a malicious silo (0) that
is simultaneously the most compositionally ordinary silo in the fleet, so
"the agent tracks attack behavior" and "the agent tracks composition" make
opposite, falsifiable predictions about it. Source:
`MULTISEED_VALIDATION_SUMMARY.md`, §1.

**{0,3,5} at the new seeds is a genuinely weaker attack**, confirmed before
running (§9 below has the full portability finding) — at seed 1337 its
weakest-family coverage is Bot 7.91% (vs. seed 42's DoS 15.44%); at seed 2024,
BruteForce 4.85%. 01_Planning's decision was to proceed with the locked,
unmodified {0,3,5} config anyway (re-optimizing per seed would destroy the
seed-1337 dissociation design, producing a weaker test, not a stronger one).

**Lift over clean baseline, malicious silos, all three seeds:**

| seed | silo 0 | silo 3 | silo 5 |
|---|---|---|---|
| 42 (reference) | +0.05 | +0.00 | +0.00 |
| 1337 | +0.05 | **+0.40** | **+0.95** |
| 2024 | **+0.35** | −0.05 | **+0.75** |

**Canary test** (extreme, never-malicious silos, clean-run flag rate): seed
1337's canaries {2,4,7} all saturate at 1.00 — a clean reproduction of seed
42's canary pattern. Seed 2024's canaries {2,9} split: silo 9 reproduces the
pattern (1.00); silo 2 does not (0.05, a true negative). Source:
`MULTISEED_VALIDATION_SUMMARY.md`, §3.

**Per-seed verdict, stated plainly, not smoothed into agreement:** at seed
1337, the clean-run compositional grouping only *partially* held (8/10
silos matched their predicted direction; silo 5 and silo 1 contradicted it).
At seed 2024, the grouping essentially **failed** (~5/10, chance-level) — the
simple lowest-Benign%-grouping that predicted seed 42 well has little
predictive power once composition is graded rather than bimodal. The
dissociation silo (0) gives **opposite answers at the two seeds**: at 1337 it
matches the composition-tracking prediction almost exactly (clean=0.05,
sudden=0.10, lift=+0.05); at 2024 it matches the attack-tracking prediction
better (clean=0.00, sudden=0.35, lift=+0.35). This dissociation is muddied by
a mechanical confound not fully anticipated at pre-registration: the
`targeted_to_benign` strategy only flips non-Benign rows, so a
compositionally-ordinary (Benign-heavy) malicious silo is *mechanically* a
weaker attack target regardless of whether the agent tracks composition or
behavior — silo 0's poisonable material is 19,223 rows (4.56% of the silo) at
seed 1337 vs. 48,296 rows (35.78%) at seed 2024, an 8× difference.
**This session cannot cleanly separate "the agent doesn't track attack
behavior in ordinary silos" from "there was very little attack signal in
silo 0's data to detect in the first place" with the data collected, and does
not claim to.**

### The ceiling effect, the headline finding of the multi-seed session

At seed 42, all three malicious silos {0,3,5} sat at **0.95–1.00 flag rate in
the clean run** (Phase 3's own published table). Lift is bounded above by
1.00 — when a baseline already sits near 1.00, lift is mathematically capped
near zero **regardless of what the agent does under attack**. Phase 3's
headline "malicious silos show ~zero lift" was therefore partly measuring a
ceiling, not an absence of attack-responsive detection — invisible at the
time because seed 42 offered no comparison point where the ceiling was
absent (malicious identity and compositional extremity were the same set).

Seeds 1337 and 2024 mostly lack this ceiling, and once it is absent the agent
visibly does respond to attack:

| silo | seed | clean baseline | sudden | lift |
|---|---|---|---|---|
| 5 | 1337 | 0.00 | 0.95 | **+0.95** |
| 5 | 2024 | 0.25 | 1.00 | **+0.75** |
| 3 | 1337 | 0.00 | 0.40 | **+0.40** |

The one case that stays flat at a new seed — silo 3 at 2024, clean=1.00,
lift=−0.05 — is exactly the case where the ceiling is *still* present,
internally consistent with this explanation rather than an exception to it.
**This bounds Phase 3's finding; it does not retract it.** Phase 3's
description of seed 42 — malicious silos flagged at ~1.00, indistinguishable
from a never-malicious canary, ~zero measured lift — remains an accurate
description of what happened at seed 42. What changes is how far that
description generalizes.

**The revised claim, locked, replacing the strong "ByzAgent detects
compositional extremity, not attacks" reading everywhere it would otherwise
appear:**

> Both effects are present. A real compositional confound saturates some
> silos' flag rates independent of any attack; real attack-responsive
> detection is also present and becomes visible where silos are not already
> saturated. Seed 42's apparent null was partly a ceiling artifact of that
> seed's unusually bimodal composition.

Source: `MULTISEED_VALIDATION_SUMMARY.md`, "THE CEILING EFFECT" section
(which `PHASE3_SUMMARY.md` now carries a forward-reference to, so the two
documents cannot be read in isolation and reach the superseded conclusion).

---

## 8. Explanation fidelity — the independent finding

§5 established the locked wording — ByzAgent **produces decisions plus a
rationale of measured fidelity** — and quantified it at seed 42
(citation frequency, citation accuracy, decision-severity correlation). The
multi-seed session repeated the identical methodology at seeds 1337/2024
(800 decisions, 1,577 extracted citations, current-round mode only) to check
whether that measurement holds up away from seed 42.

**It gets worse, in a specific and quantifiable way, not uniformly.**
Citation accuracy roughly doubles (overall strict error 11.7% → 22.5%),
driven mainly by cosine_to_global (4.4% → 18.2%) and update_norm (25.1% →
42.6%). `train_loss` (3.8% → 4.7%) and `val_accuracy` (8.6% → 10.3%) stay
reliably low-error at both — this part reproduces cleanly.

**The sharpest single finding: `update_norm`'s correlation with the agent's
own decisions collapses to essentially zero and flips sign** (+0.419 at seed
42 → **ρ=−0.076, p=0.033, negligible effect size** pooled at the new seeds)
**while it is still cited in the 2nd-most explanations of any stat (~59%
average)** and now carries **the single worst citation accuracy of all five
stats — wrong more often than right** (42.6% strict error, above the
50%-random line for a binary high/low call once ambiguous cases are
excluded). At seed 42, citing update_norm heavily was defensible-if-imperfect
(it was at least weakly predictive). At the new seeds, the agent cites it
almost as often while it carries no real signal and is actively misdescribed
nearly half the time. `train_loss` remains under-cited relative to its
predictive power at both seed sets — the "right answer, wrong stated reason"
pattern reproduces and, on the update_norm side, sharpens.

| stat | seed42 correlation (published) | new-seed pooled correlation (n=800) |
|---|---|---|
| val_accuracy | −0.745 | **−0.577 (now the single strongest correlate)** |
| cosine_to_global | −0.808 | −0.474 |
| train_loss | +0.793 | +0.456 |
| **update_norm** | +0.419 | **−0.076 (collapses to ~zero, sign-flips)** |
| cosine_to_peer_mean | +0.298 | −0.118 (weakens, sign-flips) |

Source: `MULTISEED_VALIDATION_SUMMARY.md`, §4a,
`results/inspection/multiseed_fidelity_audit.json`.

**Hand-validation of Phase 4's 45.00% trend-error figure (§6), owed and now
closed.** A random sample of 35 of the 920 scoreable trend claims (seed=7,
no new LLM calls) was independently hand-checked against the heuristic's own
verdict: **32/35 (91.4%) confidently validated**, **3/35 (8.6%) genuinely
ambiguous boundary cases**, **0/35 confident disagreements**. Several
"wrong" verdicts are not close calls at all — e.g. a monotonically
decreasing update_norm sequence (5.997→3.802, a 36.6% drop) described by the
model as "increasing." **The 45.00% automated figure is confirmed
fundamentally sound, not an artifact of a broken extractor.** Adjusting for
the ambiguous-boundary fraction (~21.4% of "wrong" verdicts) gives an
**adjusted error-rate range of ≈35–45%, point estimate ≈39%** — either
number is defensible to report, and neither changes Phase 4's Step 3 verdict,
which does not depend on this figure. Source:
`MULTISEED_VALIDATION_SUMMARY.md`, §4b.

---

## 9. Attacker-selection portability — a separate, methodological finding

Orthogonal to the compositional-confound question above: **a silo-index-pinned
attack configuration does not preserve its "worst-case/full-knowledge
adversary" framing across seeds.** {0,3,5} is the true worst-case optimum
(rank 1/120 of all C(10,3) triples) at seed 42 by construction — but only
rank 8/120 at seed 1337, and rank 33/120 at seed 2024, with its three members
scattering across the compositional spectrum rather than clustering at the
extreme end the way seed 42's own selection process guarantees. Confirmed
before running that {0,3,5} still clears Phase 0's own disqualification bar
at both new seeds (weakest family: Bot 7.91% at 1337, BruteForce 4.85% at
2024 — both above the retired {0,1,9} rule's "three families under 5%"
failure condition, though narrowly at 2024).

This shows up directly in the macro-F1 gate, reported here because the
project's own convention requires all four statistics for every run —
**not as a re-litigation of Phase 0's seed-42-only gate verdict:**

| seed | mean Δ | median Δ | final-5-mean Δ | max Δ |
|---|---|---|---|---|
| 42 (reference) | −0.0299 | −0.0048 | −0.0766 | +0.0004 |
| 1337 | −0.0095 | **+0.0052** | **+0.0274** | **+0.0017** |
| 2024 | −0.0060 | +0.0001 | −0.0068 | −0.0141 |

At seed 1337, three of four statistics (median, final-5-mean, max) move
**positive** under attack; at seed 2024, direction mostly matches seed 42 but
magnitude is roughly 1/5–1/10 as large. The macro-F1 gate does **not**
reproduce cleanly across seeds under the locked, unmodified {0,3,5}
configuration — expected, given {0,3,5} is a materially weaker,
differently-family-bound attack at both new seeds. Source:
`MULTISEED_VALIDATION_SUMMARY.md`, §1e, §2.

**Reading, general and not specific to this project's confound work:** an
attacker-selection rule specified by silo index and frozen at one seed
silently changes character — both its strength and which axis it correlates
with — under a different Dirichlet partition draw. This is a general
methodological observation about how attacker-selection is specified in
non-IID FL research, separate from and does not block the compositional
findings in §5–§7.

---

## 10. Limitations, stated plainly

**What remains n=1, deliberately — not an oversight.** Only three findings
were multi-seeded: the compositional-confound/canary finding, the
explanation-fidelity audit, and the owed Phase 4 trend-error hand-check.
Everything else in Phases 0–4 is seed-42-only, for stated reasons
(`MULTISEED_VALIDATION_SUMMARY.md`, "What remains n=1, deliberately"):

- **Phase 2's Krum/Multi-Krum/trimmed-mean baselines** — not re-run at new
  seeds. The failure finding is mechanistic (the same two silos excluded in
  literally every round of every condition tested, zero variance), and more
  seeds cannot change a mechanistic explanation that already holds with zero
  variance.
- **Phase 4's full 6-cell matrix** — not re-run at new seeds. Its negative
  verdict rests on the canary conjunction, a qualitative failure mode, not a
  number sensitive to decimal-level precision.
- **Gradual-mode attacks** — not run at new seeds; orthogonal to the
  confound question the multi-seed session was scoped to answer.
- **Phase 5's eval harness** (ByzAgent vs. Krum/trimmed-mean benchmarking) —
  moot as originally scoped, since both baselines are already documented as
  failing for reasons a benchmarking harness would not add evidence to.
- **Phase 6 dashboard** — deferred until the React port exists.

**The compositional-extremity/attack-selection entanglement (§4, §5) is
still open, not resolved by anything reported here.** It is not established
whether Krum/trimmed-mean/ByzAgent's failure to detect these specific attacks
is a general property of these mechanisms against label-flip attacks, or is
entangled with this project's specific worst-case attacker-selection rule
(which selects on the same axis — attack-family concentration — these
mechanisms are independently shown to be sensitive to). This is a live,
unresolved question, explicitly flagged for whatever design follows this
document, not settled by Phase 2, 3, or the multi-seed session.

**Silo 0 at seed 1337's near-zero lift cannot be cleanly attributed.** It is
consistent with either "the agent doesn't track attack behavior in
compositionally-ordinary silos" (the confound hypothesis) or "there was very
little attack material in silo 0's training data at this seed to detect in
the first place" (a mechanical floor from the `targeted_to_benign` strategy
only flipping non-Benign rows) — an 8× difference in poisonable material
between the two new seeds. The multi-seed session states explicitly it
cannot separate these two explanations with the data collected, and does not
claim to.

**The trend-error heuristic's hand-validated range is a range, not a point.**
45.00% is the automated, conservative-strict figure; ≈35–45% (point estimate
≈39%) is the range after excluding hand-confirmed ambiguous boundary cases.
Both are far above what "the agent's trend claims are reliable" would look
like; neither is presented as more authoritative than the other, and neither
changes Phase 4's Step 3 verdict.

**Quantization caveat, standing since Phase 0.** Any headline family with
validation support under ~500 rows must carry its sample count alongside any
recall delta before that delta is read as signal: Bot (n=353, 1 sample =
Δrecall 0.0028) and WebAttack (n=154, 1 sample = Δrecall 0.0065). Phase 0's
own per-family recall deltas on these two families were initially read as
"damaged families" and that reading was explicitly retracted once the
sample-count context was applied — the retraction is preserved here rather
than silently dropped.

**WebAttack's persistent misclassifications are a fixed model artifact, not
a dose-responsive attack signal.** All three independently-configured
poisoned runs ({0,1,9}, {0,3,5}, {0,3}) misclassify the exact same 11
WebAttack validation examples — the same 7 clean_s42 already misses, plus the
identical additional 4 in every poisoned run — despite very different attack
configurations and coverage. This is a boundary-behavior characteristic of
this architecture/seed combination, confirmed by row-level diff, not signal.

**This repo carries two Flower-app harnesses; only one produced any number in
this document.** Root `pyproject.toml` used to route `flwr run`'s default
app target (a bare `flwr run` invocation from the repo root) at
`src/federated/` — an early, much smaller prototype (`server_app.py`/`client_app.py`)
that never implements best-by-validation checkpoint selection. Every number
in this document, and every number in the explanation check, was produced by the
separate, independent app in `federated/` (invoked as `flwr run federated
local-simulation`, which resolves entirely through `federated/pyproject.toml`
and never reads root `pyproject.toml` at all — confirmed both by reading
flwr 1.33.0's own CLI source and by direct empirical test of `flwr.cli.config_utils.load_and_validate`
against both files before and after the fix). Leaving root `pyproject.toml`
pointed at the incomplete harness was a correctness landmine: nothing
prevented a future bare `flwr run` from silently producing numbers that look
comparable to, but are not produced by, the same selection logic as
everything in `results/`. **The fix removed the `[tool.flwr.app]` section
from root `pyproject.toml` entirely**, so a bare `flwr run` now fails
immediately with `ValueError: Invalid Flower App configuration ... Missing
[tool.flwr.app] section`, rather than training against the wrong harness.
Rewiring root to duplicate the real harness (importing `federated/xfed_federated`'s
900-line implementation, with its own `_vendored/` discipline and
`_PROJECT_ROOT`-anchored config loading, as a second entry point) was judged
higher-risk for an invocation path that nothing in this project's actual
workflow ever uses — every real run, in every phase, used `flwr run federated
local-simulation`. `src/federated/` itself was not deleted, renamed, or
edited; it remains on disk, present but unused, exactly as it was.

---

## 11. Artifact index

Every claim above traces to one of the six phase summaries. This index maps
each summary to the underlying data/code artifacts it in turn cites, for
anyone who needs to go one level deeper than this document.

**Phase 0 — attack (`results/attacks/PHASE0_SUMMARY.md`):**
`configs/attack.yaml`; `src/attacks/label_flip.py` (canonical) /
`federated/xfed_federated/_vendored/label_flip.py` (vendored);
`results/attacks/a0.5_s42_f3_sudden{,_silos0-3-5}/`, `a0.5_s42_f2_sudden_silos0-3/`
(flip logs + manifests); `results/federated/fedavg_a0.5_s42_poisoned_{f3_sudden,f3_sudden_silos0-3-5,f2_sudden_silos0-3}/`;
`results/inspection/silo_family_composition_a0.5_s42.csv`;
`results/inspection/frontier_{f3,f2}_a0.5_s42.csv`;
`results/inspection/attack_row_flip_diagnostic_a0.5_s42_f3_sudden.{csv,json}`;
`results/inspection/retro_replay_val_metrics_a0.5_s42.json`;
`results/inspection/round_history_comparison_a0.5_s42.json`;
`results/inspection/webattack_prediction_diff.json`.

**Phase 1 — behavioral stats (`results/monitoring/PHASE1_SUMMARY.md`):**
`src/monitoring/client_stats.py` / vendored copy;
`federated/xfed_federated/server_app.py` (`LoggingFedAvg`);
`scripts/replay_client_stats.py`; `scripts/phase1_verification_gate.py`;
`results/federated/fedavg_a0.5_s42{,_poisoned_f3_sudden_silos0-3-5,_poisoned_f2_sudden_silos0-3}/client_stats.jsonl`;
`results/inspection/phase1_gate_a0.5_s42_{f3_sudden_silos0-3-5,f2_sudden_silos0-3}.json`.

**Phase 2 — Krum/trimmed-mean (`results/defenses/PHASE2_SUMMARY.md`):**
`federated/xfed_federated/server_app.py` (`LoggingMixin`, `LoggingMultiKrum`,
`LoggingKrum`, `LoggingFedTrimmedAvg`); `configs/defense.yaml`;
`scripts/phase2_analysis.py`; run directories
`{multikrum,trimmedmean,krumclassical}_{f3_a0.5_s42_poisoned_f3_sudden_silos0-3-5,f2_a0.5_s42_poisoned_f2_sudden_silos0-3,f3_a0.5_s42}/`,
each containing `round_history.json`, `defense_config.json`,
`krum_selection.jsonl` or `trim_rate.jsonl`.

**Phase 3 — ByzAgent (`results/agents/PHASE3_SUMMARY.md`):**
`src/agents/byz_agent.py` (canonical) /
`federated/xfed_federated/_vendored/byz_agent.py`; `configs/agent.yaml`;
`scripts/phase3_verification_gate.py`, `phase3_analysis.py`,
`phase3_compositional_check.py`, `phase3_compositional_match_search.py`;
`results/inspection/phase3_gate_raw_a0.5_s42.json`,
`phase3_gate_analysis_a0.5_s42.json`,
`phase3_compositional_check_a0.5_s42.json`,
`phase3_citation_accuracy_sample.json`,
`phase3_compositional_match_search.json`;
`results/federated/{fedavg_a0.5_s42, fedavg_a0.5_s42_poisoned_f3_sudden_silos0-3-5, fedavg_a0.5_s42_poisoned_f2_sudden_silos0-3}/agent_decisions.jsonl`.

**Phase 4 — rolling history (`results/agents/PHASE4_SUMMARY.md`):**
`src/agents/byz_agent.py` (history extensions);
`scripts/phase4_verification_gate.py`, `phase4_analysis.py`,
`phase4_diagnostic_reasoning_audit.py`;
`results/attacks/a0.5_s42_f3_gradual_silos0-3-5/flip_log.csv`;
`results/federated/fedavg_a0.5_s42_poisoned_f3_gradual_silos0-3-5/`;
`results/federated/{clean,sudden,gradual}/agent_decisions_phase4_{current_round,rolling_history}.jsonl`;
`results/inspection/phase4_gate_raw_a0.5_s42.json`,
`phase4_gate_analysis_a0.5_s42.json`,
`phase4_diagnostic_reasoning_audit.json`.

**Multi-seed validation (`results/agents/MULTISEED_VALIDATION_SUMMARY.md`):**
`results/inspection/silo_family_composition_a0.5_{s1337,s2024}.csv`;
`results/inspection/frontier_{f3,f2}_a0.5_{s1337,s2024}.csv`;
`results/federated/fedavg_a0.5_{s1337,s2024}/client_stats.jsonl` (replayed);
`results/federated/fedavg_a0.5_{s1337,s2024}_poisoned_f3_sudden_silos0-3-5/`
(new live runs); `results/attacks/a0.5_{s1337,s2024}_f3_sudden_silos0-3-5/`;
`scripts/phase_multiseed_agent_replay.py`,
`results/inspection/multiseed_agent_gate_raw.json`;
`scripts/phase_multiseed_fidelity_audit.py`,
`results/inspection/multiseed_fidelity_audit.json`,
`multiseed_citation_accuracy_sample.json`;
`scripts/sample_trend_claims.py`,
`results/inspection/multiseed_trend_claim_sample.json`,
`multiseed_trend_claim_handcheck_verdicts.json`. Also from this session:
`federated/xfed_federated/server_app.py:609` (the `_PROJECT_ROOT`-anchored
output-path fix, unrelated to any number in this document but recorded there
for completeness).

**Root `pyproject.toml` fix (§10):** `pyproject.toml` (this session, current);
`federated/pyproject.toml` (read, unmodified);
`src/attacks/label_flip.py` (the pre-existing comment that first flagged
this exact discrepancy, before it was acted on here).

---

*Numbers in this document were current as of the multi-seed validation
session (`MULTISEED_VALIDATION_SUMMARY.md`), the most recently closed of the
six source summaries, accepted by 01_Planning. If any of the six phase
summaries is revised, this document is the one to re-derive from and
update.*
