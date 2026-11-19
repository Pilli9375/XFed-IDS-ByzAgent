# Introduction

An intrusion detection system (IDS) inspects network flows and raises an alert when one looks like an attack. A detector learns better from many organizations' traffic than from one, yet flow records name internal hosts and users, so organizations rarely share them. Federated learning (FL) addresses this: each participant trains on its own data and sends only model weights to a server, which averages them into a shared model [@mcmahan2017]. Federated detectors for IoT and enterprise traffic have been reported to come close to centrally trained ones [@nguyen2019diot; @rahman2020; @campos2022].

Accuracy alone, however, leaves two practical questions open. The first is about explanations. Every silo holds a local model fitted to its own skewed slice of traffic, so an analyst's explanation of an alert may depend on which silo's model produced it. The second is about participants. The server never sees data, so a silo that relabels its own traffic can bend the shared model [@tolpegin2020], and robust aggregation rules that look for outlying updates [@blanchard2017; @yin2018] may also flag honest silos whose data are simply unusual.

XFed-IDS-ByzAgent studies both questions in one system. It is built in five stages: the data, the federated training, two checks (one of explanations, one of trust) and, last, a dashboard. The two checks share the same training runs but are separate experiments, and their findings are reported separately.

## Objectives {#sec:objectives}

- Prepare the corrected Distrinet release of CICIDS2017 as eight attack families plus Benign, with a documented cleaning record and a group-aware split.
- Train a shared detector across 10 simulated organizations under Dirichlet label skew at three levels and three seeds, selecting every model and round on validation data.
- Measure whether each organization's SHAP explanation ranking matches the global model's, read against a chance level and a seed-noise floor.
- Test a worst-case label-flipping attack against Krum, Multi-Krum, trimmed mean and an LLM trust agent (ByzAgent), and audit how faithful the agent's stated reasons are.
- Run one preregistered optimizer comparison, scored on the test set once, and measure serving and communication cost.
- Deliver a dashboard that shows detection, explanations and trust decisions together, with every number linked to its source file.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Background and Literature Survey {#sec:literature}

**Federated intrusion detection.** FedAvg [@mcmahan2017] is the default aggregation rule, and federated IDS work has used it for IoT anomaly detection [@nguyen2019diot], IoT intrusion detection [@rahman2020] and attack detection with recurrent models [@mothukuri2022]; surveys list heterogeneous data as a central open problem [@campos2022; @agrawal2022]. Non-IID splits are usually generated with a Dirichlet distribution over class shares [@hsu2019], and remedies include a proximal client term (FedProx) [@li2020fedprox], server momentum [@hsu2019] and adaptive server optimizers [@reddi2021]. These studies judge success by accuracy only.

**Explanations in federated IDS.** To explain an IDS alert in terms of flow features, most work uses SHAP [@lundberg2017]. A number of federated detectors already output such explanations [@dong2022fedforest; @thi2023xfedhunter; @bilal2025; @gholamrezazadeh2026], yet none checks whether different participants explain the same alert alike. Oki et al. [@oki2024] measured how far per-site feature sets drift from a centralized detector and found that federated training narrows the gap. A recent survey of federated explainability names explanation consistency on non-IID clients as unsolved and notes that no agreed metric exists [@gholizade2026]. Outside FL, Watson et al. [@watson2022] showed that models differing only in their random seed can disagree about reasons, which means any agreement value needs a seed-noise reference.

**Byzantine robustness and LLM agents.** Krum and Multi-Krum keep the updates closest to their neighbours [@blanchard2017], and trimmed mean drops extreme values in every coordinate [@yin2018]. Both assume that honest clients look alike, which strong label skew breaks. Language-model agents have been used in security tasks such as penetration testing [@deng2024pentestgpt], but a model's written reasons need not match what drove its output [@turpin2023], so an agent's rationale must be checked against its inputs.

**The dataset.** CICIDS2017 [@sharafaldin2018] was corrected by Engelen et al. [@engelen2021], and Liu et al. [@liu2022] released the refined Distrinet version used here.

**How this project differs.** We extend Oki et al. by varying label skew to find where federated explanation agreement weakens, and we add a seed-noise floor that none of the federated IDS works report. For the trust check, we test the Krum family on 10 silos with the true attacker count given as an oracle, and we audit the agent's stated reasons. We do not claim the combination of federated learning, intrusion detection and explainability as new, and the dashboard's LLM summaries exist only for usability; we make no research claim about them. @tab:related compares the closest works.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Table: How the closest works compare with this project (a mark means the work's abstract or text shows the property) {#tab:related}
| Work | FL | IDS | XAI | Consistency metric | Seed control | Byzantine defence | LLM agent |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| DÏoT [@nguyen2019diot] | ✓ | ✓ | | | | | |
| FEDFOREST [@dong2022fedforest] | ✓ | ✓ | ✓ | | | | |
| XFedHunter [@thi2023xfedhunter] | ✓ | ✓ | ✓ | | | | |
| Oki et al. [@oki2024] | ✓ | ✓ | ✓ | ✓ | | | |
| Bilal et al. [@bilal2025] | ✓ | ✓ | ✓ | | | | |
| Watson et al. [@watson2022] | | | ✓ | ✓ | ✓ | | |
| PentestGPT [@deng2024pentestgpt] | | | | | | | ✓ |
| This project | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Organization of the Report {#sec:organization}

- Chapter 2 describes the system, the methodology, the standards used, the software and hardware, and how the system was tested.
- Chapter 3 gives the cost analysis.
- Chapter 4 presents the results, the negative results, the limitations and the challenges we met.
- Chapter 5 concludes, outlines future work and records each member's contribution.
- Chapter 6 holds key code excerpts; the complete experimental record is in the project repository.
- Chapter 7 lists the references.
<!-- numcheck: ignore -->
