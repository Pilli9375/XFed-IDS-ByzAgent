# Results and Discussion

This chapter presents what the system achieved and what the two checks found. Detection accuracy comes first, because both checks run on the same trained models. The explanation check and the trust check follow in separate sections. They are different experiments with different evidence, and no claim in this chapter combines them. The chapter ends with efficiency, the negative and null results, the limitations, and the challenges we met while building the system.

## Detection Accuracy {#sec:r-accuracy}

### Choosing the metric

We report macro-F1 rather than accuracy. Benign traffic is about three quarters of the data, so a model that labels nearly every flow Benign scores a high accuracy while missing most attacks. Macro-F1 computes the F1 score (the harmonic mean of precision and recall) for each class separately and then averages the classes with equal weight. A model that ignores a small family such as WebAttack therefore loses a full seventh of its headline score, however rare that family is. The headline macro-F1 averages the seven families above the 1,000-flow floor; Infiltration and Heartbleed are reported per class only.
<!-- src: data/README.md; PROJECT_INSTRUCTIONS.md -->

### Federated and centralized results

@tab:acc-headline gives the test macro-F1 of every model. Each value is a single test evaluation of a checkpoint that was chosen on validation.

Table: Headline test macro-F1 (seven classes): mean ± standard deviation across 3 seeds {#tab:acc-headline}
| Model | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Centralized MLP | 0.9900 ± 0.0022 | 0.9900 ± 0.0022 | 0.9900 ± 0.0022 |
| XGBoost | 0.9946 ± 0.0001 | 0.9946 ± 0.0001 | 0.9946 ± 0.0001 |
| FedAvg | 0.516 ± 0.048 | 0.941 ± 0.057 | 0.990 ± 0.001 |
| FedAvgM, momentum 0.9 (preregistered, test once) | 0.5930 ± 0.0632 | 0.9852 ± 0.0005 | 0.9911 ± 0.0005 |
<!-- src: PROJECT_INSTRUCTIONS.md -->

The centralized references do not depend on α, so their values repeat across the columns. Three readings follow from the table.

At α=5.0, the near-IID control, FedAvg matches the centralized MLP. Federation itself costs nothing when the silos hold similar data.
<!-- src: PROJECT_INSTRUCTIONS.md -->

At α=0.5, the mean of 0.941 hides one weak seed. Seeds 42 and 1337 reach 0.9753 and 0.9866, while seed 2024 reaches only 0.8605. The large standard deviation comes from that one run, not from general instability.
<!-- src: results/inspection/best_rounds_manifest.json; docs/contribution_a_results.md -->

At α=0.1, entire families are lost. Averaged over seeds, Bot reaches a test F1 of only 0.1253 and WebAttack 0.0490, while BruteForce, DoS and PortScan vary a great deal from one seed to the next. The global model at this skew is a different, weaker detector.
<!-- src: results/aggregated/federated_per_family.csv -->

@fig:val-curves shows the validation curves of all nine FedAvg runs. At α=0.1 and α=0.5 the curves jump between rounds, which is why the round kept from each run must be chosen on validation. In one run (α=5.0, seed 42), round 20 scores 0.118 below the run's best validated round. We call this the round lottery: reporting the last round instead of the best validated one would change results by more than many of the effects we study.
<!-- src: PROJECT_INSTRUCTIONS.md; results/federated/round_lottery_val.csv -->

![Round-by-round validation macro-F1 of all nine FedAvg runs, with an open marker at each run's best validated round](docs/report/figs/fig_val_curves.png){#fig:val-curves width=15.5}

The preregistered comparison (Section 6.H) used validation alone to choose FedAvg with server momentum 0.9 (FedAvgM) [@hsu2019]; its nine checkpoints were sealed first and then tested a single time. At α=0.5 it mainly removes the weak seed: seed 2024 rises from 0.8605 to 0.9856, while seed 1337 moves by −0.001. At α=0.1 it gains in each of the three seeds (+0.113, +0.058, +0.060), though α=0.1 stays far below centralized training. At α=5.0 the change is within the centralized model's own seed spread. This result is reported as an accuracy finding only. The explanation check and the trust check use the published FedAvg runs, and whether momentum changes explanation agreement was not tested.
<!-- src: docs/contribution_a_results.md -->

The dashboard serves `fedavg_a0.5_s42`, taken at round 18, whose validation macro-F1 is 0.9760. All per-run and per-class results, including the two below-floor classes, are in Section 6.D.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Explanation Check {#sec:r-expl}

### Agreement across skew levels

@tab:expl-headline and @fig:agree-alpha show how closely each eligible silo's ranking matches the global model's. Agreement falls steadily as label skew grows.

Table: Silo-versus-global explanation agreement: median [first quartile, third quartile] over eligible rows {#tab:expl-headline}
| Measure | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Jaccard@10 | 0.333 [0.250, 0.538] | 0.538 [0.429, 0.667] | 0.667 [0.538, 0.667] |
| Weighted Kendall's τ | 0.592 [0.413, 0.712] | 0.787 [0.725, 0.827] | 0.844 [0.818, 0.868] |
| Eligible / all rows | 220 / 406 | 388 / 420 | 420 / 420 |
<!-- src: PROJECT_INSTRUCTIONS.md; paper/figs/derived_values.json; site/public/data/agreement_by_alpha.json -->

The interquartile ranges were computed from `results/inspection/agreement_metrics.csv` for the project paper and are stored in `paper/figs/derived_values.json`; the medians reproduce the published values.

![Silo-versus-global explanation agreement by α. Boxes show the interquartile range and the line the median; the hatched band is the centralized-seed instability floor (panel a: Jaccard@10; panel b: weighted τ); the dashed line is the chance Jaccard@10.](docs/report/figs/fig_agreement_alpha.png){#fig:agree-alpha width=14}

Every value is well above chance. The chance Jaccard@10 for two random sets of 10 features out of 82 is 0.065, and the medians are 5.1 to 10.3 times that. The rankings therefore carry real signal at every skew level.
<!-- src: PROJECT_INSTRUCTIONS.md -->

### Reading agreement against seed noise

Chance is a low bar. The more useful question is whether a federated value differs from what random seeds produce on their own. Train three centralized models that share everything but the seed, and their median Jaccard@10 is 0.429; the medians of the individual pairs lie between 0.429 and 0.484 (@tab:floor-pairs).
<!-- src: PROJECT_INSTRUCTIONS.md -->

Table: Seed-noise floor for each pair of centralized seeds, as the median over the 14 explained rows {#tab:floor-pairs}
| Seed pair | Jaccard@10 | Weighted τ |
|---|:-:|:-:|
| 42 and 1337 | 0.484 | 0.660 |
| 42 and 2024 | 0.429 | 0.690 |
| 1337 and 2024 | 0.429 | 0.663 |
| Floor: median [range] | 0.429 [0.429, 0.484] | 0.663 [0.660, 0.690] |
<!-- src: site/public/data/headline.json; results/inspection/centralized_instability_floor.csv; docs/measurement_protocol.md -->

At α=5.0 and α=0.5, the median agreement lies above the whole range of the floor. At α=0.1, the median Jaccard@10 of 0.333 falls below the floor, while the model's test macro-F1 is still 0.516. Taken at face value, this says that at severe skew a silo's explanation agrees with the global model no better than two identically trained models with different seeds agree with each other.
<!-- src: PROJECT_INSTRUCTIONS.md -->

We read this result as **directional, not significant**. The cluster bootstrap at α=0.1, which resamples (seed, silo) clusters 10,000 times over 29 clusters, gives a 95% interval of [0.250, 0.429] for Jaccard@10 and [0.541, 0.661] for weighted τ. The Jaccard interval overlaps the floor's range of [0.429, 0.484], so the drop below the floor is not established. Intervals were computed only at α=0.1; none exists for the other two levels.
<!-- src: site/public/data/ci.json; PROJECT_INSTRUCTIONS.md -->

### Separating skew from silo size

A Dirichlet partition ties size to skew. Because a silo's size is just the total of its family shares, the smallest silos also tend to be the most lopsided. A raw correlation between agreement and size therefore restates the skew effect: silo size and Jaccard@10 correlate at r=+0.46 at α=0.1 but only r=+0.07 at α=5.0.
<!-- src: docs/contribution_a_results.md -->

Label entropy was the covariate we had planned to use for skew, and we tried it first. Once log size was held fixed, its already weak relation to agreement disappeared, and at α=0.5 the partial correlation even turned positive. Only then did we substitute the KL divergence of each silo's label mix from the global label mix. After the same conditioning, KL still predicts agreement (@tab:kl-partial). That makes size a less likely explanation, but the evidence is still observational: the same draw sets both size and skew, and size-controlled partitions turned out to be impossible to build with this partitioner.
<!-- src: docs/contribution_a_results.md -->

Table: Partial correlation between a skew measure and agreement, holding log silo size fixed (r and n only; entropy came first) {#tab:kl-partial}
| Order | Covariate | α | Partial r, Jaccard@10 | Partial r, weighted τ | n |
|---|---|:-:|:-:|:-:|:-:|
| First | Label entropy | 0.5 | +0.23 | +0.13 | 30 |
| Second | KL from global | 0.1 | −0.57 | not reported | 29 |
| Second | KL from global | 0.5 | −0.82 | −0.87 | 30 |
<!-- src: docs/contribution_a_results.md -->

### Robustness of the measurement

Three further analyses test whether the agreement numbers reflect the models rather than the measurement.

First, the SHAP additivity residual. If explanations at small silos reconstructed the model's output poorly, that alone could lower agreement. Of the 90 final-round FedAvg silo files, 3 store a residual above the worst case in the validation pool (3.336), and they belong mostly to α=0.1. Across the α=0.1 silos, the Spearman correlation between residual and Jaccard@10 is r=−0.237 (n=29). Dropping the flagged silos under a rule fixed in advance leaves the α=0.1 Jaccard@10 median at 0.333 and moves τ from 0.592 to 0.597. The full residual audit is in Section 6.F.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Second, round-wise agreement. Recomputing agreement at rounds 5, 10, 15 and 20, at reduced SHAP fidelity, shows a small decline between the fifth and the twentieth round at α=0.1 (Jaccard@10 −0.023) and α=0.5 (−0.029), while validation macro-F1 rises over the same rounds (+0.046 and +0.026). At α=5.0 it stays flat, within a spread of 0.004. This trend was not tested statistically and is reported as directional only.
<!-- src: docs/contribution_a_results.md -->

Third, checks on the explainer itself. KernelExplainer and GradientExplainer agree on the same models at median τ=0.730 (n=14); swapping per-silo backgrounds for a common one gives median τ=0.807 (n=42); and deletion and insertion curves on one configuration show every deletion AUC below the matching insertion AUC. These rule out the explainer choice and the background as the source of disagreement, and they are consistent with attributions that track model behaviour.
<!-- src: docs/contribution_a_results.md -->

### FedProx and the parity monitor

FedProx at μ=0.0005, the only μ tested, increased Jaccard@10 for every seed at α=0.5, with test macro-F1 essentially unchanged. At α=0.1 the two measures rose or fell together in every seed. With three seeds, a change in explanations cannot be told apart from a change in accuracy there, so the α=0.1 result is inconclusive. At α=5.0 there was no consistent change.
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

We also built a parity monitor that turns each silo's top-10 list into a deviation from the fleet consensus and flags outliers with a modified z-score [@iglewicz1993]. Across the whole sweep of 356 rows it flagged 3, and all of them were at α=0.5. Its flags are meaningful only when explanations are averaged over at least three draws: an earlier single-draw version raised two flags that disappeared when the same checkpoints were explained again. All per-family results, the FedProx tables, the parity-monitor details and the faithfulness numbers are in Section 6.E.
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

### What the explanation check supports

Explanation agreement falls with label skew and stays well above chance at every skew level. The claim that it reaches the seed-noise level at α=0.1 is directional: the interval reaches the floor, and only three seed pairs define that floor. KL divergence from the global label mix predicts agreement beyond silo size, observationally. This result extends Oki et al.'s finding [@oki2024] by showing where the convergence of federated explanations weakens, rather than contradicting it.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Trust Check {#sec:r-trust}

The trust check stands apart from the explanation check as its own experiment. It runs at α=0.5, seed 42, with 10 silos and 20 rounds, against the worst-case attacker sets described in @sec:m-trust. By design, each of these was run only once: the Phase 2 baselines, the six-cell history matrix of Phase 4, and the gradual attack. The full record of all phases is in Section 6.G.
<!-- src: docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

### Is the attack worth detecting?

@tab:attack-gate reports all four statistics of validation macro-F1 for the clean run and the poisoned runs. Under every attack the last-five average falls, by between 3.7 and 7.7 points, and the attacker sets that cover more of each family cause the bigger falls. The maximum barely moves. A constant-fraction attack shifts the whole curve, and the maximum of a curve is almost blind to such a shift (@fig:phase0). This is why every attack comparison reports both statistics, and why the deployed checkpoint is still chosen by the maximum.
<!-- src: docs/contribution_b_results.md -->

Table: Phase 0: validation macro-F1 over 20 rounds, clean against poisoned (change against clean in brackets) {#tab:attack-gate size=9.5}
| Statistic | Clean | {0,1,9} (retired rule) | {0,3,5}, f=3 | {0,3}, f=2 |
|---|:-:|:-:|:-:|:-:|
| Mean | 0.8535 | 0.8180 (−0.0355) | 0.8236 (−0.0299) | 0.8253 (−0.0282) |
| Median | 0.8487 | 0.8436 (−0.0051) | 0.8438 (−0.0048) | 0.8489 (+0.0003) |
| Final-5 mean | 0.9513 | 0.9143 (−0.0370) | 0.8746 (−0.0766) | 0.8787 (−0.0726) |
| Max | 0.9760 | 0.9710 (−0.0049) | 0.9763 (+0.0004) | 0.9867 (+0.0107) |
<!-- src: docs/contribution_b_results.md -->

![Seed-42 validation macro-F1 curves for the clean run and each poisoned run, with the last five rounds shaded](docs/report/figs/fig_phase0_curves.png){#fig:phase0 width=11}

### Which statistics carry the attack?

Only one of the five statistics separates the malicious silos clearly (@tab:glass-summary). For training loss, Glass's δ under attack is 33.8 times as large as for the same silos with no attack when f=3, and 154.3 times as large when f=2. Both ratios describe effect size at seed 42; neither is a threshold. A per-round loss threshold tuned on seed 42 failed at seed 1337, flagging only 0.017 of the poisoned silo-rounds, compared with 0.483 in the agent's own log. The three geometric statistics show weak separation or none. Validation accuracy points the wrong way: once attack flows are relabelled as Benign, a malicious silo scores better on a validation set that is mostly Benign.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

Table: Phase 1: ratio of Glass's δ in the poisoned run to the same silos in a clean control run {#tab:glass-summary}
| Statistic | f=3 ratio | f=2 ratio | Reading |
|---|:-:|:-:|---|
| train_loss | 33.8× | 154.3× | Clear separation |
| cosine_to_peer_mean | 1.11× | 1.17× | Within natural variance |
| update_norm | 1.12× | 1.67× | Within natural variance |
| cosine_to_global | 0.93× | 0.86× | None; poisoned run smaller |
| val_accuracy | 0.31× | 0.31× | Attack narrows the natural gap |
<!-- src: docs/contribution_b_results.md -->

### The classical rules

None of the classical rules identified the attackers. Multi-Krum excluded a malicious silo 0% of the time. Chance alone would have given 0.30 at f=3 and 0.20 at f=2. What it dropped, round after round and whether or not anyone attacked, were the big silos that hold mostly Benign traffic; in the run with no attacker it dropped exactly silos {2,7,9} in all 20 rounds. At f=2 its recovery fraction of 1.3490 looks like success, but it comes from composition. With those big silos gone, the attackers, still fully counted, made up 21.0% of what remained instead of 9.8%, and macro-F1 rose because the label mix became more balanced, not because anything was mitigated. Classical Krum's exclusions are chance-level: it keeps 1 of 10 every round.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

Trimmed mean also reacted mainly to composition. Splitting the clean silos into ordinary ones and large Benign-heavy ones shows the composition excess in trim rate (+0.1714 at f=3) to be larger than the malicious excess (+0.1522). Defending when nobody attacks has a price, too. Measured in test macro-F1 against undefended FedAvg, the cost is −22.7 points for Krum, −4.9 for Multi-Krum and −1.6 for trimmed mean.
<!-- src: docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

### ByzAgent

Under the f=3 attack at seed 42, ByzAgent flagged a malicious silo in every one of its 60 silo-rounds. Read alone, that figure misleads. With no attack at all, those silos were flagged at rates between 0.95 and 1.00, and so was silo 8, which never attacked. All four are the four lowest-Benign silos at that seed, with 9.2%, 0.3%, 0.1% and 12.3% Benign traffic against 81.5% to 98.0% for every other silo. At seed 42, the lift of a malicious silo over its own clean-run rate is at most +0.05.
<!-- src: docs/contribution_b_results.md -->

Seeds 1337 and 2024 changed the picture. At those seeds composition is graded rather than split into two groups, and lift appears wherever the clean-run rate is low (@tab:lift and @fig:lift). Silo 5 shows a lift of +0.95 at seed 1337 and +0.75 at seed 2024, and silo 3 shows +0.40 at seed 1337. Where a silo's clean rate is already at the ceiling, as for silo 3 at seed 2024 (clean rate 1.00), lift stays flat.
<!-- src: docs/contribution_b_results.md -->

Table: ByzAgent lift over each malicious silo's own clean-run flag rate, f=3 sudden attack {#tab:lift}
| Seed | Silo 0 | Silo 3 | Silo 5 |
|---|:-:|:-:|:-:|
| 42 | +0.05 | +0.00 | +0.00 |
| 1337 | +0.05 | +0.40 | +0.95 |
| 2024 | +0.35 | −0.05 | +0.75 |
<!-- src: docs/contribution_b_results.md -->

![Share of rounds in which ByzAgent flagged each attacking silo: open markers for the run without attack, filled markers for the f=3 sudden attack, at all three seeds; the horizontal gap is the lift](docs/report/figs/fig_byzagent_lift.png){#fig:lift width=12}

We state the conclusion of this part in the wording the project fixed for it:

> "Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition."
<!-- src: PROJECT_INSTRUCTIONS.md -->

We could not build the obvious control, an attacker of the same strength made from ordinary silos. Here, a silo holds enough attack traffic to be a strong attacker only if its Benign share is low, so the two properties coincide; the six silos with the most Benign traffic hold just 211 Bot rows between them, out of 3,174 in the whole federation. We therefore cannot say whether the failures of the classical rules are general to those rules or tied to our worst-case selection.
<!-- src: docs/contribution_b_results.md -->

### How faithful is the agent's rationale?

ByzAgent produces decisions plus a rationale of measured fidelity. Measured, that fidelity turns out to be partial. The strict citation error, meaning the share of quoted values that do not match the data, was 11.7% at seed 42 and 22.5% at seeds 1337 and 2024. At the two later seeds, update norm still appeared in about 59% of the agent's explanations, although its correlation with the agent's decisions had dropped from +0.419 to −0.076. Training loss, the statistic that actually carries the attack, stayed under-cited.
<!-- src: docs/contribution_b_results.md -->

Shown five rounds of history, the agent described trends wrongly about 35 to 45% of the time. Its output also changes from call to call: asking three times about round 10 gave identical decisions in 27 of 30 cases, while all 30 agreed on whether a silo was trusted or flagged. The history-based variant did not pass the test written before it ran, since a silo that never attacked was flagged just as often as the attackers.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

### What the trust check supports

The attack is built to be worst-case, and the rule that picks attackers chooses them by composition, the very property all the detectors respond to. Every mechanism tested reacted to composition. The classical rules never picked out the attackers. ByzAgent did react to the attack as well, though only for silos whose flag rate was not already at the top. Some of its stated reasons are wrong, repeated calls can disagree, and its history-based version failed. ByzAgent is not shown to outperform the classical rules, and this report makes no such claim.

## Efficiency {#sec:r-efficiency}

@tab:eff-summary summarises the serving and communication measurements. They were taken on validation rows only.

Table: Serving and communication measurements (CPU, one laptop) {#tab:eff-summary}
| Quantity | Value |
|---|---|
| Per-flow latency p50, ONNX Runtime fp32 / PyTorch (median of 3 sessions) | 45.7 µs / 186.5 µs |
| Throughput at batch 1024, ONNX Runtime fp32 / PyTorch (rows per second) | 1,071,700 / 1,482,368 |
| Traffic per round, fp32, 10 silos, both directions | 1,587,920 bytes (793,960 each way) |
| Uplink saving, fp16 / int8 update compression | 50.0% / 74.9% |
| Change in best-by-validation macro-F1, fp16 / int8 (mean, 3 seeds) | −0.0007 / −0.0011 |
| Wall time per round, median of 500 rounds | 51.4 s |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

On every one of the 143,513 validation rows, ONNX Runtime in fp32 predicts exactly what PyTorch predicts, and it handles a single flow about four times faster, so the backend now uses it by default. At batch 1024 PyTorch is faster. Dynamic int8 quantization was tried and dropped: it changed only a small share of predictions, but those fell on small classes, and validation macro-F1 fell by 0.1428. Compressing updates cuts the bytes sent by a known amount; whether it changes accuracy cannot be seen with three seeds. A loss-based pre-screen that would send only suspicious silos to the agent was replayed offline and rejected, because the seed-42 threshold did not transfer to seed 1337. Full tables are in Section 6.I.
<!-- src: docs/efficiency_results.md -->

## Negative and Null Results {#sec:r-negative}

@tab:negative gathers each idea that failed or could not be confirmed, together with the sections that report it. We list them together so that none is lost among the positive results.

Table: Failed, null and unconfirmed results {#tab:negative size=9.5}
| Hypothesis or attempt | Outcome | Reported in |
|---|---|---|
| Agreement at α=0.1 is below seed noise | Directional, not significant: the intervals overlap | 4.2, 6.E |
| Label entropy explains agreement beyond size | Failed conditioning on log size; the sign flipped | 4.2, 6.E |
| Size-controlled partitions | Impossible under this partitioner | 4.2, 6.E |
| Agreement converges with accuracy over rounds | Declines at α ≤ 0.5; untested, reduced fidelity | 4.2, 6.E |
| FedProx μ=0.0005 improves agreement | Inconclusive at α=0.1; no effect at α=5.0; one μ only | 4.2, 6.E |
| FedProx μ=0.01 | Collapsed (validation macro-F1 0.7114) | 6.C |
| Single-draw parity flags | Artifacts; at least three draws are needed | 4.2, 6.E |
| DeepExplainer on this model | Fails on LayerNorm (additivity error 2.43) | 2.2, 6.E |
| GPU for SHAP | About 3 times slower than the CPU | 2.4, 6.E |
| Bot and WebAttack near-duplication inflates agreement | Tested, not confirmed | 6.E |
| An earlier "3–8%" residual figure | No backing file; dropped | 6.F |
| Geometry statistics separate attackers | Weak to null; validation accuracy inverts | 4.3, 6.G |
| Multi-Krum excludes attackers | Multi-Krum excluded a malicious silo 0% of the time; its f=2 "success" is an artifact | 4.3, 6.G |
| Classical Krum and trimmed mean | Krum fails; the trimmed-mean f=2 success is not shown to be attack-related | 4.3, 6.G |
| ByzAgent detects the attack at seed 42 | Lift at most +0.05: a ceiling artifact | 4.3, 6.G |
| A compositionally matched control attack | Not constructible in this partition | 4.3, 6.G |
| The agent's rationale is faithful | Strict citation error 11.7% to 22.5%; update norm mis-cited | 4.3, 6.G |
| A fixed attacker set is worst-case at every seed | No: rank 8 and 33 of 120 at the other seeds | 6.G |
| Rolling history separates attack from composition | Failed its preregistered test | 4.3, 6.G |
| The agent's trend claims are reliable | About 35–45% contradict the data | 4.3, 6.G |
| A live outcome-level ByzAgent run; Krum in gradual mode | Not run: it would inherit the confound or could not change the verdict | 6.G |
| FedAdam and FedYogi as optimizers | Failed the α=0.5 guard | 6.H |
| Five of the nine preregistered candidates | Not run, for budget reasons | 6.H |
| int8 serving | Validation macro-F1 −0.1428; dropped | 4.4, 6.I |
| Update compression keeps accuracy | No detectable effect either way at n=3 | 4.4, 6.I |
| A train_loss pre-screen in front of ByzAgent | The seed-42 threshold did not transfer (0.017 against 0.483) | 4.4, 6.I |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/test_set_exposure_audit.md -->

## Limitations {#sec:r-limitations}

The limitations below bound every claim in this chapter. They are grouped by experiment; the full list from the canonical results documents is reproduced in Sections 6.E and 6.G.

**Shared by both checks.** Three seeds were used throughout, because every seed is a full training run. The silos of one run all train from the same global models, so they are not independent; the real sample size is nearer the count of runs than the count of silo rows, and we therefore give no p-values. Everything ran in simulation on one machine, so no real network, latency or client failure was involved. The data is a single benchmark, CICIDS2017, and conclusions may not carry over to other traffic.
<!-- src: docs/contribution_a_results.md -->

**Explanation check.** The α=0.1 result is directional, not significant, and the seed-noise floor rests on only three seed pairs. No seed was set for SHAP's sampling when the headline values were computed. The chance level assumes that features are equally likely to be important, which real rankings are not. The faithfulness check covers one configuration and three of ten silos. Agreement anchors on the true class by design, which deliberately excludes disagreement about the prediction itself. SHAP's background replaces a missing feature with an average that is not a real network flow. Only top-k lists cross the boundary, so server-side analyses see a compressed summary of each silo's explanation. FedProx was run at one μ only. Silo size and skew cannot be separated experimentally with this partitioner.
<!-- src: docs/contribution_a_results.md -->

**Trust check.** The attack is worst-case, not a model of a real attacker, and the baselines were handed the true f. Each of the baseline runs, the history matrix and the gradual attack exists once. The attacker-selection rule is entangled with the composition axis that the detectors react to, and that entanglement is unresolved. A fixed attacker set chosen at seed 42 is a weaker and different attack at the other seeds. The agent's decisions vary between calls, and its rationale is only partly faithful. The seed-1337 silo-0 result cannot be attributed cleanly, because that silo held very little poisonable data at that seed.
<!-- src: docs/contribution_b_results.md -->

**System.** The dashboard's LLM sentences are a usability feature with no research claim behind them. Hot-swap retraining is an engineering feature of the live system, not an experiment.

## Challenges Faced and How We Solved Them {#sec:r-challenges}

Building the system meant working through a series of problems. The ones below are recorded in the project's documents or in its git history. Each is listed with what went wrong and what we did about it.

**DeepExplainer failed on LayerNorm.** SHAP's DeepExplainer, the natural choice for a neural network, produced an additivity error of 2.43 on our model because of its LayerNorm layers. A probe confirmed the failure, and we switched to GradientExplainer, whose residuals we then measured and disclosed (Section 6.F) instead of assuming them away.
<!-- src: PROJECT_INSTRUCTIONS.md -->

**RobustScaler degenerated.** RobustScaler is the usual choice for heavy-tailed flow features, but 28 of the 82 features have an interquartile range of zero, which leaves them unscaled or degenerate. The scaler pilot showed the robust variants far behind on validation, so the StandardScaler was locked.
<!-- src: PROJECT_INSTRUCTIONS.md -->

**BatchNorm does not federate.** BatchNorm keeps running statistics of each silo's own data, and averaging those across very different silos produces meaningless values. LayerNorm, which normalises within a single example and keeps no running statistics, was locked in its place.

**The Flower runtime trained on the CPU.** We assumed federated training used the GPU. Flower builds an isolated runtime environment, and checking its installed packages showed the CPU build of PyTorch. The Flower app's dependencies were pinned on 2026-10-12 to the versions that the published runs had used, so that new runs reproduce the same numerics, and the project's hardware note was corrected on 2026-10-13.
<!-- src: federated/pyproject.toml; PROJECT_INSTRUCTIONS.md -->

**The round lottery.** Under non-IID data, validation macro-F1 can swing by up to 0.118 between the best round and round 20 of the same run. Reporting the final round would have been arbitrary, so every reported number uses the best-by-validation round. The first version of this comparison relied on test scores; on 2026-10-13 it was rebuilt from validation curves alone.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/test_set_exposure_audit.md -->

**Test-set exposure was found and fixed.** An audit of every read of the test set found that three design rationales had quoted test scores, that client-side test scoring was still logged every round, and that the dashboard simulator replayed test rows. We re-checked each choice on validation (all three survived), turned the legacy test scoring off by default, switched the simulator to validation rows, wrote the full audit, and agreed that from then on the test set would be used once more, for a single preregistered configuration, and never otherwise.
<!-- src: docs/test_set_exposure_audit.md; PROJECT_INSTRUCTIONS.md -->

**Single-draw parity flags were artifacts.** The first parity monitor flagged two silos that disappeared when the same checkpoints were explained again. The cause turned out to be one explainer draw with an unusual number of tied values, which pushed the median absolute deviation for that round down to 0.042. The fix explains every checkpoint three times with fixed seeds and averages before thresholding.
<!-- src: docs/contribution_a_results.md -->

**Entropy failed as the skew covariate.** The planned covariate, label entropy, lost its effect, and even changed sign, once silo size was controlled. We report this failure and the switch to KL divergence in that order, rather than presenting KL as if it had been the plan.

**Rolling history failed.** Giving ByzAgent five-round histories was meant to separate an attack, which changes over time, from composition, which does not. The preregistered rule judged it a failure: an innocent silo was flagged as often as the real attackers, repeated decisions agreed less often, and many descriptions of trends were false. We kept the negative result and did not tune the prompt afterwards.

**The seed-42 null was partly a ceiling.** The first ByzAgent results suggested that the agent detected composition and nothing else. Running two more seeds showed that seed 42's malicious silos were already flagged at the ceiling with no attack present, so lift could not appear there. The claim was revised to the locked wording above instead of being dropped or overstated.
<!-- src: docs/contribution_b_results.md -->

**Unbacked numbers were removed.** A "3–8%" figure for SHAP residuals had circulated in early notes with no file behind it. It was replaced by values computed from a 500-row validation pool. A claim that an `agent_config.json` file recorded the agent's information asymmetry was also found to be false, because no such file exists; the claim was corrected rather than back-filled.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

**Hot-swap retraining crashed in-process.** The first hot-swap proof runs crashed twice when heavy parquet reads followed torch training in the same process. Retraining was moved into a separate worker process that the backend starts and monitors, so a crash can never take down the served model.
