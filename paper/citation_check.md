# Citation check

Every entry in `paper/refs.bib` was looked up on 2026-11-18 and confirmed to exist with the
title, authors, venue and year given. Lookups used the Crossref API (DOI records), the arXiv
abstract pages, OpenAlex, and the publishers' own pages (USENIX, NeurIPS proceedings, MLSys,
ICLR virtual site, SciTePress, IEEE). DBLP was not used because it served a bot challenge to
automated requests. The abstract of each paper was saved to `paper/_sources/` (git-ignored)
where one was available, and each paper is cited only for a claim stated in its abstract or
text. All 58 entries are cited in the paper; no cited key is missing from the bibliography.

Corrections made during the check:

* **Gholizade et al.** is arXiv:2607.13045 (posted 2026-06-15) and is also published in
  *Expert Systems with Applications* (DOI 10.1016/j.eswa.2026.133183, per the arXiv record).
  The bib entry gives the journal with the arXiv ID as a note.
* **Oki et al.** full record found through Crossref: A. Oki, Y. Ogawa, K. Ota, M. Dong,
  IEEE Networking Letters 6(3):198–202, 2024.
* **PentestGPT**: the USENIX Security 2024 title differs from the arXiv title; the published
  title is used.
* **FoolsGold**: cited under its RAID 2020 title, "The Limitations of Federated Learning in
  Sybil Settings" (arXiv title: "Mitigating Sybils in Federated Learning Poisoning").
* **Watson et al.** page range: Crossref gives 1524–1533; a secondary source said 875–884.
  The Crossref range is used.
* **Kendall (1938)**: Crossref lists only the first page (81); no page range is given in the bib.
* **Xu et al. (LLMs for cyber security)**: published in ACM TOSEM vol. 35 no. 11 (2026);
  cited as the journal version.
* No abstract text could be saved automatically for Sharafaldin et al., Lanvin et al.,
  Blanchard et al. or Kendall; their content was confirmed on the publisher pages
  (SciTePress, HAL/Springer, NeurIPS proceedings, JSTOR/Crossref), and the overlap check had no
  abstract to compare against for these four.

