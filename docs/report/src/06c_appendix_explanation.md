## Explanation Check, Full Results {#sec:app-expl}

This section gives every agreement result, the reference lines, the supporting diagnostics and the negative checks of the explanation check. It supports Sections 2.2.4 and 4.2. Unless stated otherwise, agreement is the median over eligible rows: silos with at least 400 training rows, and families with at least 20 rows in the silo.
<!-- src: docs/contribution_a_results.md -->

### Two measurement choices

Two choices shape every number in this section. First, each comparison uses the attribution vector of the row's true class, so a disagreement about the prediction itself is excluded by design. A version anchored on each model's own predicted class would answer a different question and would need its own eligibility rules. Second, as with any perturbation-based explainer, SHAP's stand-in for a "missing" feature is an average over the background, which is not a real network flow.

The evaluation rows are fixed: 14 rows drawn once from the test set with a fixed seed, two for each headline family, used only as inputs to the explainer and never as a score. The background for each silo is 200 rows drawn from that silo's own training partition, stratified by class under a fixed seed, and each explanation uses 4000 samples.
<!-- src: docs/measurement_protocol.md; docs/test_set_exposure_audit.md -->

### Agreement by skew level and by family

@tab:agree-alpha-full gives each metric per α, including Jaccard@5 and Jaccard@20. @tab:agree-family-j and @tab:agree-family-tau break Jaccard@10 and weighted τ down by family. The interquartile ranges were computed for the project paper from `results/inspection/agreement_metrics.csv` and stored in `paper/figs/derived_values.json`; the medians reproduce the published ones.

