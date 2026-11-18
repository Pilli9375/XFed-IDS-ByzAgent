## Explanation Check, Full Results {#sec:app-expl}

Here we collect the explanation check in full: each agreement result, both reference lines, the diagnostics behind them and the checks that came out negative. It supports Sections 2.2.4 and 4.2. Unless stated otherwise, agreement is the median over eligible rows: a silo must have 400 or more training rows, and a family needs 20 or more rows inside that silo.
<!-- src: docs/contribution_a_results.md -->

### Two measurement choices

Two choices shape every number in this section. First, rankings are compared for the true class of each row, which deliberately keeps disagreement about the predicted label out of the measure. Comparing each model's ranking for its own predicted class would be a different question, with eligibility rules of its own. Second, SHAP replaces a "missing" feature by its background average, as all perturbation explainers do, and such an averaged flow does not exist in real traffic.

The evaluation rows are fixed: 14 rows drawn once from the test set with a fixed seed, two for each headline family, used only as inputs to the explainer and never as a score. Each silo's background is a 200-row sample of its own training data, balanced over classes and drawn with a fixed seed; each explanation is computed with 4000 samples.
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

**Seed-noise floor.** Three centralized models (seeds 42, 1337 and 2024) were explained on the same 14 rows, using the federated pipeline's sample count and its way of building a balanced 200-row background. @tab:floor-pairs in Section 4.2 gives each seed pair. The floor is the median of the three pair medians, reported with their range: 0.429 [0.429, 0.484] for Jaccard@10 and 0.663 [0.660, 0.690] for weighted τ.
<!-- src: site/public/data/headline.json; docs/measurement_protocol.md -->

**Cluster bootstrap.** At α=0.1 there are 29 (seed, silo) clusters. The bootstrap draws clusters with replacement, computes the median over every row of the drawn clusters, and repeats this 10,000 times. At α=0.1 the 95% percentile interval is [0.250, 0.429] for Jaccard@10 and [0.541, 0.661] for weighted τ. The Jaccard interval overlaps the floor's range, so the below-floor reading at α=0.1 is directional, not significant. An interval was computed only for α=0.1.
<!-- src: site/public/data/ci.json -->

@fig:floor-alpha, produced by the project's plotting tools, draws the federated agreement against the floor's range with the α=0.1 interval overlaid. Its τ panel draws the floor median as the median over all 42 rows of the floor file, which differs slightly from the median of the three pair medians used in the text.
<!-- src: PROJECT_INSTRUCTIONS.md; results/inspection/centralized_instability_floor.csv -->

