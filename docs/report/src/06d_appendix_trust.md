## Trust Check, Full Results {#sec:app-trust}

This section gives every phase of the trust check (ByzAgent and the classical baselines) with its full tables. It supports Sections 2.2.5 and 4.3. Unless stated otherwise, results are for α=0.5, seed 42, 10 silos and 20 rounds. Phase 2, the Phase 4 matrix and the gradual-mode attack are single runs by design. The attack is a worst-case construction throughout. The trust check does not claim that ByzAgent beats the classical rules; its value lies in what it shows about all of them and in the audit of the agent's stated reasons.
<!-- src: docs/contribution_b_results.md -->

### Phase 0: attack construction and strength

@tab:attack-config gives the locked attack configuration.

Table: Locked primary attack configuration (`configs/attack.yaml`) {#tab:attack-config}
| Parameter | Value |
|---|---|
| Partition | α=0.5, seed 42 |
| Malicious silos f | 3 |
| Malicious silo set | {0, 3, 5} |
| Mode | Sudden (constant flip fraction from round 1) |
| Flip fraction | 0.40 of each malicious silo's non-Benign rows |
| Strategy | Targeted to Benign (attack rows relabelled as Benign) |
| Attack seed | 9001 |
| Number of silos | 10 |
<!-- src: docs/contribution_b_results.md -->

**Selection, and why the adversary is worst-case.** The attacker set was chosen by enumerating all 120 three-silo subsets at α=0.5, seed 42, against the known family composition of every silo, and keeping the subset that maximises the minimum coverage across the six non-Benign headline families when every eligible row is flipped. For {0,3,5} the weakest family is DoS, at 38.60%. This adversary has full knowledge of the federation's composition. No real attacker has that view, so the construction bounds what a detector must handle; it does not model a realistic attack. A secondary condition at f=2, {0,3}, was chosen the same way and reaches 16.73%. An earlier rule picked size-representative silos {0,1,9}. It reached only 13.98% coverage across the federation, with three of six families under 5%, and was retired as too weak a test. Logged flips matched the expected coverage, scaled by the 0.4 flip fraction, within one to two percentage points on every family, for both f=3 and f=2.
<!-- src: docs/contribution_b_results.md -->

**Strength.** @tab:attack-gate in Section 4.3 gives all four statistics of validation macro-F1 for the clean run and the three poisoned runs. The final-five mean drops by 3.7 to 7.7 points in the same direction every time, and the drop orders correctly with coverage. The maximum is almost blind to the attack, since a constant-fraction attack shifts the curve and the maximum is insensitive to a shift. This divergence is itself a finding about best-by-validation reporting under attack. It is why every attack comparison in this project reports both statistics, while the deployed checkpoint is still chosen by the maximum.
<!-- src: docs/contribution_b_results.md -->

**Gradual mode.** In gradual mode the flip fraction ramps as min(0.05 + 0.05(r − 1), 1), reaching 1.0 exactly at round 20 and matching the sudden attack's 0.40 at round 8. Rounds 1 to 8 are therefore the strength-matched window, the only range in which gradual is a fair test against sudden. In its final five rounds the gradual attack runs at flip fractions of 0.80 to 1.00, 2 to 2.5 times stronger than the sudden one, so its larger drops in @tab:gradual reflect a stronger attack, not a harder detection problem. Inside rounds 1 to 8 the per-round gap to the clean run is small and non-monotonic (−0.001 to −0.041).
<!-- src: docs/contribution_b_results.md -->

Table: Sudden against gradual attack on {0,3,5}: validation macro-F1 (change against clean in brackets) {#tab:gradual}
| Statistic | Clean | Sudden | Gradual |
|---|:-:|:-:|:-:|
| Mean | 0.8535 | 0.8236 (−0.0299) | 0.7958 (−0.0577) |
| Median | 0.8487 | 0.8438 (−0.0048) | 0.7993 (−0.0494) |
| Final-5 mean | 0.9513 | 0.8746 (−0.0766) | 0.8104 (−0.1408) |
| Max | 0.9760 | 0.9763 (+0.0004) | 0.9758 (−0.0002) |
<!-- src: docs/contribution_b_results.md -->

### Phase 1: the five statistics

@tab:phase1 gives Glass's δ, the difference between the malicious and clean group means divided by the clean group's standard deviation, for the same silo grouping in the poisoned run and in a clean control run where no silo attacks. The control asks whether these silos differ anyway because of their data.
<!-- src: docs/contribution_b_results.md -->

Table: Phase 1: Glass's δ in the poisoned run and the clean control (ratio = poisoned / control) {#tab:phase1 size=9.5}
| Statistic | f=3 poisoned | f=3 control | f=3 ratio | f=2 poisoned | f=2 control | f=2 ratio | Verdict |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| train_loss | 140.9 | 4.17 | 33.8× | 51.8 | 0.34 | 154.3× | Clear separation |
| cosine_to_peer_mean | 1.78 | 1.59 | 1.11× | 1.24 | 1.06 | 1.17× | Within natural variance |
| update_norm | 1.32 | 1.19 | 1.12× | 1.18 | 0.71 | 1.67× | Within natural variance |
| cosine_to_global | 1.56 | 1.67 | 0.93× | 0.95 | 1.10 | 0.86× | None; poisoned smaller |
| val_accuracy | 0.97 | 3.17 | 0.31× | 0.45 | 1.44 | 0.31× | Attack narrows the gap |
<!-- src: docs/contribution_b_results.md -->

Training loss separates clearly, but label flipping raises the loss almost by definition, so this mainly confirms that the instrumentation works end to end; it does not show that the geometric statistics carry independent signal. Validation accuracy inverts. With labels pushed toward Benign on a validation set that is about three quarters Benign, malicious silos look more accurate, and the gap between malicious and clean silos is smaller under attack than in the control in every round. A detector, or an agent, given validation accuracy without this context would read a malicious silo's higher accuracy as evidence of trust, which is exactly backwards. For this reason the agent's prompt carries an explicit warning about it.
<!-- src: docs/contribution_b_results.md -->

The 33.8× and 154.3× ratios are seed-42 effect sizes, not per-round thresholds. A per-round training-loss threshold chosen on seed 42 did not transfer: at seed 1337 it flagged poisoned silo-rounds at a rate of 0.017, against the 0.483 the agent had logged (Section 6.I).
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

### Phase 2: Krum, Multi-Krum and trimmed mean

The design was fixed before any run. Multi-Krum, keeping n − f updates, is the main Krum-family baseline. Classical Krum, which ships one client's model as the next global model, is a secondary sanity check and is never presented as a standalone baseline. Trimmed mean uses β = f/n (0.3 at f=3, 0.2 at f=2), computed at run time. All three receive the true f as an oracle; ByzAgent never does. The recovery fraction is the share of the clean-to-poisoned gap in final-five mean that a defence closes (gap 0.0767 at f=3 and 0.0726 at f=2), and a value of 0.5 or more counts as success. @tab:phase2 gives the outcomes.
<!-- src: docs/contribution_b_results.md -->

Table: Phase 2 outcomes: validation macro-F1 statistics over 20 rounds and recovery fraction {#tab:phase2 size=9}
| Defence | Condition | Mean | Median | Final-5 | Max | Recovery | Verdict |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| Multi-Krum | f=3 {0,3,5} | 0.7716 | 0.8018 | 0.8534 | 0.8633 | −0.2766 | Fails |
| Multi-Krum | f=2 {0,3} | 0.8368 | 0.8474 | 0.9766 | 0.9812 | 1.3490 | "Succeeds": compositional artifact |
| Multi-Krum | Clean (oracle f=3) | 0.8223 | 0.8508 | 0.9086 | 0.9300 | n/a | |
| Trimmed mean | f=3 {0,3,5} | 0.8046 | 0.8351 | 0.8696 | 0.8839 | −0.0647 | Fails |
| Trimmed mean | f=2 {0,3} | 0.8294 | 0.8274 | 0.9419 | 0.9631 | 0.8702 | Succeeds; not shown to be attack-related |
| Trimmed mean | Clean (oracle f=3) | 0.8388 | 0.8565 | 0.9221 | 0.9616 | n/a | |
| Classical Krum | f=3 {0,3,5} | 0.7014 | 0.6957 | 0.7738 | 0.8466 | −1.3139 | Fails |
| Classical Krum | f=2 {0,3} | 0.7536 | 0.7495 | 0.7651 | 0.8817 | −1.5652 | Fails |
| Classical Krum | Clean (oracle f=3) | 0.5792 | 0.5983 | 0.6405 | 0.7474 | n/a | |
<!-- src: docs/contribution_b_results.md -->

**Cost with no attack.** Test macro-F1 of the clean runs is 0.9753 for undefended FedAvg, 0.9261 for Multi-Krum, 0.9590 for trimmed mean and 0.7480 for classical Krum. Defending when nobody attacks therefore costs 22.7 points for Krum, 4.9 for Multi-Krum and 1.6 for trimmed mean. Each clean run's results file also holds a round-20 test score from the legacy harness's end-of-run pass; no claim uses it, and it is no longer exported to the site.
<!-- src: docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

**Who gets excluded.** @tab:exclusion compares how often a malicious silo is excluded with the right chance rate. Multi-Krum excludes f updates per round by construction, so f/n is its chance rate. Classical Krum always excludes nine of ten, so its chance rate is 0.9 whatever f is. Multi-Krum excluded a malicious silo 0% of the time. Classical Krum's exclusions are chance-level: it keeps 1 of 10 every round.
<!-- src: docs/contribution_b_results.md -->

Table: Malicious-silo exclusion rate against the matching chance rate {#tab:exclusion}
| Defence | Condition | Exclusion rate | Chance rate |
|---|---|:-:|:-:|
| Multi-Krum | f=3 | 0.0000 | 0.30 |
| Multi-Krum | f=2 | 0.0000 | 0.20 |
| Classical Krum | f=3 | 1.0000 | 0.900 |
| Classical Krum | f=2 | 1.0000 | 0.900 |
<!-- src: docs/contribution_b_results.md -->

**The compositional artifact.** Krum's distance-based selection is driven by silo size and composition, not by attack behaviour. Multi-Krum removed the same large, Benign-heavy silos in every round of every condition: silos 2 and 7, which hold 30.3% and 23.0% of the fleet and are over 90% Benign. At f=2, dropping {2,7} raised the malicious silos' weight share in the surviving aggregate from 9.8% to 21.0% while they stayed fully included, so the 1.3490 recovery cannot be mitigation; a defence cannot beat the no-attack run by removing an attack it kept. The gain plausibly comes from rebalancing labels. At f=3 the same mechanism, with {2,7,9} removed, raised the malicious share to 32.6%, which nets the observed failure. Multi-Krum's f=2 recovery must never be cited as evidence of detection.
<!-- src: docs/contribution_b_results.md -->

**Trimmed mean.** Trimmed mean's chance baseline had to be corrected. It is 2β, not f/n: the trim count per coordinate is set by β at both ends. Against 2β, the malicious excess in trim rate is small and positive (+0.0551 at f=3, +0.0556 at f=2). Splitting the clean silos into an ordinary group (1, 4, 6, 8) and the large Benign-heavy group (2, 7, 9) shows that the composition excess is larger than the malicious one in both conditions (@tab:trim). Silo 5, malicious at f=3 but ordinary at f=2, still shows a raised trim rate of 0.4994 at f=2, which suggests a third confounding axis, natural compositional extremity.
<!-- src: docs/contribution_b_results.md -->

Table: Trimmed mean: trim rate of ordinary clean silos, and the excess of malicious and of large Benign-heavy clean silos over it {#tab:trim}
| Condition | Ordinary clean | Malicious excess | Large, Benign-heavy excess |
|---|:-:|:-:|:-:|
| f=3 | 0.5030 | +0.1522 | +0.1714 |
| f=2 | 0.3191 | +0.1365 | +0.1787 |
<!-- src: docs/contribution_b_results.md -->

**Confirmation with no attacker present.** The three clean control runs, with no malicious silo anywhere, isolate the confound. Multi-Krum excludes exactly {2,7,9} in 20 of 20 rounds. Classical Krum selects only silos 4 and 5, never {2,7,9}, matching the attack runs exactly. Trimmed mean's {2,7,9} excess is +0.1726, within 0.002 to 0.006 of both attack runs. The clean control also found that silos 3 and 5, the true label-mix extremes at 0.3% and 0.1% Benign, trim even more (0.7606 and 0.7216). The confound therefore follows distance from a typical label mix in either direction. It is a property of this partition and of each defence's geometry, not an artifact of either attack.
<!-- src: docs/contribution_b_results.md -->

### Phase 3: ByzAgent

**Model selection.** Three local models were tried on 22 synthetic cases (@tab:llm-select). All three fit within the 6 GB GPU budget (3.7 to 4.8 GB resident) and unload within 3 to 8 seconds once a call finishes. Llama 3.1 8B was chosen: it parsed and covered every client, and it cited real numbers far more often than the others. Phi-3.5 was disqualified because it corrupted client identifiers. Adding an instruction to cite the specific values behind each decision lifted the share of grounded explanations to 91.6% on a held-out synthetic subset.
<!-- src: docs/contribution_b_results.md -->

Table: Language-model selection for ByzAgent on 22 synthetic cases (all 4-bit quantized) {#tab:llm-select}
| Model | JSON parse | Client-ID coverage | Explanations citing real numbers | Outcome |
|---|:-:|:-:|:-:|---|
| llama3.1:8b-instruct-q4_K_M | 100% | 100% | 65.1% | Selected |
| qwen2.5:7b-instruct-q4_K_M | 100% | 100% | 0.8% | Not selected |
| phi3.5:latest | 100% | 59.1% | 0% | Disqualified (corrupted IDs) |
<!-- src: docs/contribution_b_results.md -->

**Prompt and schema.** The prompt states the server's task, defines the five statistics, warns that this attack biases validation accuracy upward for malicious silos on a Benign-heavy validation set, notes that natural non-IID differences can also move the statistics, lists every silo's values for the round, and asks for one decision per silo with an explanation that cites the numbers used. The reply must match a JSON schema with a round number and a list of decisions, each holding a client id, a decision of trust, downweight or quarantine, and an explanation; Ollama enforces the schema through its format field. The full schema and prompt excerpt are in Section 6.S. A malformed reply is retried once and then raises an error, so no round is ever silently defaulted. Trust keeps a silo's normal weight, downweight multiplies it by 0.3, and quarantine sets it to zero. If every silo were quarantined, the server would raise an error rather than fall back to an unweighted average.
<!-- src: configs/agent.yaml; docs/contribution_b_results.md -->

The prompt never contains attacker identities, f, or hints about which statistic matters. Because the agent has to decide before an aggregate exists, cosine-to-aggregate is computed against a probe FedAvg aggregate that is never shipped; under ByzAgent, therefore, this one statistic refers to a model that is not the one deployed in that round. An earlier summary claimed that the asymmetry against the oracle-f baselines was also written to a file named `agent_config.json`. No such file exists anywhere in the repository; the claim was corrected rather than back-filled, and no result depends on it.

**Decisions.** @tab:agent-decisions counts flags over 200 silo-rounds per condition, and @tab:agent-silo gives per-silo rates. The three malicious silos and a never-malicious silo, 8, are the four lowest-Benign silos at seed 42, with 9.2%, 0.3%, 0.1% and 12.3% Benign traffic against 81.5% to 98.0% for every other silo. Their flag rates are already 0.95 to 1.00 with no attack, so the lift at seed 42 is at most +0.05.
<!-- src: docs/contribution_b_results.md -->

Table: ByzAgent flags (downweight or quarantine), seed 42, 200 silo-rounds per condition {#tab:agent-decisions}
| Condition | Malicious flagged | Clean flagged |
|---|:-:|:-:|
| Clean (no attack) | n/a | 86/200 = 0.43 |
| f=3 {0,3,5} | 60/60 = 1.00 | 21/140 = 0.15 |
| f=2 {0,3} | 40/40 = 1.00 | 41/160 = 0.256 |
<!-- src: docs/contribution_b_results.md -->

Table: Per-silo ByzAgent flag rate, seed 42 {#tab:agent-silo}
| Silo | Role | Clean run | f=3 | f=2 | Benign share |
|---|---|:-:|:-:|:-:|:-:|
| 0 | Malicious in both | 0.95 | 1.00 | 1.00 | 9.2% |
| 3 | Malicious in both | 1.00 | 1.00 | 1.00 | 0.3% |
| 5 | Malicious at f=3 | 1.00 | 1.00 | n/a | 0.1% |
| 8 | Never malicious | 0.95 | 1.00 | 1.00 | 12.3% |
| 1, 2, 4, 6, 7, 9 | Never malicious | 0.00–0.25 | 0.00–0.05 | 0.00–0.05 | 81.5–98.0% |
<!-- src: docs/contribution_b_results.md -->

**Stability.** At round 10, three independent calls per condition matched exactly in 27 of 30 decisions (90%). Every mismatch was a switch between downweight and quarantine, so the trust-versus-flagged call was stable in 30 of 30 (100%).
<!-- src: docs/contribution_b_results.md -->

**Why a live re-run was not done.** Measuring what final-five macro-F1 would look like if ByzAgent's decisions drove aggregation needs a live re-run, because quarantining or downweighting changes every later round. It was not run against {0,3,5} or {0,3}, because any number it produced would carry the compositional confound above, and, as the next paragraph shows, no compositionally matched attack can be built to run it against instead.
<!-- src: docs/contribution_b_results.md -->

**Why no matched control exists.** In this partition, holding enough attack traffic to poison well and having a low Benign share are the same property, measured two ways. The six high-Benign silos (1, 2, 4, 6, 7, 9; 81.5% to 98.0% Benign) hold only 211 of the federation's 3,174 Bot rows (6.65%), a ceiling on any subset of that group. The best triple from that group, {2,4,9}, reaches a minimum coverage of 5.42% against 38.60% for {0,3,5}, 7.1 times weaker. The best pair, {2,4}, reaches 4.35% against 16.73% for {0,3}, 3.85 times weaker. Scaled to the locked 0.4 flip fraction, {2,4,9} would cover about 2.2% of Bot, roughly a tenth of the 22.68% that {0,3,5} actually covers. A control that is both compositionally ordinary and strong cannot be built, and this is a ceiling on the whole group, not something that choosing different members could fix. Other partitions were considered and rejected: a lower α makes the link stronger, and an α high enough to remove it removes the non-IID setting that the whole project studies.
<!-- src: docs/contribution_b_results.md -->

### The fidelity audit

The fidelity audit compares the statistics the agent cites with the statistics its decisions actually follow. Decision severity is correlated with each statistic's within-round percentile using Spearman's ρ, pooled over 600 decisions (@tab:fidelity42). Training loss is almost the strongest correlate of the agent's decisions but is cited least often of the four main statistics. Update norm is cited often, is the weakest real correlate, and is misdescribed most often, with 25.1% strict error confirmed by hand rather than boundary noise. The overall strict citation error is 11.7%. This pattern, the right answer with the wrong stated reason, is the reason the project's wording is that ByzAgent produces decisions plus a rationale of measured fidelity.
<!-- src: docs/contribution_b_results.md -->

Table: Seed 42: citation frequency (clean / f=3 / f=2), decision-severity ρ and strict citation error {#tab:fidelity42}
| Statistic | Cited in explanations | ρ with decision severity | Strict citation error |
|---|:-:|:-:|:-:|
| cosine_to_global | 99.5% / 86% / 71.5% | −0.808 | 4.4% |
| train_loss | 7.5% / 39% / 53% | +0.793 | 3.8% |
| val_accuracy | 43.5% / 65% / 57.5% | −0.745 | 8.6% |
| update_norm | 93% / 73% / 49% | +0.419 | 25.1% |
| cosine_to_peer_mean | 7% / 11.5% / 3% | +0.298 | Too few citations |
<!-- src: docs/contribution_b_results.md -->

At seeds 1337 and 2024 the same audit covered 800 decisions and 1,577 extracted citations. The overall strict error roughly doubled, from 11.7% to 22.5%, mainly through cosine-to-aggregate (4.4% to 18.2%) and update norm (25.1% to 42.6%). Training loss (3.8% to 4.7%) and validation accuracy (8.6% to 10.3%) stayed low (@tab:fidelity-new). Update norm's correlation with the agent's own decisions collapsed to near zero and changed sign, yet the agent still mentioned it in roughly 59% of its explanations, and 42.6% of those mentions misstated it, which is worse than chance once ambiguous cases are set aside.
<!-- src: docs/contribution_b_results.md -->

Table: Decision-severity correlation: seed 42 against seeds 1337 and 2024 pooled (n=800) {#tab:fidelity-new}
| Statistic | Seed 42 | Seeds 1337 and 2024 |
|---|:-:|:-:|
| val_accuracy | −0.745 | −0.577 |
| cosine_to_global | −0.808 | −0.474 |
| train_loss | +0.793 | +0.456 |
| update_norm | +0.419 | −0.076 |
| cosine_to_peer_mean | +0.298 | −0.118 |
<!-- src: docs/contribution_b_results.md -->

### Multi-seed validation and the ceiling effect

A later session repeated three findings at seeds 1337 and 2024, both at α=0.5: the compositional confound and its canary, the fidelity audit above, and a hand check of the Phase 4 trend-error figure. Everything else in Phases 0 to 4 stays single-seed by design.
<!-- src: docs/contribution_b_results.md -->

**Composition at the new seeds.** The partitions matched the manifest exactly. Neither new seed reproduces seed 42's two-group composition, in which the extreme silos hold 0.08% to 12.25% Benign and the ordinary ones 81.5% to 98.0%, a 69-point gap; at the new seeds composition is graded. At seed 1337 only silo 5 of the attacker set is extreme, silo 3 is ordinary, and silo 0 is the single most ordinary silo in the fleet (95.44% Benign). At seed 2024, silos 3 and 5 are extreme and silo 0 sits at the boundary (64.22% Benign, fifth of ten). Seed 1337 therefore offers a test that seed 42 could not: a malicious silo that is also the most ordinary one, for which "the agent tracks attacks" and "the agent tracks composition" predict opposite outcomes.
<!-- src: docs/contribution_b_results.md -->

**A weaker attack at the new seeds.** The silo-index-pinned set {0,3,5} is the worst-case optimum at seed 42 by construction, but it ranks only 8th of 120 at seed 1337 and 33rd of 120 at seed 2024. Its weakest-family coverage is Bot at 7.91% (seed 1337) and BruteForce at 4.85% (seed 2024). Both still clear the retired rule's failure condition, narrowly at seed 2024. The team kept {0,3,5} unchanged, since re-optimizing per seed would have destroyed the seed-1337 test. @tab:portability shows that the macro-F1 effect does not reproduce. At seed 1337, three of the four statistics move up under attack; at seed 2024 the direction mostly matches seed 42 but the size is about a fifth to a tenth.
<!-- src: docs/contribution_b_results.md -->

Table: Attack effect by seed for the {0,3,5} sudden attack (change against clean) {#tab:portability}
| Seed | Mean | Median | Final-5 mean | Max |
|:-:|:-:|:-:|:-:|:-:|
| 42 | −0.0299 | −0.0048 | −0.0766 | +0.0004 |
| 1337 | −0.0095 | +0.0052 | +0.0274 | +0.0017 |
| 2024 | −0.0060 | +0.0001 | −0.0068 | −0.0141 |
<!-- src: docs/contribution_b_results.md -->

This is a general methodological point about non-IID federated learning research: an attacker set specified by silo index and frozen at one seed silently changes both its strength and the axis it correlates with under a different partition draw.

**Lift and canaries.** @tab:lift in Section 4.3 gives the lift of each malicious silo over its own clean-run rate. Where the clean rate is low, the agent responds to the attack: silo 5 at seed 1337 (clean 0.00, attacked 0.95, lift +0.95) and seed 2024 (clean 0.25, attacked 1.00, lift +0.75), and silo 3 at seed 1337 (clean 0.00, attacked 0.40, lift +0.40). Where the clean rate is already at the ceiling, as for silo 3 at seed 2024 (clean 1.00), lift stays flat at −0.05. Canary silos, which are extreme but never malicious, saturate at 1.00 at seed 1337 (silos 2, 4 and 7). At seed 2024, silo 9 saturates as well, while silo 2 does not (0.05, a true negative).
<!-- src: docs/contribution_b_results.md -->

**Per-seed verdict.** At seed 1337 the simple lowest-Benign grouping predicted 8 of 10 silos; at seed 2024 it predicted about 5 of 10, roughly chance. Silo 0 gave opposite answers at the two seeds. At seed 1337 it matched the composition prediction (clean 0.05, attacked 0.10, lift +0.05); at seed 2024 it matched the attack prediction better (clean 0.00, attacked 0.35, lift +0.35). But the attack flips only non-Benign rows, so a Benign-heavy attacker has little to flip: silo 0 held 19,223 poisonable rows (4.56% of the silo) at seed 1337 against 48,296 (35.78%) at seed 2024, an eightfold difference. These data cannot separate "the agent misses attacks in ordinary silos" from "there was little attack to see".
<!-- src: docs/contribution_b_results.md -->

**The ceiling effect.** At seed 42 all three malicious silos sat at 0.95 to 1.00 in the clean run. Lift is bounded above by 1.00, so when the baseline is already near 1.00, lift is capped near zero whatever the agent does under attack. The seed-42 headline of "about zero lift" was therefore partly measuring a ceiling, which could not be seen at the time because at seed 42 the malicious silos and the extreme silos were the same set. This bounds the Phase 3 finding without retracting it: the description of seed 42 remains accurate, and what changes is how far it generalizes. The locked claim that replaces the stronger reading is quoted in Section 4.3.
<!-- src: docs/contribution_b_results.md -->

### Phase 4: rolling history

The rolling-history variant shows the agent the last five rounds of each statistic for each silo, with fewer rounds early on, which the prompt discloses. It was tested in a six-cell matrix (three conditions times two modes, 138 live calls) under a rule written before the data existed: if the history mode's lift is comparable to the current-round lift, or if canary silo 8 rises with the malicious silos, history does not separate them. @tab:phase4 and @tab:phase4-lift give the results.
<!-- src: docs/contribution_b_results.md -->

Table: Phase 4 per-silo flag rate (cur = current round only, hist = rolling history) {#tab:phase4}
| Silo | Clean, cur | Clean, hist | Sudden, cur | Sudden, hist | Gradual, cur | Gradual, hist |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| 0 | 0.95 | 0.00 | 1.00 | 0.15 | 1.00 | 0.45 |
| 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 8 (canary) | 0.90 | 0.35 | 1.00 | 0.95 | 1.00 | 0.80 |
<!-- src: docs/contribution_b_results.md -->

Table: Phase 4 lift over the clean baseline {#tab:phase4-lift}
| Silo | Attack | Current round | Rolling history |
|---|---|:-:|:-:|
| 0 | Sudden | +0.0500 | +0.1500 |
| 0 | Gradual | +0.0500 | +0.4500 |
| 3 and 5 | Both | +0.0000 | +0.0000 |
| 8 (canary) | Sudden | +0.10 | +0.60 |
| 8 (canary) | Gradual | +0.10 | +0.45 |
<!-- src: docs/contribution_b_results.md -->

The canary's rolling-history lift (+0.60 sudden, +0.45 gradual) equals or exceeds every malicious silo's lift, so the negative branch of the rule applies. The full sequences confirm it. In current-round mode silo 0 is flagged in every round, attack or not, which is the saturated confound firing. In rolling-history mode the canary is flagged in 6 of the first 8 rounds of the gradual run, the same timing as a real attacker. Decision stability at the trust-versus-flagged boundary falls from 100% to 70 to 80%, and the false-positive rate on ordinary clean silos never settles: it is still 0.50 at round 14.
<!-- src: docs/contribution_b_results.md -->

**A diagnostic that separates two claims.** A report-only diagnostic told apart two things: (A) rolling history as an approach fails to separate composition from attack, which was already decided; and (B) this particular model's reasoning degrades on the denser prompt. (B) also holds (@tab:phase4-diag). Decision-severity correlations collapse, and 45.00% of 920 scoreable trend claims are wrong against the sequence the agent was given; for example, a steadily falling update norm (5.997 to 3.802) was described as "increasing". A hand check of 35 sampled claims confirmed the automatic verdict in 32 (91.4%), found 3 (8.6%) ambiguous and none in clear disagreement, which puts the error at about 35 to 45%, with a point estimate of about 39%. Krum and trimmed mean were not run in gradual mode, because a baseline number could not move an already negative verdict, and the prompt was not tuned after the diagnostic.
<!-- src: docs/contribution_b_results.md -->

Table: Phase 4 diagnostic: decision-severity correlation in each mode {#tab:phase4-diag}
| Check | Current round | Rolling history |
|---|:-:|:-:|
| ρ, cosine_to_global | −0.7789 | −0.2091 |
| ρ, train_loss | +0.7510 | +0.2105 |
| ρ, val_accuracy | −0.7265 | −0.2250 |
| Trend claims wrong (rolling history only) | n/a | 45.00% of 920 |
<!-- src: docs/contribution_b_results.md -->

### Other caveats and design notes

**Small validation classes.** Bot and WebAttack have 353 and 154 validation rows, so a single row moves their recall by 0.0028 and 0.0065. An early reading of "damaged families" in Phase 0 was retracted once these sample counts were applied, and the retraction is kept on record.
<!-- src: docs/contribution_b_results.md -->

**A fixed WebAttack artifact.** All three poisoned runs misclassify the same 11 WebAttack validation rows: the 7 that the clean run already misses, plus the same 4 more in every run, despite very different attack configurations. This is a property of the model and seed, confirmed by a row-level comparison, not an attack signal.
<!-- src: docs/contribution_b_results.md -->

**Two Flower harnesses.** The repository holds two Flower apps, and only `federated/xfed_federated/`, run as `flwr run federated local-simulation`, produced any number in this report. The root project file once pointed a bare `flwr run` at the early prototype in `src/federated/`, which never implemented best-by-validation selection. That pointer was removed, so a bare `flwr run` now fails at once with a configuration error instead of training against the wrong harness. The prototype itself was left on disk, unused and unchanged.

**Open question.** It is not established whether the failure of Krum, trimmed mean and ByzAgent to detect these attacks is general to those mechanisms against label flipping, or is entangled with this project's worst-case attacker-selection rule, which selects along the same axis that the mechanisms are shown to be sensitive to. This is a live, unresolved question for whatever design follows.