Table: Agreement per α: median, with [first quartile, third quartile] where computed {#tab:agree-alpha-full}
| Measure | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Eligible / all rows | 220 / 406 | 388 / 420 | 420 / 420 |
| Jaccard@5 | 0.250 | 0.429 | 0.667 |
| Jaccard@10 | 0.333 [0.250, 0.538] | 0.538 [0.429, 0.667] | 0.667 [0.538, 0.667] |
| Jaccard@20 | 0.379 | 0.600 | 0.667 |
| Weighted τ | 0.592 [0.413, 0.712] | 0.787 [0.725, 0.827] | 0.844 [0.818, 0.868] |
<!-- src: site/public/data/agreement_by_alpha.json; paper/figs/derived_values.json -->

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

Table: Weighted Kendall's τ by family: median [first quartile, third quartile] {#tab:agree-family-tau size=9.5}
| Family | α=0.1 | α=0.5 | α=5.0 |
|---|:-:|:-:|:-:|
| Benign | 0.649 [0.532, 0.716] | 0.772 [0.737, 0.806] | 0.830 [0.794, 0.851] |
| Bot | 0.560 [0.347, 0.696] | 0.751 [0.698, 0.795] | 0.818 [0.789, 0.845] |
| BruteForce | 0.596 [0.403, 0.696] | 0.803 [0.692, 0.842] | 0.841 [0.811, 0.848] |
| DDoS | 0.620 [0.464, 0.736] | 0.808 [0.773, 0.839] | 0.858 [0.842, 0.881] |
| DoS | 0.688 [0.549, 0.740] | 0.819 [0.783, 0.855] | 0.876 [0.856, 0.887] |
| PortScan | 0.519 [0.354, 0.632] | 0.788 [0.740, 0.814] | 0.861 [0.839, 0.881] |
| WebAttack | 0.416 [0.335, 0.583] | 0.769 [0.637, 0.798] | 0.823 [0.807, 0.843] |
<!-- src: paper/figs/derived_values.json -->

The family pattern follows the overall one: every family agrees less at α=0.1, and DDoS and DoS keep the highest agreement throughout.
<!-- src: PROJECT_INSTRUCTIONS.md -->

### Reference lines and uncertainty

**Chance.** For two independent, uniformly random k-subsets of n items, the expected intersection is k²/n and the expected union is 2k − k²/n. Their ratio approximates the expected Jaccard index. With k=10 and n=82 it is 0.065.
<!-- src: docs/contribution_a_results.md -->

**Seed-noise floor.** Three centralized models (seeds 42, 1337 and 2024) were explained on the same 14 rows, with the same number of samples and the same class-stratified 200-row background construction as the federated pipeline. @tab:floor-pairs in Section 4.2 gives each seed pair. The floor is the median of the three pair medians, reported with their range: 0.429 [0.429, 0.484] for Jaccard@10 and 0.663 [0.660, 0.690] for weighted τ.
<!-- src: site/public/data/headline.json; docs/measurement_protocol.md -->

**Cluster bootstrap.** The bootstrap resamples (seed, silo) clusters with replacement 10,000 times, 29 clusters at α=0.1, and takes the median of all rows in each resample. At α=0.1 the 95% percentile interval is [0.250, 0.429] for Jaccard@10 and [0.541, 0.661] for weighted τ. The Jaccard interval overlaps the floor's range, so the below-floor reading at α=0.1 is directional, not significant. An interval was computed only for α=0.1.
<!-- src: site/public/data/ci.json -->

@fig:floor-alpha, produced by the project's plotting tools, draws the federated agreement against the floor's range with the α=0.1 interval overlaid. Its τ panel draws the floor median as the median over all 42 rows of the floor file, which differs slightly from the median of the three pair medians used in the text.
<!-- src: PROJECT_INSTRUCTIONS.md; results/inspection/centralized_instability_floor.csv -->

![Federated agreement against the centralized-seed instability floor, with the α=0.1 cluster-bootstrap interval (from results/figures/)](results/figures/instability_floor_vs_alpha.png){#fig:floor-alpha width=15.5}

@fig:agree-alpha-results is the project's own earlier plot of the same headline numbers, with the interquartile band and the chance level.

![Silo-versus-global agreement against α for Jaccard@10 and weighted τ, with the floor median and the chance level (from results/figures/)](results/figures/agreement_vs_alpha.png){#fig:agree-alpha-results width=15.5}

### Size and label skew

Under the partitioner, a silo's size is the sum over families of the family's size times the silo's share of it, a function of the same draw that sets the silo's skew. A raw size correlation therefore restates the skew effect. Silo size and Jaccard@10 correlate at r=+0.46 at α=0.1 and r=+0.07 at α=5.0, which is consistent with size carrying the skew signal, since skew and size variation are largest at α=0.1.
<!-- src: docs/contribution_a_results.md -->

Label entropy over the nine classes was the covariate fixed in advance. Its zero-order correlation with agreement at α=0.5 was weak and negative (r=−0.12 to −0.15). After conditioning on log size, its partial correlation weakened and changed sign, to +0.23 for Jaccard@10 and +0.13 for τ (n=30). That is the signature of a covariate whose apparent effect was carried by size, so it was dropped. KL divergence from the global label distribution was then tried in its place. Unlike entropy, which measures only how even a silo's label mix is, KL measures how far the mix is from the global one. It kept a strong partial correlation after the same conditioning (@tab:kl-partial in Section 4.2; @fig:kl-scatter and @fig:entropy-kl).
<!-- src: docs/contribution_a_results.md -->

![Per-silo KL divergence from the global label mix against Jaccard@10 at the final round; filled markers are seed 42, open square and triangle are seeds 1337 and 2024](docs/report/figs/fig_kl_scatter.png){#fig:kl-scatter width=12}

![Zero-order and partial correlations of label entropy (pre-specified) and KL divergence (its replacement) with Jaccard@10, controlling for log silo size (from results/figures/)](results/figures/entropy_kl_partial_correlation.png){#fig:entropy-kl width=15}

This narrows the limitation but does not remove it. The partial correlation is observational, computed on silos whose size and skew came from the same draw. Disentangling them causally needs size-equalized partitions, and this partitioner cannot produce partitions that vary skew while holding size fixed. No p-values are reported, because silos within one run are not independent.

### Round-wise agreement

Agreement was recomputed at rounds 5, 10, 15 and 20 with 1000 SHAP samples, a quarter of the headline setting. These values check the shape of convergence and are not comparable in size with the headline numbers. @tab:roundwise and @fig:roundwise give the means; @fig:roundwise-results and @fig:decoupling show the same data as plotted by the project's tools.
<!-- src: docs/contribution_a_results.md -->

Table: Round-wise means (reduced SHAP fidelity) {#tab:roundwise}
| Measure | α | Round 5 | Round 10 | Round 15 | Round 20 |
|---|:-:|:-:|:-:|:-:|:-:|
| Jaccard@10 | 0.1 | 0.359 | 0.350 | 0.334 | 0.336 |
| Jaccard@10 | 0.5 | 0.560 | 0.542 | 0.548 | 0.531 |
| Jaccard@10 | 5.0 | 0.640 | 0.641 | 0.642 | 0.644 |
| Weighted τ | 0.1 | 0.524 | 0.548 | 0.541 | 0.529 |
| Weighted τ | 0.5 | 0.770 | 0.760 | 0.759 | 0.742 |
| Weighted τ | 5.0 | 0.830 | 0.828 | 0.822 | 0.830 |
| Validation macro-F1 | 0.1 | 0.460 | 0.461 | 0.464 | 0.506 |
| Validation macro-F1 | 0.5 | 0.872 | 0.895 | 0.937 | 0.898 |
| Validation macro-F1 | 5.0 | 0.860 | 0.984 | 0.949 | 0.950 |
<!-- src: docs/contribution_a_results.md -->

From round 5 to round 20, Jaccard@10 falls by 0.023 at α=0.1 and by 0.029 at α=0.5, while validation macro-F1 rises by 0.046 and 0.026. At α=5.0 the four Jaccard values span 0.004. No test was run on this trend; it is directional.
<!-- src: docs/contribution_a_results.md -->

![Round-wise mean Jaccard@10 (a) and mean validation macro-F1 (b) by α](docs/report/figs/fig_round_wise.png){#fig:roundwise width=13}

![Explanation agreement against validation macro-F1 across rounds, reduced fidelity (from results/figures/)](results/figures/agreement_vs_round.png){#fig:roundwise-results width=13}

![Accuracy and explanation agreement decouple under non-IID federation: per-α panels of mean Jaccard@10 and validation macro-F1 by round (from results/figures/)](results/figures/accuracy_agreement_decoupling.png){#fig:decoupling width=15.5}

### FedProx at μ=0.0005

FedProx [@li2020fedprox] was run at one value, μ=0.0005, carried forward from an exploratory run; μ was never swept. One other value, μ=0.01, was tried once at α=0.5, seed 42, and collapsed validation macro-F1 to 0.7114 with Bot and WebAttack recall at zero. @tab:fedprox-agree compares FedProx with FedAvg per seed on agreement, using the mean over eligible rows rather than the median used elsewhere. @tab:fedprox-f1 gives test macro-F1. Row counts match exactly between the two methods at every (α, seed) pair, so the same eligibility filter applied to both.
<!-- src: docs/contribution_a_results.md; docs/test_set_exposure_audit.md -->

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

Table: FedAvg against FedProx (μ=0.0005): test macro-F1 per seed {#tab:fedprox-f1}
| α | Seed | FedAvg | FedProx | Δ |
|:-:|:-:|:-:|:-:|:-:|
| 0.1 | 42 | 0.5426 | 0.5526 | +0.0100 |
| 0.1 | 1337 | 0.4481 | 0.4202 | −0.0279 |
| 0.1 | 2024 | 0.5572 | 0.6265 | +0.0693 |
| 0.5 | 42 | 0.9753 | 0.9794 | +0.0041 |
| 0.5 | 1337 | 0.9866 | 0.9846 | −0.0020 |
| 0.5 | 2024 | 0.8605 | 0.8591 | −0.0014 |
| 5.0 | 42 | 0.9900 | 0.9889 | −0.0011 |
| 5.0 | 1337 | 0.9905 | 0.9890 | −0.0015 |
| 5.0 | 2024 | 0.9889 | 0.9919 | +0.0029 |
<!-- src: docs/contribution_a_results.md -->

At α=0.5, Jaccard@10 rises in all three seeds, shrinking from +0.0263 to +0.0042, while test macro-F1 moves by small amounts of mixed sign; weighted τ rises in two seeds and is negligibly lower in the third. At α=0.1, agreement and accuracy move in the same direction in every seed (both up at seeds 42 and 2024, both down at seed 1337), so three seeds cannot separate an explanation effect from an accuracy effect, and the result is inconclusive. At α=5.0 there is no consistent change. @fig:fedprox-seeds plots the per-seed comparison.
<!-- src: docs/contribution_a_results.md -->

![FedProx (μ=0.0005) against FedAvg, per seed, at α=0.1 and α=0.5: mean Jaccard@10, labelled with the change in test macro-F1 (from results/figures/)](results/figures/fedprox_vs_fedavg_per_seed.png){#fig:fedprox-seeds width=15.5}

### The parity monitor

The parity monitor turns per-silo rankings into a fleet-wide drift flag, using only what would cross the client-to-server boundary: top-10 feature-index lists, with no SHAP magnitudes and no raw data. Each silo's per-row top-10 sets are combined by vote into one ordered list. Each silo's deviation is one minus the Jaccard index between its list and a consensus built from every other silo in the same draw. A silo is flagged when its modified z-score, computed from the median and the median absolute deviation (MAD), exceeds 3.5 [@iglewicz1993].
<!-- src: docs/contribution_a_results.md -->

Over the full sweep (9 configurations, 4 rounds each, 356 rows, 392.0 minutes of compute) the monitor raised 3 flags, all at α=0.5 and round 5 (@tab:parity, @fig:parity).
<!-- src: docs/contribution_a_results.md -->

Table: Parity-monitor flags (three-draw average) {#tab:parity}
| Run | Seed | Silo | Deviation |
|---|:-:|:-:|:-:|
| `fedavg_a0.5_s1337` | 1337 | 7 | 0.775 |
| `fedavg_a0.5_s2024` | 2024 | 3 | 0.530 |
| `fedavg_a0.5_s2024` | 2024 | 6 | 0.535 |
<!-- src: docs/contribution_a_results.md -->

![Parity monitor: fleet parity by round and per-silo deviation, with flagged silos circled (from results/figures/)](results/figures/parity_monitor.png){#fig:parity width=15.5}

Zero flags at α=0.1 does not mean that the α=0.1 fleet is healthy. The threshold judges a silo against its own fleet's spread in that round, not against an absolute level. At α=0.1, round 5, the median deviation across 29 eligible silos was 0.694, worse than any of the three flagged values at α=0.5. Yet nothing was flagged, because at severe skew every silo diverges from the consensus about equally, so none stands out. Absolute agreement should be read from the headline Jaccard and τ values, not from the flag count.
<!-- src: docs/contribution_a_results.md -->

**The multi-draw fix.** An earlier version of the monitor, based on a single explainer draw, flagged two silos of `fedavg_a0.1_s1337` at round 5, with deviations of 0.947 and 0.889. Explaining the same checkpoints again with the same background and rows did not reproduce either flag. Tracing the cause showed that the original draw had produced an unusually tight cluster of tied deviations, a side effect of breaking ties among top-k votes over only 14 rows. That shrank the round's MAD to 0.042, about a third of what fresh draws gave, so an ordinary deviation crossed the threshold. The threshold formula was sound; judging it on one uncontrolled draw was not. The monitor now explains each checkpoint three times with fixed seeds (1001, 2002, 3003), computes each draw's deviations separately without mixing features across draws, and averages the three deviations per silo before thresholding. The numbers above come from this version.
<!-- src: docs/contribution_a_results.md -->

### Faithfulness and explainer checks

**Deletion and insertion.** Deletion and insertion curves [@petsiuk2018] replace features by the model's training mean, in ranked order, and track the probability assigned to the true class. They were run for one configuration (α=0.5, seed 42) on the global model and three of the ten silos (@tab:faith, @fig:deletion and @fig:insertion). Every deletion AUC lies below the matching insertion AUC, which fits attributions that track the model. There is no agreed threshold for these AUCs, and nothing downstream is gated on them, so this is a spot-check, not a gate.
<!-- src: docs/contribution_a_results.md -->

Table: Deletion AUC (lower is better) and insertion AUC (higher is better), α=0.5, seed 42 {#tab:faith}
| Model | Deletion AUC | Insertion AUC |
|---|:-:|:-:|
| Global | 0.167 | 0.696 |
| Silo 0 | 0.274 | 0.800 |
| Silo 1 | 0.166 | 0.628 |
| Silo 2 | 0.179 | 0.655 |
<!-- src: docs/contribution_a_results.md -->

![Deletion faithfulness curves for the global model and three silos, α=0.5, seed 42 (from results/figures/)](results/figures/deletion_curve.png){#fig:deletion width=12}

![Insertion faithfulness curves for the global model and three silos, α=0.5, seed 42 (from results/figures/)](results/figures/insertion_curve.png){#fig:insertion width=12}

**Explainer and background checks.** KernelExplainer and GradientExplainer on the same models agree at median τ=0.730 and median Jaccard@10 0.538 (n=14), so the rankings are not an artifact of the explainer choice. Replacing per-silo backgrounds with a common one gives median τ=0.807 and Jaccard@10 0.603 (n=42), so cross-silo disagreement is not an artifact of background sampling.
<!-- src: docs/contribution_a_results.md -->

**DeepExplainer.** DeepExplainer was rejected after a probe: on this model its additivity error is 2.43, against a tolerance of 0.01, because of the LayerNorm layers.
<!-- src: docs/contribution_a_results.md -->

**CPU against GPU.** SHAP on this small model ran about 3 times slower on the GPU than on the CPU, because kernel-launch overhead dominates a model with 19,849 parameters. All SHAP work therefore used the CPU.
<!-- src: docs/contribution_a_results.md; docs/efficiency_results.md -->

**Unseeded sampling.** The Monte Carlo sampling inside GradientExplainer is not seeded in the headline pipeline. Re-explaining one global model with an identical background and identical rows gave a mean absolute difference of 0.0188 and a maximum of 0.403 between draws, while every deterministic part of the pipeline reproduced exactly. Every headline Jaccard and τ value reflects one unseeded draw per (configuration, silo). How often this noise moves a feature across the top-10 boundary has not been measured for the headline pipeline.
<!-- src: docs/contribution_a_results.md -->

### Generalization and near-duplication

A nearest-neighbour audit compared, for each family, how far its test rows sit from their nearest training row with how far its training rows sit from each other (@tab:nn-audit). For most families the two distances are about equal. PortScan stands out: its test rows sit about 23 times further from the training data than its training rows sit from each other, so PortScan is the family whose test rows are genuinely new. Its recall is also bimodal across seeds (0.9505, 0.9506 and 0.9995).
<!-- src: results/near_duplicate_audit.json; PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->

Table: Nearest-neighbour audit: median test-to-train distance over median train-to-train distance {#tab:nn-audit}
| Family | Probed rows | Median test distance | Median train distance | Ratio |
|---|:-:|:-:|:-:|:-:|
| Benign | 2,259 | 0.0014 | 0.0014 | 1.00 |
| Bot | 250 | 0.0 | 0.0 | undefined |
| BruteForce | 250 | 0.0038 | 0.0039 | 0.97 |
| DDoS | 250 | 0.0161 | 0.0176 | 0.92 |
| DoS | 278 | 0.0150 | 0.0152 | 0.99 |
| PortScan | 292 | 0.0456 | 0.0020 | 23.32 |
| WebAttack | 250 | 0.0 | 0.0 | undefined |
<!-- src: results/near_duplicate_audit.json -->

For Bot and WebAttack both distances are zero: their test rows have exact copies in the training data once identifiers are removed. That raised a preregistered concern that their agreement numbers could be inflated. The concern was tested and not confirmed. Thin support, 3,527 Bot and 1,542 WebAttack training rows, explains their behaviour better.
<!-- src: docs/contribution_a_results.md -->

### An open pattern at α=0.5

Three separate analyses single out α=0.5. All three parity flags occur there, although α=0.1 has worse absolute deviations. The KL partial correlation is stronger there than at α=0.1. And the FedProx agreement gain is consistent across seeds only there. We record this as an open pattern and propose no mechanism. The temptation to fit a story to it after the fact is resisted, and it is left for future work.
<!-- src: docs/contribution_a_results.md -->

### Limitations of the explanation check

@tab:expl-limits lists every limitation recorded for the explanation check in its canonical results document, in short form.

Table: Limitations of the explanation check {#tab:expl-limits size=9.5}
| # | Limitation |
|:-:|---|
| 1 | The round lottery is real (up to 0.118 in validation macro-F1); validation-based round selection is required and used everywhere |
| 2 | Bot and WebAttack near-duplication was tested and not confirmed |
| 3 | The α=0.1 below-floor reading is directional, not significant |
| 4 | Silo size and skew cannot be varied independently by this partitioner |
| 5 | PortScan is the genuine generalization family |
| 6 | GradientExplainer was chosen over DeepExplainer by a confirmed probe |
| 7 | The CPU beats the GPU for this SHAP workload, by measurement |
| 8 | Conflicts had to be detected on the family, not the raw label (58,307 rows would have been lost) |
| 9 | GradientExplainer's additivity residual is nonzero, and is disclosed |
| 10 | Only top-k rankings cross the boundary, so server analyses see a compressed summary |
| 11 | SHAP's background substitution is off the data manifold |
| 12 | The faithfulness check is a single-slice spot-check, not a gate |
| 13 | The seed-noise floor rests on three seed pairs only |
| 14 | Anchoring on the true class is a choice, not the only valid one |
| 15 | The chance level assumes independent, uniform features |
| 16 | Deletion and insertion AUCs have no agreed threshold |
| 17 | SHAP's Monte Carlo sampling is unseeded |
| 18 | Silos within one run are not independent samples |
| 19 | Three seeds is a ceiling set by cost, not a free choice |
| 20 | μ=0.0005 is a single point, not a swept optimum |
| 21 | High additivity residuals concentrate in small α=0.1 silos, without moving the headline |
<!-- src: docs/contribution_a_results.md -->

## SHAP Additivity Residuals {#sec:app-residuals}

This section reports how well the SHAP values reconstruct the model's output, and whether poor reconstruction could explain the low agreement at α=0.1. It supports Section 4.2.
<!-- src: PROJECT_INSTRUCTIONS.md -->

For a row x, the relative residual is the largest over classes of |Σ SHAP − (f(x) − E[f])|, divided by the largest over classes of |f(x) − E[f]|, where f(x) is the model's logit and E[f] its average over the background.
<!-- src: PROJECT_INSTRUCTIONS.md -->

### The validation pool

For the served model, 500 validation rows were explained with 4000 samples (@tab:valpool). Of the 18 rows whose relative residual is above 8%, seven are Bot, four Benign and four WebAttack; the worst case, at 21.2%, is an Infiltration row. A range of "3–8%" quoted in earlier project notes could not be traced to any file, so it was dropped. For the 14 test rows used by the explanation check, the residual cannot be recomputed at all, because their stored SHAP files lack the model outputs it needs.
<!-- src: PROJECT_INSTRUCTIONS.md; results/shap/fedavg_a0.5_s42/val_pool_summary.json -->

Table: Additivity residuals on 500 validation rows {#tab:valpool}
| Residual | Median | p95 | Maximum |
|---|:-:|:-:|:-:|
| Relative | 3.2% | 7.7% | 21.2% |
| Absolute (logit) | 0.472 | 1.105 | 3.336 |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->

### Audit of stored residuals

Each stored SHAP file records one value: the worst residual among its 14 rows. Comparing that with a single-row maximum is therefore rough. Stored values range from 0.156 to 15.874. @tab:residaudit counts files above the validation-pool maximum of 3.336. Among final-round FedAvg files, 4 of 99 exceed it: silos 3 and 9 of α=0.1 seed 42, silo 8 of α=0.1 seed 1337, and the global model of α=5.0 seed 1337 (3.500). Two of the three silos are the smallest in their run.
<!-- src: results/inspection/residual_audit_summary.json; docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

Table: Stored residual files above 3.336, and Spearman r between silo residual and Jaccard@10 (final round) {#tab:residaudit}
| Pass | α=0.1 | α=0.5 | α=5.0 | Silo / global |
|---|:-:|:-:|:-:|:-:|
| FedAvg final | 3/33 | 0/33 | 1/33 | 3/90, 1/9 |
| FedAvg round-wise | 26/132 | 0/132 | 5/132 | 29/360, 2/36 |
| FedProx final | 1/33 | 0/33 | 0/33 | 1/90, 0/9 |
| Spearman r (n), final | −0.237 (29) | 0.202 (30) | 0.11 (30) | |
<!-- src: results/inspection/residual_audit_summary.json -->

### Pre-specified sensitivity check and a post-hoc variant

The exclusion rule was fixed before computing: drop any silo whose final-round residual exceeds 3.336. At α=0.1 the rule removes two silos that contribute eligible rows, 8 of the 220. The Jaccard@10 median stays at 0.333, and the τ median moves from 0.592 to 0.597. Nothing is removed at α=0.5 or α=5.0.
<!-- src: PROJECT_INSTRUCTIONS.md -->

**Post-hoc, and not part of the pre-specified rule:** if the whole α=5.0 seed-1337 run is dropped because its global model is flagged, the α=5.0 medians are still 0.667 for Jaccard@10 and 0.844 for τ. The headline therefore does not depend on the high-residual files.
<!-- src: PROJECT_INSTRUCTIONS.md -->