![Federated agreement against the centralized-seed instability floor, with the α=0.1 cluster-bootstrap interval (from results/figures/)](results/figures/instability_floor_vs_alpha.png){#fig:floor-alpha width=15.5}

@fig:agree-alpha-results is the project's own earlier plot of the same headline numbers, with the interquartile band and the chance level.

![Silo-versus-global agreement against α for Jaccard@10 and weighted τ, with the floor median and the chance level (from results/figures/)](results/figures/agreement_vs_alpha.png){#fig:agree-alpha-results width=15.5}

### Size and label skew

Under the partitioner, a silo's size is the sum over families of the family's size times the silo's share of it, so size is decided by the very draw that decides skew. A plain correlation with size is therefore just the skew effect seen from another side. Silo size and Jaccard@10 correlate at r=+0.46 at α=0.1 and r=+0.07 at α=5.0, which is consistent with size carrying the skew signal, since skew and size variation are largest at α=0.1.
<!-- src: docs/contribution_a_results.md -->

Before looking at the data, we had chosen the entropy of a silo's nine-class label mix as the covariate. Its zero-order correlation with agreement at α=0.5 was weak and negative (r=−0.12 to −0.15). Holding log size fixed made the relation weaker and reversed its sign, to +0.23 for Jaccard@10 and +0.13 for τ (n=30). That is the signature of a covariate whose apparent effect was carried by size, so it was dropped. KL divergence from the global label distribution was then tried in its place. Unlike entropy, which measures only how even a silo's label mix is, KL measures how far the mix is from the global one. It kept a strong partial correlation after the same conditioning (@tab:kl-partial in Section 4.2; @fig:kl-scatter and @fig:entropy-kl).
<!-- src: docs/contribution_a_results.md -->

![Jaccard@10 at the final round plotted against each silo's KL divergence from the overall label mix; seed 42 uses filled markers, seeds 1337 and 2024 open squares and triangles](docs/report/figs/fig_kl_scatter.png){#fig:kl-scatter width=12}

![Zero-order and partial correlations of label entropy (pre-specified) and KL divergence (its replacement) with Jaccard@10, controlling for log silo size (from results/figures/)](results/figures/entropy_kl_partial_correlation.png){#fig:entropy-kl width=15}

This narrows the limitation but does not remove it. The partial correlation comes from observation only, and in these silos one random draw fixed both size and skew. Disentangling them causally needs size-equalized partitions, and this partitioner cannot produce partitions that vary skew while holding size fixed. No p-values are reported, because silos within one run are not independent.

### Round-wise agreement

To follow agreement over training, it was computed again at four rounds (5, 10, 15 and 20) using 1000 SHAP samples, one quarter of the headline setting. The point is the shape over time; the size of these values should not be compared with the headline results. @tab:roundwise and @fig:roundwise give the means; @fig:roundwise-results and @fig:decoupling show the same data as plotted by the project's tools.
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

Over these rounds, Jaccard@10 goes down by 0.023 (α=0.1) and 0.029 (α=0.5), while validation macro-F1 goes up by 0.046 and 0.026 respectively. At α=5.0 the four Jaccard values lie within 0.004 of each other. Because the trend was never tested statistically, it counts as directional.
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

At α=0.5, Jaccard@10 rises in all three seeds, shrinking from +0.0263 to +0.0042, and test macro-F1 changes only a little, up in one seed and down in two; weighted τ increases for two seeds and is very slightly lower for the third. At α=0.1, agreement and accuracy move in the same direction in every seed (both up at seeds 42 and 2024, both down at seed 1337), so with three seeds one cannot say whether FedProx changed the explanations or only the accuracy; this result is inconclusive. At α=5.0 there is no consistent change. @fig:fedprox-seeds plots the per-seed comparison.
<!-- src: docs/contribution_a_results.md -->

![FedProx (μ=0.0005) against FedAvg, per seed, at α=0.1 and α=0.5: mean Jaccard@10, labelled with the change in test macro-F1 (from results/figures/)](results/figures/fedprox_vs_fedavg_per_seed.png){#fig:fedprox-seeds width=15.5}

### The parity monitor

The parity monitor turns per-silo rankings into a fleet-wide drift flag, using only what would cross the client-to-server boundary: top-10 feature-index lists, with no SHAP magnitudes and no raw data. Each silo's per-row top-10 sets are combined by vote into one ordered list. Each silo's deviation is one minus the Jaccard index between its list and a consensus built from every other silo in the same draw. A flag is raised when a silo's modified z-score, which uses the median and the median absolute deviation (MAD) instead of the mean and standard deviation, is above 3.5 [@iglewicz1993].
<!-- src: docs/contribution_a_results.md -->

The complete sweep covered 9 configurations at 4 rounds each, 356 rows in all, and took 392.0 minutes; it produced 3 flags, all at α=0.5 and round 5 (@tab:parity, @fig:parity).
<!-- src: docs/contribution_a_results.md -->

Table: Parity-monitor flags (three-draw average) {#tab:parity}
| Run | Seed | Silo | Deviation |
|---|:-:|:-:|:-:|
| `fedavg_a0.5_s1337` | 1337 | 7 | 0.775 |
| `fedavg_a0.5_s2024` | 2024 | 3 | 0.530 |
| `fedavg_a0.5_s2024` | 2024 | 6 | 0.535 |
<!-- src: docs/contribution_a_results.md -->

![Parity monitor: fleet parity by round and per-silo deviation, with flagged silos circled (from results/figures/)](results/figures/parity_monitor.png){#fig:parity width=15.5}

The absence of flags at α=0.1 should not be read as a sign that those silos agree well. The threshold judges a silo against its own fleet's spread in that round, not against an absolute level. In round 5 at α=0.1, the 29 eligible silos had a median deviation of 0.694, which is larger than each of the three values flagged at α=0.5. Yet nothing was flagged, because at severe skew every silo diverges from the consensus about equally, so none stands out. Absolute agreement should be read from the headline Jaccard and τ values, not from the flag count.
<!-- src: docs/contribution_a_results.md -->

**The multi-draw fix.** An earlier version of the monitor, based on a single explainer draw, flagged two silos of `fedavg_a0.1_s1337` at round 5, with deviations of 0.947 and 0.889. Explaining the same checkpoints again with the same background and rows did not reproduce either flag. Tracing the cause showed that the original draw had produced an unusually tight cluster of tied deviations, a side effect of breaking ties among top-k votes over only 14 rows. That draw's MAD came out at 0.042, roughly one third of the value in new draws, and an ordinary deviation was therefore pushed over the threshold. Nothing was wrong with the formula; the mistake was to apply it to a single uncontrolled draw. In the current monitor, every checkpoint is explained three times with the fixed seeds 1001, 2002 and 3003; deviations are worked out for each draw on its own, never pooling features from different draws, and the three values for a silo are averaged before the threshold is applied. The numbers above come from this version.
<!-- src: docs/contribution_a_results.md -->

### Faithfulness and explainer checks

**Deletion and insertion.** These curves [@petsiuk2018] take the features in ranked order and set them to the training mean (deletion) or restore them from it (insertion), watching the probability the model gives to the true class. We ran them for a single configuration, α=0.5 with seed 42, on the global model and on three silos out of ten (@tab:faith, @fig:deletion and @fig:insertion). In each case the deletion AUC is lower than the insertion AUC, as it should be if the attributions follow the model. No accepted cut-off exists for such AUCs, and no later step depends on them; the check is a spot-check only.
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

**Explainer and background checks.** Running KernelExplainer and GradientExplainer on identical models gives median τ=0.730 and median Jaccard@10 0.538 between them (n=14); the rankings therefore do not depend on which explainer is used. Giving every silo one shared background instead of its own yields median τ=0.807 and Jaccard@10 0.603 (n=42); the disagreement between silos therefore does not come from how backgrounds are sampled.
<!-- src: docs/contribution_a_results.md -->

**DeepExplainer.** DeepExplainer was rejected after a probe: on this model its additivity error is 2.43, against a tolerance of 0.01, because of the LayerNorm layers.
<!-- src: docs/contribution_a_results.md -->

**CPU against GPU.** For a model of only 19,849 parameters, the cost of launching GPU kernels outweighs the work itself, and SHAP took about 3 times as long on the GPU as on the CPU. All SHAP work therefore used the CPU.
<!-- src: docs/contribution_a_results.md; docs/efficiency_results.md -->

**Unseeded sampling.** The headline pipeline sets no seed for GradientExplainer's internal random sampling. When one global model was explained twice with the same background and rows, the SHAP values differed by 0.0188 on average and by 0.403 at most, although every other, deterministic step gave identical output. Every headline Jaccard and τ value reflects one unseeded draw per (configuration, silo). How often this noise moves a feature across the top-10 boundary has not been measured for the headline pipeline.
<!-- src: docs/contribution_a_results.md -->

### Generalization and near-duplication

A nearest-neighbour audit compared, for each family, how far its test rows sit from their nearest training row with how far its training rows sit from each other (@tab:nn-audit). For most families the two distances are about equal. PortScan stands out: its test rows sit about 23 times further from the training data than its training rows sit from each other, which makes PortScan the one family whose test rows really differ from what training saw. Its recall is also bimodal across seeds (0.9505, 0.9506 and 0.9995).
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

For Bot and WebAttack both distances are zero: their test rows have exact copies in the training data once identifiers are removed. That raised a preregistered concern that their agreement numbers could be inflated. The concern was tested and not confirmed. Their behaviour is better explained by how few training rows they have: 3,527 for Bot and 1,542 for WebAttack.
<!-- src: docs/contribution_a_results.md -->

### An open pattern at α=0.5

Three separate analyses single out α=0.5. All three parity flags occur there, although α=0.1 has worse absolute deviations. The KL partial correlation is stronger there than at α=0.1. And the FedProx agreement gain is consistent across seeds only there. We note the pattern and leave it open, without offering an explanation for it. The temptation to fit a story to it after the fact is resisted, and it is left for future work.
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

Let f(x) be the model's logit for row x and E[f] its mean over the background. The absolute residual is the maximum, across classes, of |Σ SHAP − (f(x) − E[f])|; dividing it by the maximum, across classes, of |f(x) − E[f]| gives the relative residual.
<!-- src: PROJECT_INSTRUCTIONS.md -->

### The validation pool

We explained 500 validation rows with the served model, using 4000 samples each (@tab:valpool). Eighteen rows have a relative residual over 8%: 7 Bot rows, 4 Benign, 4 WebAttack and the single worst row, an Infiltration flow at 21.2%. Early notes had given a "3–8%" range, but no file supported it, so that range is no longer used. For the 14 test rows of the explanation check the residual cannot be computed again: their saved SHAP files do not store the model outputs needed.
<!-- src: PROJECT_INSTRUCTIONS.md; results/shap/fedavg_a0.5_s42/val_pool_summary.json -->

Table: Additivity residuals on 500 validation rows {#tab:valpool}
| Residual | Median | p95 | Maximum |
|---|:-:|:-:|:-:|
| Relative | 3.2% | 7.7% | 21.2% |
| Absolute (logit) | 0.472 | 1.105 | 3.336 |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/contribution_a_results.md -->

### Audit of stored residuals

Each stored SHAP file records one value: the worst residual among its 14 rows. Comparing that with a single-row maximum is therefore rough. The smallest stored value is 0.156 and the largest 15.874. @tab:residaudit counts how many files exceed 3.336, the highest value seen in the validation pool. Of the 99 FedAvg files from final rounds, 4 do: silos 3 and 9 of α=0.1 seed 42, silo 8 of α=0.1 seed 1337, and the global model of α=5.0 seed 1337 (3.500). In two cases the silo is the smallest one of its run.
<!-- src: results/inspection/residual_audit_summary.json; docs/contribution_a_results.md; PROJECT_INSTRUCTIONS.md -->

Table: Files whose stored residual exceeds 3.336, and the final-round Spearman r linking residual to Jaccard@10 per silo {#tab:residaudit}
| Pass | α=0.1 | α=0.5 | α=5.0 | Silo / global |
|---|:-:|:-:|:-:|:-:|
| FedAvg final | 3/33 | 0/33 | 1/33 | 3/90, 1/9 |
| FedAvg round-wise | 26/132 | 0/132 | 5/132 | 29/360, 2/36 |
| FedProx final | 1/33 | 0/33 | 0/33 | 1/90, 0/9 |
| Spearman r (n), final | −0.237 (29) | 0.202 (30) | 0.11 (30) | |
<!-- src: results/inspection/residual_audit_summary.json -->

### Pre-specified sensitivity check and a post-hoc variant

The exclusion rule was fixed before computing: remove every silo with a final-round residual above 3.336. At α=0.1 this takes out two silos that had eligible rows, 8 rows out of 220. The Jaccard@10 median stays at 0.333, and the τ median moves from 0.592 to 0.597. Nothing is removed at α=0.5 or α=5.0.
<!-- src: PROJECT_INSTRUCTIONS.md -->

**Post-hoc, and not part of the pre-specified rule:** removing the entire α=5.0, seed-1337 run, whose global model exceeded the limit, leaves the α=5.0 medians unchanged, with Jaccard@10 at 0.667 and τ at 0.844. The headline therefore does not depend on the high-residual files.
<!-- src: PROJECT_INSTRUCTIONS.md -->