| Bib key | Verified at (DOI / arXiv / page) | What the paper actually says that we rely on |
|---|---|---|
| mcmahan2017 | arXiv:1602.05629; AISTATS 2017, PMLR pp. 1273–1282 (OpenAlex) | Introduces FedAvg: clients train locally and the server averages their weights. |
| nguyen2019diot | doi:10.1109/ICDCS.2019.00080 | DÏoT: federated, device-type-specific anomaly detection for IoT across gateways. |
| rahman2020 | doi:10.1109/MNET.011.2000286 | Compares centralized, on-device and federated training for IoT intrusion detection. |
| mothukuri2022 | doi:10.1109/JIOT.2021.3077803 | FL-based anomaly detection (GRU models) for IoT attacks. |
| campos2022 | doi:10.1016/j.comnet.2021.108661 | Review and experiments on FL for IoT IDS; identifies challenges and future directions. |
| agrawal2022 | doi:10.1016/j.comcom.2022.09.012; arXiv:2106.09527 | Survey of FL for IDS: concepts, challenges of FL implementations, and directions. |
| popoola2022 | doi:10.1109/JIOT.2021.3100755 | Federated deep learning for zero-day botnet detection on IoT-edge devices. |
| li2022noniid | doi:10.1109/ICDE53745.2022.00077 | Benchmark of FL algorithms under non-IID silos with partitioning strategies covering typical skew cases. |
| hsu2019 | arXiv:1909.06335 | Synthesises splits with a continuous range of non-identicalness; server momentum (FedAvgM) mitigates the drop. |
| li2020fedprox | MLSys 2020, pp. 429–450; arXiv:1812.06127 | FedProx: a proximal term on local objectives for heterogeneous federated networks. |
| reddi2021 | ICLR 2021; arXiv:2003.00295 | Adaptive server optimizers FedAdam, FedYogi, FedAdagrad. |
| beutel2020flower | arXiv:2007.14390 | Flower, the FL framework our harness is built on. |
| lundberg2017 | NeurIPS 2017 proceedings, pp. 4765–4774; arXiv:1705.07874 | SHAP: additive feature attributions based on Shapley values. |
| wang2020xai | doi:10.1109/ACCESS.2020.2988359 | Uses SHAP to explain IDS decisions locally and globally. |
| warnecke2020 | doi:10.1109/EuroSP48549.2020.00018 | Criteria for evaluating explanation methods in security, including robustness. |
| neupane2022 | doi:10.1109/ACCESS.2022.3216617 | Survey of the state of the art in XAI for IDS and its current challenges. |
| arisdakessian2023 | doi:10.1109/JIOT.2022.3203249 | IoT IDS survey naming FL and explainable AI as future directions. |
| oki2024 | doi:10.1109/LNET.2024.3465516 | FL applied to a distributed IDS; XAI shows the per-class feature-set distance to the non-distributed IDS shrinks under FL and grows under independent learning. |
| gholizade2026 | arXiv:2607.13045; doi:10.1016/j.eswa.2026.133183 | FedXAI survey: notes the lack of standard metrics for explanation quality and stability, and lists explainability under non-IID data as a key challenge. |
| dong2022fedforest | arXiv:2201.03134 | FEDFOREST: interpretable GBDT-based federated NIDS. |
| thi2023xfedhunter | arXiv:2309.08485 | XFedHunter: explainable FL framework for APT detection in SDN. |
| bilal2025 | doi:10.1109/ACCESS.2025.3613459 | FL (FedAvg) with SHAP and LIME for malicious IoT traffic detection. |
| gholamrezazadeh2026 | arXiv:2605.19448 | XAI FL-IDS: FL with SHAP explanations, 10 clients, XGBoost on Edge-IIoTset. |
| watson2022 | doi:10.1109/WACV51458.2022.00159; arXiv:2105.06791 | Identical architectures trained with different seeds/shuffles give inconsistent explanations; introduces a consistency measure. |
| krishna2024 | TMLR 2024; arXiv:2202.01602 | Quantitative framework for disagreement between explanation methods; disagreement is frequent in practice. |
| ghorbani2019 | doi:10.1609/aaai.v33i01.33013681 | Attributions can change markedly under small input perturbations. |
| alvarezmelis2018 | arXiv:1806.08049 | Interpretability methods can be unstable to small input changes. |
| slack2021 | NeurIPS 2021; arXiv:2008.05030 | Post hoc explanations carry estimation uncertainty; models it with Bayesian versions of LIME/KernelSHAP. |
| vigna2015 | doi:10.1145/2736277.2741088 | Weighted correlation index for rankings (weighted Kendall's tau, the scipy implementation). |
| kendall1938 | doi:10.2307/2332226 | Defines Kendall's rank correlation coefficient. |
| petsiuk2018 | BMVC 2018; arXiv:1806.07421 | Proposes deletion and insertion metrics for judging saliency/attribution faithfulness. |
| erion2021 | doi:10.1038/s42256-021-00343-w | Expected gradients, the attribution method behind SHAP's GradientExplainer. |
| blanchard2017 | NeurIPS 2017 proceedings (pp. 118–128 per OpenAlex) | Krum: linear aggregation tolerates no Byzantine worker; Krum selects the update closest to its neighbours (Multi-Krum variant). |
| yin2018 | ICML 2018, PMLR pp. 5650–5659; arXiv:1803.01498 | Coordinate-wise median and trimmed mean for Byzantine-robust distributed learning. |
| mhamdi2018 | ICML 2018, PMLR pp. 3521–3530; arXiv:1802.07927 | Bulyan, combining Krum-style selection with trimmed aggregation. |
| fung2020 | RAID 2020, pp. 301–316 (OpenAlex); arXiv:1808.04866 | FoolsGold: identifies poisoning sybils from the diversity of client updates during training. |
| cao2021fltrust | doi:10.14722/ndss.2021.24434 | FLTrust: server holds a small root dataset to bootstrap trust in client updates. |
| karimireddy2021 | ICML 2021, PMLR 139:5311–5319; arXiv:2012.10333 | Iterative clipping plus worker momentum to resist attacks coupled across rounds. |
| fang2020local | USENIX Security 2020, pp. 1605–1622; arXiv:1911.11815 | Crafted local model poisoning defeats Krum, trimmed mean, median and Bulyan. |
| tolpegin2020 | doi:10.1007/978-3-030-58951-6_24 | Label-flipping data poisoning against FL systems. |
| nguyen2020poison | doi:10.14722/diss.2020.23003 | Backdoor data poisoning against FL-based IoT IDS that evades existing defences. |
| yao2023react | ICLR 2023; arXiv:2210.03629 | ReAct: LLMs interleave reasoning traces with actions. |
| deng2024pentestgpt | USENIX Security 2024, pp. 847–864 (usenix.org) | LLM-based penetration testing agent with self-interacting modules. |
| fang2024oneday | arXiv:2404.08144 | LLM agents can autonomously exploit known (one-day) vulnerabilities. |
| xu2026llmsec | doi:10.1145/3769676 | Systematic literature review of LLMs for cyber security tasks. |
| turpin2023 | NeurIPS 2023; arXiv:2305.04388 | Chain-of-thought explanations can misrepresent the true reason for a model's answer. |
| grattafiori2024llama3 | arXiv:2407.21783 | Describes the Llama 3 model family (the agent uses Llama 3.1 8B instruct). |
| sharafaldin2018 | doi:10.5220/0006639801080116 (SciTePress page) | Introduces the CICIDS2017 dataset of benign and attack flows. |
| engelen2021 | doi:10.1109/SPW53761.2021.00009 | Documents errors in CICIDS2017 traffic generation, flow construction, feature extraction and labelling; fixes them. |
| liu2022 | doi:10.1109/CNS56114.2022.9947235 | Further error analysis of CIC-IDS-2017/CSE-CIC-IDS-2018 and the refined release we use. |
| lanvin2023 | doi:10.1007/978-3-031-31108-6_2 (HAL hal-03775466) | A separate correction of CICIDS2017 labelling/capture errors; not used here. |
| arp2022 | USENIX Security 2022, pp. 3971–3988 (usenix.org) | Pitfalls of ML in security research, including data snooping. |
| cui2019 | doi:10.1109/CVPR.2019.00949 | Class-balanced loss using the effective number of samples (our class weights). |
| ba2016 | arXiv:1607.06450 | Layer normalization (per-sample statistics; no running batch statistics). |
| chen2016xgb | doi:10.1145/2939672.2939785 | XGBoost gradient-boosted trees (our centralized baseline). |
| loshchilov2019 | ICLR 2019; arXiv:1711.05101 | AdamW, decoupled weight decay (our local optimizer). |
| fieldwelsh2007 | doi:10.1111/j.1467-9868.2007.00593.x | Bootstrap methods for clustered data (basis for resampling whole silos). |
| iglewicz1993 | ASQC Basic References in Quality Control vol. 16 (1993); NIST handbook citing it | Modified z-score from median and MAD, with 3.5 as the outlier cut-off. |
