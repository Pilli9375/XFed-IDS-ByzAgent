## 2.5 Trust check (ByzAgent) {#ch-trust}

### In one line

We poisoned some organizations with a label-flipping attack, gave a local LLM agent (ByzAgent) five behaviour statistics per organization per round, compared its trust / downweight / quarantine decisions with Krum, Multi-Krum and trimmed mean, and found that every method — including ByzAgent — is entangled with how *unusual* an organization's data is, not only with whether it is attacking.

**Reminder:** this is a separate experiment from the explanation check. Its findings are reported here, on their own, and never combined with Chapter 2.4's.

### Why this exists

In federated learning the server can't see the data, so it can't check whether a client is honest. Classical robust aggregators (Krum, trimmed mean) assume "unusual update = malicious update." Under non-IID data that assumption is shaky, because honest organizations with unusual traffic also look unusual. We wanted to know:

1. Does a realistic label-flipping attack actually hurt the shared model?
2. Which behaviour statistics reveal attackers?
3. Do classical defenses catch them in a non-IID setting?
4. Can an LLM agent, reading the same statistics a human operator would see, make better-informed trust decisions — and can we check the reasons it gives?

### How it works

![ByzAgent's loop, once per round. The LLM never sees raw data, the true attacker identity, or the attacker count.](img/fig15_byzagent_loop.svg)

**The attack** (`configs/attack.yaml`; source: `docs/contribution_b_results.md` §2):

| Parameter | Value |
|---|---|
| Partition | α=0.5, seed 42 |
| f (malicious silos) | 3 |
| Malicious silos | {0, 3, 5} |
| Mode | sudden |
| flip_fraction | 0.40 |
| Strategy | targeted_to_benign |
| attack_seed | 9001 |

A secondary condition uses **f=2, silos {0, 3}** (source: `docs/contribution_b_results.md` §2).

**This is a worst-case attacker, never a realistic one.** The locked framing, used wherever this attack is cited:

> Worst-case/upper-bound adversary with full knowledge of federation composition. Selected by enumerating all C(10,3)=120 malicious-silo triples at alpha=0.5 seed=42 against the global per-silo family composition and maximizing the minimum per-family coverage across the 6 non-Benign headline families at flip_fraction=1.0 (achieved: 38.60% min, on DoS). NOT a realistic or naturalistic attacker — no real attacker has this global view.

(source: `results/attacks/PHASE0_SUMMARY.md`, quoted in `docs/contribution_b_results.md` §2)

An earlier rule ({0, 1, 9}, chosen by size) reached only 13.98% attack-row coverage and was retired as too weak a test (source: `docs/contribution_b_results.md` §2).

**The five behaviour statistics** (per silo, per round; source: `docs/contribution_b_results.md` §3):

| Statistic | Plain meaning |
|---|---|
| `update_norm` | How far the silo's weights moved from last round's global model (L2 distance) |
| `cosine_to_global` | Does the silo's update point the same way as this round's average? |
| `cosine_to_peer_mean` | Does it point the same way as the *unweighted* mean of all updates? (Unweighted on purpose, so a large malicious silo can't define its own baseline) |
| `train_loss` | The silo's own final local training loss (already in its reply; zero extra computation) |
| `val_accuracy` | Its model's accuracy on the server's fixed 143,513-row validation set |

**ByzAgent's prompt** (`src/agents/byz_agent.py`, `PROMPT_TEMPLATE`) contains: the five definitions; a required caveat — *"this specific attack biases val_accuracy upward for malicious clients on this Benign-heavy validation set — do not read high val_accuracy alone as evidence of trustworthiness"*; a note that natural non-IID differences can also move these statistics; the instruction *"cite the specific numeric value(s) that informed this decision"*; and a strict JSON schema enforced through Ollama's `format` field (source: `src/agents/byz_agent.py`; `docs/contribution_b_results.md` §5). It **never** contains the true malicious silos, the oracle f, or any hint about which statistic is strongest.

**Decisions and what they do** (`configs/agent.yaml`): *trust* → normal sample-count weight; *downweight* → 0.3 × weight; *quarantine* → weight 0 that round. One retry on malformed output, then it fails loudly (`AgentResponseError`) rather than silently defaulting (source: `configs/agent.yaml`). Temperature 0.2, `keep_alive: 0` so the model unloads from the 6 GB GPU between rounds (source: `configs/agent.yaml`).

**How the numbers were produced: replay.** The reported agent numbers come from **retrospective replays** of logged statistics from undefended FedAvg runs, not from a run where ByzAgent's decisions drove training (source: `README.md`, step 6; `docs/efficiency_results.md` Part A). Why: see "Why no live run" below.

### What we actually did — phase by phase

The trust check was built in phases, each with its own summary file (source: `docs/contribution_b_results.md` §11).

**Phase 0 — is the attack strong enough to matter?** We report **all four statistics** for every comparison: mean and median over 20 rounds, the **final-5-round mean** (rounds 16–20; the primary attack-effect statistic) and the **max** (the best-by-validation statistic that selects the deployed checkpoint) (source: `docs/contribution_b_results.md` §2):

| Statistic | Clean, seed 42 | Poisoned {0,3,5} | Poisoned {0,3} |
|---|---|---|---|
| mean (20 rounds) | 0.8535 | 0.8236 (Δ−0.0299) | 0.8253 (Δ−0.0282) |
| median | 0.8487 | 0.8438 (Δ−0.0048) | 0.8489 (Δ+0.0003) |
| **final-5 mean** | **0.9513** | **0.8746 (Δ−0.0766)** | **0.8787 (Δ−0.0726)** |
| max | 0.9760 | 0.9763 (Δ+0.0004) | 0.9867 (Δ+0.0107) |

The attack is real: the final-5 mean drops by 0.0766 (f=3) and 0.0726 (f=2). But the **max barely moves** — a constant-strength attack shifts the whole curve down a little, and the single best round can still be high. **Lesson, locked as a rule:** model selection stays best-by-validation max, attack effects are reported as the final-5 mean, and every comparison reports all four (source: `CLAUDE.md`; `docs/contribution_b_results.md` §2).

**Phase 1 — which statistics reveal attackers?** Glass's delta (malicious − clean) ÷ sd(clean), computed on the poisoned run and on a clean-run control with the same silo grouping (source: `docs/contribution_b_results.md` §3):

| Statistic | f=3 ratio (poisoned ÷ clean control) | f=2 ratio | Verdict |
|---|---|---|---|
| **train_loss** | **33.8×** | **154.3×** | clear separation |
| cosine_to_peer_mean | 1.11× | 1.17× | no separation |
| update_norm | 1.12× | 1.67× | no separation |
| cosine_to_global | 0.93× | 0.86× | no separation |
| val_accuracy | 0.31× | 0.31× | **inverts** |

- **train_loss is the only strong signal** — and that's the easy case: flipping labels directly raises the loss.
- **33.8×–154.3× is a seed-42 effect-size ratio, not a per-round detection threshold.** A per-round train_loss threshold chosen on seed 42 did not transfer (seed 1337 poisoned flag rate 0.017 vs logged 0.483) (source: `docs/efficiency_results.md` Part A).
- **val_accuracy inverts**: flipping attack labels to Benign makes malicious models *better* at the Benign-heavy validation set, so a naive reader would trust attackers more. Hence the prompt caveat.

**Phase 2 — classical baselines** (seed 42; all given the **true f as an oracle**; source: `docs/contribution_b_results.md` §4). Success means recovering at least half the gap between clean and poisoned FedAvg (`recovery_fraction ≥ 0.5`).

| Strategy | Condition | final-5 mean | recovery_fraction | Verdict |
|---|---|---|---|---|
| Multi-Krum (primary) | f=3 {0,3,5} | 0.8534 | −0.2766 | fails |
| Multi-Krum (primary) | f=2 {0,3} | 0.9766 | 1.3490 | "succeeds" — **not attack mitigation** (see below) |
| Trimmed mean | f=3 | 0.8696 | −0.0647 | fails |
| Trimmed mean | f=2 | 0.9419 | 0.8702 | "succeeds" — not confirmed as attack-attributable |
| Classical Krum (secondary only) | f=3 | 0.7738 | −1.3139 | fails |
| Classical Krum (secondary only) | f=2 | 0.7651 | −1.5652 | fails |

**Does the exclusion hit the attackers?** No:

| Strategy | Malicious exclusion rate | Correct chance baseline |
|---|---|---|
| Multi-Krum, f=3 | **0.0000** | 0.30 |
| Multi-Krum, f=2 | **0.0000** | 0.20 |
| Classical Krum, f=3 / f=2 | 1.0000 | 0.900 (it keeps 1 of 10 every round, so it excludes 9 regardless) |

(source: `docs/contribution_b_results.md` §4)

**The 0% belongs to Multi-Krum.** Classical Krum's exclusions are chance-level, because it keeps one client of ten every round (source: `CLAUDE.md`).

**Why Multi-Krum "succeeds" at f=2 without detecting anything.** It excluded the same two silos, **{2, 7}**, in every round of both conditions — the two largest (30.3% and 23.0% of the fleet) and Benign-heavy (>90%) — regardless of who was attacking. Dropping them raised the attackers' share of the remaining weight from 9.8% to 21.0%, which plausibly improved macro-F1 by rebalancing labels. A defense can't legitimately beat "no attack, no defense" (recovery > 1.0) by keeping the attack fully in the average. So **Multi-Krum's f=2 recovery of 1.35 must never be cited as attack detection** (source: `docs/contribution_b_results.md` §4).

**Confirmed with zero attackers present:** in the clean control, Multi-Krum excludes exactly {2, 7, 9} in 20/20 rounds; classical Krum selects only {4, 5}; trimmed mean's excess trim rate on {2, 7, 9} (+0.1726) matches the attack runs within 0.002–0.006 (source: `docs/contribution_b_results.md` §4). The confound is a property of the partition and each defense's geometry, not of the attack.

**The cost of defending when nobody attacks** (test macro-F1 of the clean-control runs vs clean FedAvg 0.9753): Krum −22.7pp (0.7480), Multi-Krum −4.9pp (0.9261), trimmed mean −1.6pp (0.9590) (source: `CLAUDE.md`; `docs/contribution_b_results.md` §4).

![How Krum picks, and why non-IID data fools it: the honest-but-unusual silos sit as far from the cluster as attackers do. Schematic.](img/fig11_krum.svg)

**Phase 3 — ByzAgent.**

*Model selection, by test, on 22 synthetic cases* (source: `docs/contribution_b_results.md` §5):

| Model | JSON parse | ID coverage | Explanations citing real numbers |
|---|---|---|---|
| **llama3.1:8b-instruct-q4_K_M** | 100% | 100% | **65.1%** |
| qwen2.5:7b-instruct-q4_K_M | 100% | 100% | 0.8% |
| phi3.5:latest | 100% | 59.1% (disqualifying) | 0% |

Adding "cite the specific numeric value(s)" to the prompt raised the grounded-explanation rate to 91.6% on a held-out synthetic subset (source: `docs/contribution_b_results.md` §5).

*Decisions, seed 42* (200 (silo, round) observations per condition; source: `docs/contribution_b_results.md` §5):

| Condition | Malicious flagged (downweight or quarantine) | Clean flagged |
|---|---|---|
| Clean (no attack) | n/a | 86/200 = 0.43 |
| f=3 {0,3,5} | **60/60 = 1.00** | 21/140 = 0.15 |
| f=2 {0,3} | **40/40 = 1.00** | 41/160 = 0.256 |

A flag rate of 1.00 sounds perfect. It isn't. **The compositional confound:**

| Silo | Role | Clean-run flag rate | f=3 | f=2 | Benign share |
|---|---|---|---|---|---|
| 0 | malicious (f3, f2) | 0.95 | 1.00 | 1.00 | 9.2% |
| 3 | malicious (f3, f2) | 1.00 | 1.00 | 1.00 | 0.3% |
| 5 | malicious (f3 only) | 1.00 | 1.00 | — | 0.1% |
| **8** | **never malicious** | **0.95** | 1.00 | 1.00 | 12.3% |
| 1, 2, 4, 6, 7, 9 | never | 0.00–0.25 | 0.00–0.05 | 0.00–0.05 | 81.5–98.0% |

(source: `docs/contribution_b_results.md` §5)

![The compositional confound at seed 42: the four silos with the least Benign traffic are flagged almost always — with or without an attack. Silo 8 is never malicious. From the table above.](img/fig16_confound.svg)

**The compositional confound, very simply.** Picture a school where the attendance system flags "unusual" students. The four students who always take unusual classes get flagged every day — whether or not they misbehave. Three of them are also the troublemakers we planted. The system flags them at 100%, but it also flagged them at 95–100% *before they did anything*, and it flags the fourth unusual student (silo 8, never malicious) just as often. So a 100% flag rate on the attackers mostly reflects "unusual," not "attacking." At seed 42, the attackers' **lift** over their own no-attack rate is at most +0.05 (source: `docs/contribution_b_results.md` §5).

Why can't we just pick ordinary-looking attackers to fix this? Because in this partition **a silo with enough attack traffic to poison meaningfully is necessarily compositionally unusual**. The Benign-heavy group {1, 2, 4, 6, 7, 9} holds only 211 of the federation's 3,174 Bot rows (6.65%). The strongest attacker triple drawn from that group reaches 5.42% Bot coverage vs {0, 3, 5}'s 38.60% (7.1× weaker) (source: `docs/contribution_b_results.md` §5). A matched control attack is not constructible here — a structural finding, not an oversight.

*Decision stability* (round 10, 3 independent calls): 27/30 (90%) exact match; every flip was a downweight ↔ quarantine wobble; **0** crossed the trust/flagged boundary (30/30 = 100% binary stability) (source: `docs/contribution_b_results.md` §5).

*Fidelity audit at seed 42 — do the reasons match the decisions?* (source: `docs/contribution_b_results.md` §5):

| Statistic | How often cited (clean / f3 / f2) | Correlation with decision severity (ρ) | Citation error |
|---|---|---|---|
| cosine_to_global | 99.5% / 86% / 71.5% | −0.808 | 4.4% |
| train_loss | 7.5% / 39% / 53% | +0.793 | 3.8% |
| val_accuracy | 43.5% / 65% / 57.5% | −0.745 | 8.6% |
| update_norm | 93% / 73% / 49% | +0.419 | 25.1% |
| cosine_to_peer_mean | 7% / 11.5% / 3% | +0.298 | n too small |

Overall citation strict error: **11.7%**. The pattern: train_loss is the second-strongest real driver of decisions but is rarely cited; update_norm is cited constantly despite being the weakest driver and the most often misdescribed. "Right answer, wrong stated reason," measured.


**This is why the locked wording is:** ByzAgent **produces decisions plus a rationale of measured fidelity**. Never say it "explains its reasoning" (source: `CLAUDE.md`).

**Why no live run.** A live run where ByzAgent's decisions drive aggregation would answer "what macro-F1 would we get?" But any number from it would inherit the compositional confound, and no matched control attack exists. So Phase 3 closed on the replay numbers plus the structural finding (source: `docs/contribution_b_results.md` §5).

**Phase 4 — rolling history (pre-registered, failed).** Idea: composition is static, attacks are changes. If the agent sees each silo's last 5 rounds, maybe it can spot "recently turned bad." The interpretation rule was written and locked *before* the data existed (source: `docs/contribution_b_results.md` §6):

> "If rolling-history's lift over clean baseline is comparable to current-round-only's (both near zero), or if silo 8 rises alongside the malicious silos → rolling history does NOT separate them."

Result: silo 8 (the never-malicious canary) got a rolling-history lift of +0.60 (sudden) and +0.45 (gradual) — **equal to or above every real attacker's** (source: `docs/contribution_b_results.md` §6). **Verdict: negative, as pre-registered.** Also, the agent's reasoning degraded on the longer prompt: decision-severity correlations collapsed (e.g. cosine_to_global −0.7789 → −0.2091), boundary stability fell from 100% to 70–80%, and 45.00% of 920 volunteered trend claims ("increasing," "decreasing") were wrong against the sequence it was given (source: `docs/contribution_b_results.md` §6).

**Multi-seed validation — the ceiling effect.** Three findings were re-run at seeds 1337 and 2024 (α=0.5): the confound/canary result, the fidelity audit, and a hand-check of the trend-error figure (source: `docs/contribution_b_results.md` §7). At seed 42, attackers were *already* flagged 0.95–1.00 with no attack, so their lift *couldn't* exceed ~0.05 — a **ceiling**. The new seeds have graded, not bimodal, composition, and the ceiling is mostly absent:

| Silo | Seed | Clean baseline | Sudden attack | Lift |
|---|---|---|---|---|
| 5 | 1337 | 0.00 | 0.95 | **+0.95** |
| 5 | 2024 | 0.25 | 1.00 | **+0.75** |
| 3 | 1337 | 0.00 | 0.40 | **+0.40** |
| 3 | 2024 | 1.00 | 0.95 | −0.05 (ceiling still present) |

(source: `docs/contribution_b_results.md` §7; the 0.95 for silo 3 at seed 2024 from `results/agents/MULTISEED_VALIDATION_SUMMARY.md`)

![The trust dumbbell: each malicious silo's flag rate with no attack (open circle) and under a sudden attack (filled), at three seeds. Long bars = attack-responsive detection; bars stuck near 1.00 = ceiling. Real values from contribution_b §7.](img/fig17_dumbbell.svg)

**The locked ByzAgent claim — say it exactly:**

> Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition.

(source: `CLAUDE.md`; `docs/contribution_b_results.md` §7)

**Fidelity at the new seeds gets worse, specifically** (source: `docs/contribution_b_results.md` §8): overall citation strict error rises from 11.7% to 22.5%; update_norm's link to decisions collapses to about zero and flips sign (+0.419 → −0.076) while it is still cited in about 59% of explanations, with 42.6% citation error. train_loss (3.8% → 4.7%) and val_accuracy (8.6% → 10.3%) stay reliable.

**The 45.00% trend-error figure was hand-checked**: of 35 sampled claims, 32 (91.4%) confidently validated, 3 (8.6%) ambiguous, 0 confident disagreements; adjusted error range ≈35–45%, point estimate ≈39% (source: `docs/contribution_b_results.md` §8). That's where "~35–45% of trend claims contradicted the data they were given" comes from.

**Attacker-selection portability.** {0, 3, 5} is the worst-case triple (rank 1/120) at seed 42 by construction, but only rank 8/120 at seed 1337 and 33/120 at seed 2024 (source: `docs/contribution_b_results.md` §9). A silo-index-pinned attack silently changes strength under a new partition draw — a general methodological observation.

### What we found

- **train_loss is the only strong attack signal** (33.8×–154.3×, seed-42 effect-size ratios); geometry statistics are weak-to-null; val_accuracy inverts.
- **Multi-Krum excluded a malicious silo 0% of the time**; its f=2 "success" is a compositional artifact. Defending with nobody attacking costs Krum −22.7pp, Multi-Krum −4.9pp, trimmed mean −1.6pp.
- **ByzAgent:** the locked claim above. Decisions are stable on the trust/flag boundary (30/30); exact decisions 27/30.
- **Rationale fidelity is measured, not assumed:** citation error 11.7% (seed 42) → 22.5% (seeds 1337/2024); trend claims ≈35–45% wrong under rolling history (source: `docs/contribution_b_results.md` §5, §8).
- **Rolling history failed its pre-registered test.**

### What this does NOT mean

- **Not "ByzAgent beats Krum."** The trust check is explicitly not that claim; Phases 3 and 4 are negative results on the agent's own headline metric (source: `docs/contribution_b_results.md` §1).
- **Not a realistic attack.** Every configuration is a worst-case, full-knowledge adversary.
- **Not a fair fight in the baselines' disfavour** — the opposite: the baselines were given the true f as an oracle; ByzAgent was not.
- **Not "explains its reasoning."** It produces decisions plus a rationale of measured fidelity.
- **Not deterministic.** One logged decision is one draw at temperature 0.2; stability is reported with it.
- **Not general.** Whether these failures are general properties of the detectors, or entangled with our worst-case attacker-selection rule (which selects on the same compositional axis), is **still open** (source: `docs/contribution_b_results.md` §10).
- **Mostly n=1.** Phase 2 baselines, the Phase 4 matrix and gradual mode are seed 42 only, by design (source: `CLAUDE.md`).
- **Silo 0 at seed 1337** (near-zero lift) can't be attributed: it is the most Benign-heavy silo there (95.44% Benign), so it had little attack material to flip (source: `docs/contribution_b_results.md` §7, §10).
- **A disclosed correction:** earlier documents claimed the oracle asymmetry was written to an `agent_config.json` on every run. That file never existed; the asymmetry is real and documented in prose, and the file was deliberately *not* created afterwards, because that would backdate the claim (source: `docs/contribution_b_results.md` §5).
- Under ByzAgent, `cosine_to_global` is computed against a diagnostic plain-FedAvg aggregate, not the model actually deployed that round (source: `docs/contribution_b_results.md` §5).
- Small-class caveat: Bot (n=353) and WebAttack (n=154) validation recall deltas move 0.0028 and 0.0065 per sample, so an early "damaged families" reading was retracted (source: `docs/contribution_b_results.md` §10).

### Where it lives in the code

| File | What it does |
|---|---|
| `configs/attack.yaml`, `configs/defense.yaml`, `configs/agent.yaml` | Attack, baseline and agent settings (all inert by default) |
| `src/attacks/label_flip.py` | The label-flip attack (sudden and gradual) |
| `src/monitoring/client_stats.py` | The five behaviour statistics |
| `src/agents/byz_agent.py` | Prompts, JSON schema, `decide_round()`, rolling-history extensions |
| `federated/xfed_federated/server_app.py` | `LoggingFedAvg`, `LoggingMultiKrum`, `LoggingKrum`, `LoggingFedTrimmedAvg`, ByzAgent strategy |
| `scripts/phase1_verification_gate.py` … `scripts/phase4_analysis.py`, `scripts/phase_multiseed_*.py` | Phase gates and analyses |
| `results/attacks/PHASE0_SUMMARY.md`, `results/monitoring/PHASE1_SUMMARY.md`, `results/defenses/PHASE2_SUMMARY.md`, `results/agents/PHASE3_SUMMARY.md`, `PHASE4_SUMMARY.md`, `MULTISEED_VALIDATION_SUMMARY.md` | Phase summaries |
| `docs/contribution_b_results.md` | Canonical results |

### Questions an examiner might ask

_Numbers in these model answers repeat numbers already given with their source earlier in this chapter; the source notes are not repeated here._

**Q: Krum is standard. Why did it fail?**
A: Krum assumes honest updates cluster and attackers sit apart. Under non-IID data, honest organizations with unusual traffic also sit apart. In our partition, Krum-family selection was dominated by silo size and composition: Multi-Krum excluded the same large, Benign-heavy silos every round, even with zero attackers, and excluded a malicious silo 0% of the time.

**Q: Classical Krum excluded malicious silos 100% of the time — isn't that good?**
A: No. Classical Krum keeps one client in ten every round, so it excludes nine regardless; its chance baseline is 0.900. The meaningful 0% figure is Multi-Krum's.

**Q: Why trust an LLM with security decisions?**
A: We don't trust it blindly — we audit it. We measured how often its cited numbers are wrong (11.7% at seed 42, 22.5% at other seeds), how its decisions correlate with the statistics, and how stable repeated calls are. That's why we say it produces decisions plus a rationale of measured fidelity.

**Q: ByzAgent flagged attackers 100% of the time. Why isn't that your headline?**
A: Because it flagged the same silos at 95–100% with no attack, and also a never-malicious silo. That 1.00 is mostly the compositional confound. Where the ceiling was absent (seeds 1337 and 2024), real lifts of +0.40 to +0.95 appeared.

**Q: Isn't giving the baselines the true f unfair to ByzAgent?**
A: It's unfair *in the baselines' favour*, on purpose. If they still fail with the oracle, the failure isn't due to a bad guess of f.

**Q: Why didn't you run ByzAgent live in the training loop?**
A: Any live number would inherit the compositional confound, and no compositionally matched attack can be built in this partition. So it couldn't be interpreted either way.

**Q: Why use val_accuracy at all if it inverts?**
A: It's what a human operator would see, so we kept it and told the agent, in the prompt, that high val_accuracy is not evidence of trust for this attack.

**Q: Rolling history sounds sensible. Why did it fail?**
A: Our pre-registered rule said: if the never-malicious canary rises alongside the attackers, it fails. The canary's lift (+0.60 sudden) matched or exceeded every attacker's. The agent's reasoning also degraded on longer prompts.

**Q: Is the attack realistic?**
A: No, and we say so everywhere: it's a worst-case adversary chosen by searching all 120 triples with full knowledge of every silo's composition.

**Q: Isn't train_loss enough on its own? Why an LLM?**
A: At seed 42 it separates attackers by 33.8×–154.3× as an effect size, but a per-round threshold tuned on seed 42 didn't transfer to seed 1337 (flag rate 0.017 vs 0.483 logged). And for a 100% flip, loss can *fall*, because the flipped labels become self-consistent.
