# Results and Discussion

The results come in two separate parts, the explanation check and the trust check, preceded by detection accuracy, which both share, and followed by efficiency, negative results and limitations. No claim here combines the two checks.

## Detection Accuracy {#sec:r-accuracy}

We report macro-F1, the unweighted mean of per-class F1, instead of accuracy. Benign is about three quarters of all flows, so a detector that misses rare attack families can still score a high accuracy, whereas macro-F1 counts each of the seven headline families equally. @tab:acc-headline gives the test results; each is one evaluation of a checkpoint chosen on validation.
<!-- src: data/README.md; PROJECT_INSTRUCTIONS.md -->

Table: Headline test macro-F1 (seven classes): mean ± standard deviation over 3 seeds {#tab:acc-headline}
| Model | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Centralized MLP | 0.9900 ± 0.0022 | 0.9900 ± 0.0022 | 0.9900 ± 0.0022 |
| XGBoost | 0.9946 ± 0.0001 | 0.9946 ± 0.0001 | 0.9946 ± 0.0001 |
| FedAvg | 0.516 ± 0.048 | 0.941 ± 0.057 | 0.990 ± 0.001 |
| FedAvgM, momentum 0.9 (preregistered, test once) | 0.5930 ± 0.0632 | 0.9852 ± 0.0005 | 0.9911 ± 0.0005 |
<!-- src: PROJECT_INSTRUCTIONS.md -->

FedAvg matches the centralized model in the near-IID control (α=5.0). At α=0.5 the mean drops because seed 2024 reaches only 0.8605. At α=0.1 entire families disappear: averaged over seeds, Bot scores an F1 of 0.1253 and WebAttack 0.0490. Choosing each run's round on validation matters: within one run, the best validated round and round 20 differ by up to 0.118.
<!-- src: PROJECT_INSTRUCTIONS.md; results/aggregated/federated_per_family.csv; results/inspection/best_rounds_manifest.json -->

@fig:val-curves plots validation macro-F1 round by round for each FedAvg run; @tab:perclass breaks test F1 down by class, with Infiltration and Heartbleed shown separately.

![Round-by-round validation macro-F1 of all nine FedAvg runs, with an open marker at each run's best validated round](docs/report/figs/fig_val_curves.png){#fig:val-curves width=15.5}

Table: Per-class test F1: mean over 3 seeds (FedAvg also shows the standard deviation) {#tab:perclass size=9.5}
| Class | FedAvg α=0.1 | FedAvg α=0.5 | FedAvg α=5.0 | Centralized MLP | XGBoost |
|---|:-:|:-:|:-:|:-:|:-:|
| Benign | 0.9449 ± 0.0130 | 0.9984 ± 0.0004 | 0.9993 ± 0.0000 | 0.9973 | 0.9996 |
| Bot | 0.1253 ± 0.1003 | 0.9404 ± 0.0410 | 0.9696 ± 0.0012 | 0.9733 | 0.9804 |
| BruteForce | 0.5730 ± 0.4182 | 0.9929 ± 0.0023 | 0.9954 ± 0.0002 | 0.9972 | 0.9978 |
| DDoS | 0.9976 ± 0.0018 | 0.9998 ± 0.0001 | 0.9999 ± 0.0001 | 1.0000 | 1.0000 |
| DoS | 0.6025 ± 0.4308 | 0.9947 ± 0.0047 | 0.9979 ± 0.0000 | 0.9981 | 0.9987 |
| PortScan | 0.3197 ± 0.4521 | 0.9965 ± 0.0005 | 0.9974 ± 0.0000 | 0.9813 | 0.9987 |
| WebAttack | 0.0490 ± 0.0693 | 0.6627 ± 0.4207 | 0.9691 ± 0.0058 | 0.9831 | 0.9870 |
| Infiltration (per class only) | 0.0000 ± 0.0000 | 0.3767 ± 0.0669 | 0.4362 ± 0.0502 | 0.7954 | 0.8148 |
| Heartbleed (per class only) | 0.3333 ± 0.4714 | 0.6000 ± 0.4320 | 0.9524 ± 0.0673 | 1.0000 | 1.0000 |
<!-- src: results/aggregated/federated_per_family.csv; results/aggregated/centralized_per_family.csv; results/aggregated/xgboost_per_family.csv -->

@tab:collapse lists the runs and families whose test recall is essentially zero.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Families with near-zero test recall in FedAvg runs {#tab:collapse}
| α | Seed | Family | Recall | Precision | Test support |
|:-:|:-:|---|:-:|:-:|---:|
| 0.1 | 42 | Bot | 0.0 | 0.0 | 1,176 |
| 0.1 | 42 | PortScan | 0.0 | 0.0 | 46,540 |
| 0.1 | 1337 | BruteForce | 0.0 | 0.0 | 1,743 |
| 0.1 | 1337 | DoS | 0.00002 | 1.0 | 44,373 |
| 0.1 | 1337 | WebAttack | 0.0 | 0.0 | 514 |
| 0.1 | 2024 | PortScan | 0.0 | 0.0 | 46,540 |
| 0.1 | 2024 | WebAttack | 0.0 | 0.0 | 514 |
| 0.5 | 2024 | WebAttack | 0.0350 | 1.0 | 514 |
<!-- src: results/aggregated/federated_collapse.csv -->

The FedAvgM row is the single preregistered test evaluation. Server momentum 0.9 [@hsu2019] was chosen on validation from four candidates, and its sealed checkpoints were tested once. It removes the weak α=0.5 seed (0.8605 to 0.9856) and improves every α=0.1 seed, though α=0.1 stays far below centralized training. The explanation and trust checks that follow were run on FedAvg, not on FedAvgM. The dashboard serves `fedavg_a0.5_s42` at round 18 (validation macro-F1 0.9760).
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

@tab:prereg-val lists the validation means on which the choice was made.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Validation selection: mean best-by-validation macro-F1 per candidate {#tab:prereg-val}
| Candidate | α=0.1 mean | α=0.5 mean | Guard (at least 0.9325) |
|---|:-:|:-:|:-:|
| FedAvg (published baseline) | 0.5228 | 0.9425 | n/a |
| FedAvgM, momentum 0.5 | 0.5386 | 0.9502 | Pass |
| FedAvgM, momentum 0.9 | 0.6068 | 0.9861 | Pass; selected |
| FedAdam, η=0.01 | 0.4583 | 0.8482 | Fail |
| FedYogi, η=0.01 | 0.4627 | 0.9004 | Fail |
<!-- src: docs/preregistration_accuracy.md -->

## Explanation Check {#sec:r-expl}

@tab:expl-headline and @fig:agree-alpha show how closely each eligible silo's SHAP ranking matches the global model's. Agreement falls steadily as skew grows, and every median is 5.1 to 10.3 times the chance Jaccard@10 of 0.065.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Table: Silo-versus-global explanation agreement: median [first quartile, third quartile] {#tab:expl-headline}
| Measure | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Jaccard@10 | 0.333 [0.250, 0.538] | 0.538 [0.429, 0.667] | 0.667 [0.538, 0.667] |
| Weighted Kendall's τ | 0.592 [0.413, 0.712] | 0.787 [0.725, 0.827] | 0.844 [0.818, 0.868] |
<!-- src: PROJECT_INSTRUCTIONS.md; paper/figs/derived_values.json -->

@tab:agree-family-j breaks Jaccard@10 down by attack family.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Jaccard@10 by family: median [first quartile, third quartile], with n eligible rows {#tab:agree-family-j size=9.5}
| Family | n, α=0.1 | α=0.1 | n, α=0.5 | α=0.5 | n, α=5.0 | α=5.0 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Benign | 46 | 0.333 [0.250, 0.538] | 56 | 0.538 [0.429, 0.667] | 60 | 0.667 [0.538, 0.667] |
| Bot | 26 | 0.250 [0.176, 0.405] | 54 | 0.484 [0.429, 0.538] | 60 | 0.538 [0.429, 0.667] |
| BruteForce | 28 | 0.333 [0.250, 0.538] | 52 | 0.538 [0.429, 0.667] | 60 | 0.667 [0.538, 0.667] |
| DDoS | 34 | 0.381 [0.250, 0.538] | 60 | 0.603 [0.538, 0.667] | 60 | 0.818 [0.667, 0.818] |
| DoS | 38 | 0.381 [0.250, 0.538] | 60 | 0.538 [0.429, 0.667] | 60 | 0.667 [0.667, 0.818] |
| PortScan | 32 | 0.250 [0.176, 0.429] | 58 | 0.538 [0.538, 0.667] | 60 | 0.667 [0.538, 0.818] |
| WebAttack | 16 | 0.292 [0.250, 0.333] | 48 | 0.538 [0.429, 0.667] | 60 | 0.538 [0.538, 0.667] |
<!-- src: paper/figs/derived_values.json -->

![Explanation agreement by α: boxes show the interquartile range, the hatched band is the seed-noise floor, the dashed line is the chance Jaccard@10](docs/report/figs/fig_agreement_alpha.png){#fig:agree-alpha width=13}

The key comparison is with seed noise. If three centralized models are trained with different seeds and nothing else changed, their median Jaccard@10 is 0.429 (range of the three pairs: 0.429 to 0.484). At α=0.5 and α=5.0, federated agreement lies above that range. At α=0.1 it falls below it, at 0.333, while test macro-F1 is still 0.516. This result is **directional, not significant**: the α=0.1 cluster-bootstrap interval, [0.250, 0.429], overlaps the floor's range.
<!-- src: PROJECT_INSTRUCTIONS.md; site/public/data/ci.json -->

@tab:floor-pairs gives the floor for each pair of seeds.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Seed-noise floor for each pair of centralized seeds, as the median over the 14 explained rows {#tab:floor-pairs}
| Seed pair | Jaccard@10 | Weighted τ |
|---|:-:|:-:|
| 42 and 1337 | 0.484 | 0.660 |
| 42 and 2024 | 0.429 | 0.690 |
| 1337 and 2024 | 0.429 | 0.663 |
| Floor: median [range] | 0.429 [0.429, 0.484] | 0.663 [0.660, 0.690] |
<!-- src: site/public/data/headline.json; results/inspection/centralized_instability_floor.csv; docs/measurement_protocol.md -->

Silo size and skew come from the same Dirichlet draw, so they cannot be varied separately. Label entropy, the covariate planned first, lost its link with agreement once log size was held fixed. KL divergence from the global label mix, tried next, kept it: partial r=−0.57 at α=0.1 (n=29) and −0.82 for Jaccard@10 and −0.87 for τ at α=0.5 (n=30). The evidence is observational. Three robustness checks support the measurement: dropping silos with large SHAP additivity residuals under a rule fixed in advance leaves the α=0.1 median at 0.333; KernelExplainer and GradientExplainer agree at median τ=0.730; and deletion and insertion curves behave as faithful attributions should, in a single spot-check. With FedProx (μ=0.0005), agreement rose for every seed at α=0.5 while accuracy stayed level; at α=0.1 the outcome was inconclusive, and at α=5.0 nothing changed.
<!-- src: docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

@tab:fedprox-agree compares FedProx with FedAvg seed by seed, @tab:parity lists the three flags of the parity monitor, which compares silos' top-10 lists and needs three seeded explainer draws, and @tab:faith gives the faithfulness spot-check.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md -->

Table: FedAvg against FedProx (μ=0.0005): mean agreement over eligible rows, per seed {#tab:fedprox-agree size=9.5}
| α | Seed | J@10 FedAvg | J@10 FedProx | Δ | τ FedAvg | τ FedProx | Δ |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 0.1 | 42 | 0.3257 | 0.3917 | +0.0660 | 0.5078 | 0.6176 | +0.1098 |
| 0.1 | 1337 | 0.3979 | 0.3312 | −0.0667 | 0.6147 | 0.5689 | −0.0458 |
| 0.1 | 2024 | 0.3301 | 0.4109 | +0.0808 | 0.5331 | 0.6265 | +0.0934 |
| 0.5 | 42 | 0.5444 | 0.5707 | +0.0263 | 0.7545 | 0.7647 | +0.0102 |
| 0.5 | 1337 | 0.5096 | 0.5269 | +0.0173 | 0.7318 | 0.7565 | +0.0247 |
| 0.5 | 2024 | 0.6167 | 0.6209 | +0.0042 | 0.7913 | 0.7904 | −0.0009 |
| 5.0 | 42 | 0.6406 | 0.6441 | +0.0035 | 0.8415 | 0.8396 | −0.0018 |
| 5.0 | 1337 | 0.6688 | 0.6593 | −0.0095 | 0.8385 | 0.8330 | −0.0055 |
| 5.0 | 2024 | 0.6269 | 0.6732 | +0.0463 | 0.8373 | 0.8391 | +0.0018 |
<!-- src: docs/contribution_a_results.md -->

Table: Parity-monitor flags (three-draw average) {#tab:parity}
| Run | Seed | Silo | Deviation |
|---|:-:|:-:|:-:|
| `fedavg_a0.5_s1337` | 1337 | 7 | 0.775 |
| `fedavg_a0.5_s2024` | 2024 | 3 | 0.530 |
| `fedavg_a0.5_s2024` | 2024 | 6 | 0.535 |
<!-- src: docs/contribution_a_results.md -->

Table: Deletion AUC (lower is better) and insertion AUC (higher is better), α=0.5, seed 42 {#tab:faith}
| Model | Deletion AUC | Insertion AUC |
|---|:-:|:-:|
| Global | 0.167 | 0.696 |
| Silo 0 | 0.274 | 0.800 |
| Silo 1 | 0.166 | 0.628 |
| Silo 2 | 0.179 | 0.655 |
<!-- src: docs/contribution_a_results.md -->

@tab:kl-partial gives the partial correlations and @fig:kl-scatter the per-silo values; @fig:roundwise shows how agreement and accuracy moved over the rounds (reduced SHAP fidelity, a directional check only).
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Partial correlation between a skew measure and agreement, holding log silo size fixed (r and n only; entropy came first) {#tab:kl-partial}
| Order | Covariate | α | Partial r, Jaccard@10 | Partial r, weighted τ | n |
|---|---|:-:|:-:|:-:|:-:|
| First | Label entropy | 0.5 | +0.23 | +0.13 | 30 |
| Second | KL from global | 0.1 | −0.57 | not reported | 29 |
| Second | KL from global | 0.5 | −0.82 | −0.87 | 30 |
<!-- src: docs/contribution_a_results.md -->

![Jaccard@10 at the final round plotted against each silo's KL divergence from the overall label mix; seed 42 uses filled markers, seeds 1337 and 2024 open squares and triangles](docs/report/figs/fig_kl_scatter.png){#fig:kl-scatter width=12}

![Round-wise mean Jaccard@10 (a) and mean validation macro-F1 (b) by α](docs/report/figs/fig_round_wise.png){#fig:roundwise width=13}

## Trust Check {#sec:r-trust}

This experiment runs at α=0.5 and seed 42 with 10 silos and 20 rounds, against the worst-case attacker sets of @sec:m-trust; each baseline, the history matrix and the gradual attack have one run. The attack is worth detecting: the final-five mean of validation macro-F1 falls from 0.9513 to 0.8746 at f=3 and to 0.8787 at f=2, while the maximum, which picks the deployed checkpoint, barely moves (0.9760 to 0.9763 and 0.9867). Training loss is the one statistic among the five that sets the attackers apart, with a Glass's δ 33.8 times its clean-run value at f=3 and 154.3 times at f=2. These are seed-42 effect sizes, not thresholds: a loss threshold tuned on seed 42 flagged only 0.017 of poisoned silo-rounds at seed 1337, against 0.483 for the agent. Validation accuracy points the wrong way, because Benign-labelled attack rows make a malicious silo look more accurate.
<!-- src: docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

@tab:attack-gate and @fig:phase0 give the four statistics and the curves; @tab:glass-summary compares the five statistics.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Phase 0: validation macro-F1 over 20 rounds, clean against poisoned (change against clean in brackets) {#tab:attack-gate size=9.5}
| Statistic | Clean | {0,1,9} (retired rule) | {0,3,5}, f=3 | {0,3}, f=2 |
|---|:-:|:-:|:-:|:-:|
| Mean | 0.8535 | 0.8180 (−0.0355) | 0.8236 (−0.0299) | 0.8253 (−0.0282) |
| Median | 0.8487 | 0.8436 (−0.0051) | 0.8438 (−0.0048) | 0.8489 (+0.0003) |
| Final-5 mean | 0.9513 | 0.9143 (−0.0370) | 0.8746 (−0.0766) | 0.8787 (−0.0726) |
| Max | 0.9760 | 0.9710 (−0.0049) | 0.9763 (+0.0004) | 0.9867 (+0.0107) |
<!-- src: docs/contribution_b_results.md -->

@tab:gradual compares the sudden attack with a gradual one whose flip fraction rises each round.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Sudden against gradual attack on {0,3,5}: validation macro-F1 (change against clean in brackets) {#tab:gradual}
| Statistic | Clean | Sudden | Gradual |
|---|:-:|:-:|:-:|
| Mean | 0.8535 | 0.8236 (−0.0299) | 0.7958 (−0.0577) |
| Median | 0.8487 | 0.8438 (−0.0048) | 0.7993 (−0.0494) |
| Final-5 mean | 0.9513 | 0.8746 (−0.0766) | 0.8104 (−0.1408) |
| Max | 0.9760 | 0.9763 (+0.0004) | 0.9758 (−0.0002) |
<!-- src: docs/contribution_b_results.md -->

![Seed-42 validation macro-F1 curves for the clean run and each poisoned run, with the last five rounds shaded](docs/report/figs/fig_phase0_curves.png){#fig:phase0 width=11}

Table: Phase 1: ratio of Glass's δ in the poisoned run to the same silos in a clean control run {#tab:glass-summary}
| Statistic | f=3 ratio | f=2 ratio | Reading |
|---|:-:|:-:|---|
| train_loss | 33.8× | 154.3× | Clear separation |
| cosine_to_peer_mean | 1.11× | 1.17× | Within natural variance |
| update_norm | 1.12× | 1.67× | Within natural variance |
| cosine_to_global | 0.93× | 0.86× | None; poisoned run smaller |
| val_accuracy | 0.31× | 0.31× | Attack narrows the natural gap |
<!-- src: docs/contribution_b_results.md -->

**Classical rules.** Multi-Krum excluded a malicious silo 0% of the time. The chance rate is 0.30 at f=3. It dropped the large, mostly Benign silos in every round, with or without an attack, and its apparent recovery at f=2 (recovery fraction 1.3490) came from rebalancing labels, not from mitigation. Classical Krum's exclusions are chance-level: it keeps 1 of 10 every round. Defending when nobody attacks costs test macro-F1: −22.7 points for Krum, −4.9 for Multi-Krum and −1.6 for trimmed mean.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_b_results.md -->

@tab:phase2 gives every defence's outcome and @tab:exclusion its exclusion rate against the matching chance rate.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Results of the Phase 2 defences: four summaries of the 20-round validation curve, with the recovery fraction {#tab:phase2 size=9}
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

Table: Malicious-silo exclusion rate against the matching chance rate {#tab:exclusion}
| Defence | Condition | Exclusion rate | Chance rate |
|---|---|:-:|:-:|
| Multi-Krum | f=3 | 0.0000 | 0.30 |
| Multi-Krum | f=2 | 0.0000 | 0.20 |
| Classical Krum | f=3 | 1.0000 | 0.900 |
| Classical Krum | f=2 | 1.0000 | 0.900 |
<!-- src: docs/contribution_b_results.md -->

@tab:trim shows that trimmed mean, too, trims the large Benign-heavy silos more than the attackers.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Trimmed mean: how often ordinary clean silos are trimmed, and how much more often malicious silos and the large Benign-heavy silos are trimmed {#tab:trim}
| Condition | Ordinary clean | Malicious excess | Large, Benign-heavy excess |
|---|:-:|:-:|:-:|
| f=3 | 0.5030 | +0.1522 | +0.1714 |
| f=2 | 0.3191 | +0.1365 | +0.1787 |
<!-- src: docs/contribution_b_results.md -->

**ByzAgent.** At seed 42 the agent flagged the attackers in 60 of 60 silo-rounds, but the same silos, and silo 8 that never attacks, were already flagged 0.95 to 1.00 of the time with no attack; all four are the silos with the least Benign traffic. Two further seeds, 1337 and 2024, have more evenly graded compositions, and there the lift over each silo's attack-free rate shows up wherever that rate is not already near the top (@tab:lift, @fig:lift).
<!-- src: docs/contribution_b_results.md -->

@tab:agent-decisions counts the flags in each condition.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: ByzAgent flags (downweight or quarantine), seed 42, 200 silo-rounds per condition {#tab:agent-decisions}
| Condition | Malicious flagged | Clean flagged |
|---|:-:|:-:|
| Clean (no attack) | n/a | 86/200 = 0.43 |
| f=3 {0,3,5} | 60/60 = 1.00 | 21/140 = 0.15 |
| f=2 {0,3} | 40/40 = 1.00 | 41/160 = 0.256 |
<!-- src: docs/contribution_b_results.md -->

@tab:agent-silo gives each silo's flag rate at seed 42, and @tab:portability shows that the fixed attacker set is a weaker attack at the other two seeds.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md -->

Table: Per-silo ByzAgent flag rate, seed 42 {#tab:agent-silo}
| Silo | Role | Clean run | f=3 | f=2 | Benign share |
|---|---|:-:|:-:|:-:|:-:|
| 0 | Malicious in both | 0.95 | 1.00 | 1.00 | 9.2% |
| 3 | Malicious in both | 1.00 | 1.00 | 1.00 | 0.3% |
| 5 | Malicious at f=3 | 1.00 | 1.00 | n/a | 0.1% |
| 8 | Never malicious | 0.95 | 1.00 | 1.00 | 12.3% |
| 1, 2, 4, 6, 7, 9 | Never malicious | 0.00–0.25 | 0.00–0.05 | 0.00–0.05 | 81.5–98.0% |
<!-- src: docs/contribution_b_results.md -->

Table: Attack effect by seed for the {0,3,5} sudden attack (change against clean) {#tab:portability}
| Seed | Mean | Median | Final-5 mean | Max |
|:-:|:-:|:-:|:-:|:-:|
| 42 | −0.0299 | −0.0048 | −0.0766 | +0.0004 |
| 1337 | −0.0095 | +0.0052 | +0.0274 | +0.0017 |
| 2024 | −0.0060 | +0.0001 | −0.0068 | −0.0141 |
<!-- src: docs/contribution_b_results.md -->

Table: ByzAgent lift over each malicious silo's own attack-free flag rate, f=3 sudden attack {#tab:lift}
| Seed | Silo 0 | Silo 3 | Silo 5 |
|---|:-:|:-:|:-:|
| 42 | +0.05 | +0.00 | +0.00 |
| 1337 | +0.05 | +0.40 | +0.95 |
| 2024 | +0.35 | −0.05 | +0.75 |
<!-- src: docs/contribution_b_results.md -->

![ByzAgent flag rate of each attacking silo without attack (open marker) and under attack (filled marker); the horizontal gap is the lift](docs/report/figs/fig_byzagent_lift.png){#fig:lift width=11}

The conclusion is stated in the project's fixed wording:

> "Both effects are present. A real compositional confound saturates some silos' flag rates independent of any attack; real attack-responsive detection is also present and becomes visible where silos are not already saturated. Seed 42's apparent null was partly a ceiling artifact of that seed's unusually bimodal composition."
<!-- src: PROJECT_INSTRUCTIONS.md -->

ByzAgent produces decisions plus a rationale of measured fidelity. Its strict citation error was 11.7% at seed 42 and 22.5% at the other seeds, where it kept citing update norm (about 59% of explanations) after that statistic had stopped tracking its decisions. With five-round histories, about 35 to 45% of its trend claims were wrong, and the history variant failed its preregistered test. Three repeated calls gave identical decisions in 27 of 30 cases. ByzAgent is not shown to beat the classical rules.
<!-- src: docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

@tab:phase4 shows why the history variant failed: the canary, silo 8, which never attacks, is flagged as often as the attackers.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Phase 4 flag rate of each silo in each cell (cur: this round only; hist: five-round history) {#tab:phase4}
| Silo | Clean, cur | Clean, hist | Sudden, cur | Sudden, hist | Gradual, cur | Gradual, hist |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| 0 | 0.95 | 0.00 | 1.00 | 0.15 | 1.00 | 0.45 |
| 3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 8 (canary) | 0.90 | 0.35 | 1.00 | 0.95 | 1.00 | 0.80 |
<!-- src: docs/contribution_b_results.md -->

@tab:fidelity42 shows, for seed 42, how often each statistic is cited, how strongly it tracks the decisions, and how often it is misquoted.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Seed 42: citation frequency (clean / f=3 / f=2), decision-severity ρ and strict citation error {#tab:fidelity42}
| Statistic | Cited in explanations | ρ with decision severity | Strict citation error |
|---|:-:|:-:|:-:|
| cosine_to_global | 99.5% / 86% / 71.5% | −0.808 | 4.4% |
| train_loss | 7.5% / 39% / 53% | +0.793 | 3.8% |
| val_accuracy | 43.5% / 65% / 57.5% | −0.745 | 8.6% |
| update_norm | 93% / 73% / 49% | +0.419 | 25.1% |
| cosine_to_peer_mean | 7% / 11.5% / 3% | +0.298 | Too few citations |
<!-- src: docs/contribution_b_results.md -->

@tab:fidelity-new shows how the decision correlations changed at the other two seeds.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Decision-severity correlation: seed 42 against seeds 1337 and 2024 pooled (n=800) {#tab:fidelity-new}
| Statistic | Seed 42 | Seeds 1337 and 2024 |
|---|:-:|:-:|
| val_accuracy | −0.745 | −0.577 |
| cosine_to_global | −0.808 | −0.474 |
| train_loss | +0.793 | +0.456 |
| update_norm | +0.419 | −0.076 |
| cosine_to_peer_mean | +0.298 | −0.118 |
<!-- src: docs/contribution_b_results.md -->

## Efficiency {#sec:r-efficiency}

@tab:eff-summary gives the measured serving and communication figures, taken on validation rows only.

Table: Serving and communication measurements (CPU, one laptop) {#tab:eff-summary}
| Quantity | Value |
|---|---|
| Per-flow latency p50, ONNX Runtime fp32 / PyTorch (median of 3 sessions) | 45.7 µs / 186.5 µs |
| Traffic per round, fp32, 10 silos, both directions | 1,587,920 bytes |
| Uplink saving, fp16 / int8 update compression | 50.0% / 74.9% |
| Change in best-by-validation macro-F1, fp16 / int8 (mean, 3 seeds) | −0.0007 / −0.0011 |
| Wall time per round, median of 500 rounds | 51.4 s |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

Served with ONNX Runtime in fp32, the model gives the same prediction as PyTorch for every one of the 143,513 validation rows, and this is now the default engine. An int8 version cut validation macro-F1 by 0.1428 and was abandoned. The accuracy effect of update compression could not be detected with three seeds.
<!-- src: docs/efficiency_results.md -->

@tab:serving-latency compares the serving variants, @tab:comp-bytes gives the bytes saved by update compression, and @tab:prescreen the replay of a loss-based pre-screen for the agent, which failed at seed 1337.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Serving variants: validation macro-F1 and per-flow latency (median of 3 sessions [min, max]) {#tab:serving-latency size=9.5}
| Variant | Validation macro-F1 | p50 latency, batch 1 | p95 latency, batch 1 |
|---|:-:|:-:|:-:|
| PyTorch eager | 0.9760 | 186.5 µs [172.7, 193.2] | 322.1 µs [254.1, 369.4] |
| ONNX Runtime fp32 | 0.9760 | 45.7 µs [40.6, 46.9] | 83.6 µs [75.7, 88.5] |
| ONNX Runtime int8 (dynamic) | 0.8332 | 47.9 µs [45.3, 57.9] | 98.1 µs [65.1, 99.2] |
<!-- src: docs/efficiency_results.md -->

Table: Uplink bytes per round under update compression {#tab:comp-bytes}
| Scheme | Uplink per round (bytes) | Saved against fp32 uplink | Saved against fp32 total |
|---|:-:|:-:|:-:|
| fp32 (reference) | 793,960 | n/a | n/a |
| fp16 | 396,980 | 50.0% | 25.0% |
| int8 per tensor | 198,890 | 74.9% | 37.5% |
<!-- src: docs/efficiency_results.md -->

@tab:comp-f1 reports the effect of compression on validation macro-F1 with all four statistics.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md; docs/preregistration_accuracy.md; PROJECT_INSTRUCTIONS.md -->

Table: Change in validation macro-F1 caused by compression at α=0.5, listed for seeds 42, 1337 and 2024 and then as mean ± sd {#tab:comp-f1 size=9}
| Scheme | Best-by-validation | Final round (20) | Final-5 mean | Mean of rounds 1–20 |
|---|:-:|:-:|:-:|:-:|
| fp16, per seed | +0.0036 / +0.0011 / −0.0068 | +0.0037 / −0.0016 / +0.0083 | −0.0465 / +0.0223 / −0.0037 | −0.0029 / +0.0168 / −0.0011 |
| fp16, mean ± sd | −0.0007 ± 0.0054 | +0.0035 ± 0.0050 | −0.0093 ± 0.0347 | +0.0043 ± 0.0109 |
| int8, per seed | +0.0020 / +0.0013 / −0.0066 | −0.0876 / +0.1173 / +0.0083 | −0.0169 / +0.0436 / −0.0023 | +0.0034 / +0.0068 / −0.0001 |
| int8, mean ± sd | −0.0011 ± 0.0048 | +0.0127 ± 0.1025 | +0.0081 ± 0.0316 | +0.0034 ± 0.0034 |
<!-- src: docs/efficiency_results.md -->

Table: Pre-screen replay at t=10 (flag rates: replay / logged) {#tab:prescreen size=9.5}
| Run | Calls avoided | Silo slots avoided | Replay equals logged | Flag rate, poisoned | Flag rate, clean |
|---|:-:|:-:|:-:|:-:|:-:|
| Seed 1337, clean | 25.0% | 90.0% | 0.685 | n/a | 0.100 / 0.415 |
| Seed 1337, f=3 sudden | 95.0% | 99.5% | 0.450 | 0.017 / 0.483 | 0.000 / 0.586 |
| Seed 2024, clean | 0.0% | 90.0% | 0.560 | n/a | 0.100 / 0.540 |
| Seed 2024, f=3 sudden | 5.0% | 64.5% | 0.765 | 0.733 / 0.767 | 0.100 / 0.421 |
<!-- src: docs/efficiency_results.md -->

## Negative and Null Results {#sec:r-negative}

- Agreement at α=0.1 below the seed-noise floor: directional, not significant.
- Label entropy as the skew covariate: failed once size was controlled.
- FedProx (μ=0.0005) at α=0.1 and α=5.0: inconclusive and no effect; μ=0.01 collapsed.
- Single-draw parity-monitor flags: artifacts; three seeded draws are needed.
- DeepExplainer on LayerNorm: failed; the GPU ran SHAP about 3 times slower than the CPU.
- Multi-Krum excluded a malicious silo 0% of the time. Its apparent success at f=2 is an artifact.
- ByzAgent at seed 42: lift of at most +0.05, a ceiling artifact; rolling history failed its preregistered test.
- int8 serving and a training-loss pre-screen for the agent: both rejected.
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md; docs/contribution_b_results.md; docs/efficiency_results.md -->

## Limitations {#sec:r-limitations}

Three seeds were used throughout, and silos of one run are not independent, so no p-values are reported. The seed-noise floor rests on three seed pairs, SHAP sampling in the headline pipeline was unseeded, and the faithfulness check covers one configuration. The attack is worst-case and the baselines knew the true f; the attacker-selection rule follows the same composition axis that all detectors react to, so it is open whether their failures are general. The agent's reasons are only partly faithful and its decisions vary between calls. Everything ran in simulation on one machine with one dataset. The complete record of every experiment, table and audit is in the project repository and in the full version of this report.
<!-- src: docs/contribution_a_results.md; docs/contribution_b_results.md; PROJECT_INSTRUCTIONS.md -->

## Challenges Faced and How We Solved Them {#sec:r-challenges}

Building the system meant working through a series of problems. The ones below are recorded in the project's documents or in its git history. Each is listed with what went wrong and what we did about it.

**DeepExplainer failed on LayerNorm.** SHAP's DeepExplainer, the natural choice for a neural network, produced an additivity error of 2.43 on our model because of its LayerNorm layers. A probe confirmed the failure, and we switched to GradientExplainer, whose residuals we then measured and disclosed instead of assuming them away.
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
