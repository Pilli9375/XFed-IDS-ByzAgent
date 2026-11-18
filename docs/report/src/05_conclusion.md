# Conclusion and Future Work

## Conclusion {#sec:conclusion}

In this project we built XFed-IDS-ByzAgent, a federated detector that is judged on more than accuracy. It also asks two questions: do the participants' models rely on the same evidence when they detect an attack, and can each participant be trusted? The system runs end to end: corrected CICIDS2017 data, federated training across ten simulated organizations, the two checks, and a dashboard that puts live alerts, their explanations and the trust decisions on one screen.

On detection, FedAvg matches a centralized model when the organizations hold similar data, and loses whole attack families when their data is severely skewed. Test macro-F1 is 0.990 ± 0.001 at α=5.0 and 0.516 ± 0.048 at α=0.1. A preregistered comparison, scored on the test set only once, found that server momentum stabilises the moderate-skew case and gives a modest gain at severe skew.
<!-- src: PROJECT_INSTRUCTIONS.md -->

The explanation check found that agreement between each organization's explanation and the global model's explanation falls as label skew grows. It stays well above chance at every skew level. Compared with a seed-noise floor built from centralized models, agreement at severe skew is no higher than seed changes alone would give. Because the confidence interval touches the floor, we report this as directional, not significant. KL divergence from the global label mix predicts agreement beyond what silo size explains, on observational evidence.

The trust check, a separate experiment, ran a worst-case label-flipping attack. Every mechanism tested reacted to how unusual a silo's data was. Multi-Krum excluded a malicious silo 0% of the time, and its one apparent success was an artifact of composition. ByzAgent's flags rose under attack for silos whose flag rate had room to rise, and the reasons it gave, once checked against its inputs, were only partly accurate.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Taken together, the project shows that a federated IDS can be built to report on its own explanations and its own participants, and it shows how much care such reports need. Without a seed-noise reference, an agreement number cannot be interpreted. Without a clean-run baseline per silo, a flag rate cannot be interpreted. And without an audit of what was cited, an agent's explanation cannot be trusted. We kept every number traceable to a file, reported negative results alongside positive ones, and kept the two checks' findings apart.

## Future Work {#sec:future}

Several next steps follow directly from the limitations in Section 4.6.

- **Partitions in which size and skew vary separately.** Under the Dirichlet partitioner the two move together, so their effects on agreement could be separated only by observation. A design that equalizes silo sizes while varying skew would allow an experimental test.
- **Several seeded SHAP draws behind every headline value.** The parity monitor already averages three draws with fixed seeds. Doing the same for the headline agreement pipeline would remove one source of noise and allow its size to be measured.
- **More seeds for the instability floor.** Three seed pairs give a median, not a reliable interval. More centralized seeds would tighten the floor and might settle the α=0.1 question either way.
- **A way of choosing attackers that is independent of composition.** The worst-case rule chooses the silos with the most extreme label mix, and that is exactly what every detector responds to. A different selection rule, or a different partition, is needed to separate detection of attacks from detection of unusual data.
- **Explanation agreement under server momentum.** FedAvgM improved accuracy in the preregistered study, but whether it also changes explanation agreement was not tested.
- **A real deployment.** All results come from simulation on one machine. Running the federation across machines would expose network cost, stragglers and client failures that the simulation does not model.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Contribution of Each Member {#sec:contributions newpage}

**V Naga Adithya (23BCE9062):** Built the federated training pipeline on Flower and ran the FedAvg, FedProx and FedAvgM experiments across all label-skew levels and seeds. Designed and ran the preregistered accuracy study and the efficiency work (ONNX serving, update compression, communication cost). Developed the dashboard, both the FastAPI backend and the React frontend, including the hot-swap gate and the validation-only simulator. Led the testing, the audits (including the test-set exposure audit) and the reproducibility setup, and wrote the IEEE paper, this report, the team handbook and the README.
<!-- src: paper/main.tex -->

**T Shaun (23BCE9916):** Prepared the dataset. Cleaned the Distrinet CICIDS2017 (V4) data into eight attack families plus Benign, built the group-aware train, validation and test split, and created the Dirichlet partitions for the ten silos with the SHA256 manifest that checks every partition at load time.
<!-- src: paper/main.tex -->

**P Sampath (23BCE8614):** Built the trust check. Implemented the worst-case label-flipping attacks, the per-silo behaviour statistics and the Krum, Multi-Krum and trimmed-mean baselines, and developed ByzAgent, the local LLM agent that decides to trust, downweight or quarantine each silo, together with its fidelity and decision-stability audits.
<!-- src: paper/main.tex -->

**D Tharun (23BCE8818):** Built the explanation check. Implemented client-side SHAP with fixed backgrounds, the Jaccard@10 and weighted Kendall's τ agreement measures, the centralized-seed instability floor and chance level, and the SHAP additivity residual audit with its sensitivity check.
<!-- src: paper/main.tex -->
