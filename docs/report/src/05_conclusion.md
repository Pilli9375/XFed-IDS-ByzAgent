# Conclusion and Future Work

## Conclusion {#sec:conclusion}

This project built XFed-IDS-ByzAgent, a federated intrusion detection system that goes one step past accuracy. It asks whether the participants' models detect attacks for the same reasons, and whether any participant can be trusted. The system runs end to end: corrected CICIDS2017 data, federated training across ten simulated organizations, an explanation check, a trust check, and a dashboard that shows live detection, explanations and trust decisions together.

On detection, FedAvg matches a centralized model when the organizations hold similar data, and loses whole attack families when their data is severely skewed. Test macro-F1 is 0.990 ± 0.001 at α=5.0 and 0.516 ± 0.048 at α=0.1. A preregistered comparison, scored on the test set only once, found that server momentum stabilises the moderate-skew case and gives a modest gain at severe skew.
<!-- src: PROJECT_INSTRUCTIONS.md -->

The explanation check found that agreement between each organization's explanation and the global model's explanation falls as label skew grows. It stays well above chance at every skew level. Read against a seed-noise floor that we built from centralized models, the agreement at severe skew sits at the level that random seeds produce on their own. Because the confidence interval touches the floor, we report this as directional, not significant. KL divergence from the global label mix predicts agreement beyond what silo size explains, on observational evidence.

The trust check, a separate experiment, ran a worst-case label-flipping attack. Every mechanism tested reacted to how unusual a silo's data was. Multi-Krum excluded a malicious silo 0% of the time, and its one apparent success was an artifact of composition. ByzAgent's flags responded to the attack where silos were not already saturated, and its decisions came with a rationale whose fidelity we measured and found to be partial.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Taken together, the project shows that a federated IDS can be built to report on its own explanations and its own participants, and it shows how much care such reports need. Without a seed-noise reference, an agreement number cannot be interpreted. Without a clean-run baseline per silo, a flag rate cannot be interpreted. And without an audit of what was cited, an agent's explanation cannot be trusted. We kept every number traceable to a file, reported negative results alongside positive ones, and kept the two checks' findings apart.

## Future Work {#sec:future}

Several next steps follow directly from the limitations in Section 4.6.

- **A partitioning design that varies size and skew independently.** The Dirichlet partitioner ties the two together, so their effects on agreement could only be separated observationally. A design that equalizes silo sizes while varying skew would allow an experimental test.
- **Seeded, multi-draw SHAP for the headline numbers.** The parity monitor already averages three seeded draws. Doing the same for the headline agreement pipeline would remove one source of noise and allow its size to be measured.
- **More seeds for the instability floor.** Three seed pairs give a median, not a reliable interval. More centralized seeds would tighten the floor and might settle the α=0.1 question either way.
- **Attacker selection that does not ride the composition axis.** The worst-case rule picks the most compositionally extreme silos, which is the same axis every detector reacts to. A different selection rule, or a different partition, is needed to separate detection of attacks from detection of unusual data.
- **Explanation agreement under server momentum.** FedAvgM improved accuracy in the preregistered study, but whether it also changes explanation agreement was not tested.
- **A real deployment.** All results come from simulation on one machine. Running the federation across machines would expose network cost, stragglers and client failures that the simulation does not model.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Contribution of Each Member {#sec:contributions}
