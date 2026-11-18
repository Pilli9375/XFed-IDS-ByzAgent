# Introduction

A network intrusion detection system (IDS) watches traffic and raises an alert when a flow looks like an attack. Modern detectors are trained on labelled flow records, and their quality depends heavily on how varied those records are. A university, a hospital and a bank each see a different slice of the attack landscape. A detector trained by any one of them alone will miss attack types that only the others have seen. The obvious fix, pooling every organization's flow records in one place, is usually not allowed. Flow records name internal hosts, users and services, and contracts, privacy rules and plain caution keep them inside the organization that collected them.

Federated learning (FL) offers a way to train a shared model without moving the data [@mcmahan2017]. Each participant, called a client or silo, trains a copy of the model on its own data, and only the resulting weights go to a coordinating server, which averages them into a new global model. Several groups have applied this idea to intrusion detection and report accuracy close to that of a centrally trained detector [@nguyen2019diot; @rahman2020; @mothukuri2022; @campos2022; @agrawal2022].

When we started the project, we noticed that most of this work stops at accuracy. For a system that people would actually run, two further questions matter just as much, and they are the reason this project exists.

The first question concerns explanations. When an analyst receives an alert, the label alone is not enough: the analyst wants to know which features of the flow made the model call it an attack. In a federation, each silo keeps a local copy of the model, fitted to a skewed slice of traffic. Suppose those copies lean on different features. Then the analyst's explanation changes with the silo that produced it, and it no longer describes "the detector" as a whole. We wanted to measure how far the silos' explanations agree, how that agreement changes as the silos' data grows more different, and how much disagreement random seeds alone produce.

The second question concerns the participants. The server sees only weight updates, never data. A silo that quietly relabels its own training data can bend the shared model, and nothing in plain averaging would notice [@tolpegin2020; @nguyen2020poison]. Byzantine-robust aggregation rules were designed for this threat [@blanchard2017; @yin2018], but they look for updates that are geometric outliers. In a federation where honest silos hold very different data, an honest but unusual silo can look like an outlier too. We wanted to test what these rules actually exclude in such a setting, and whether a language-model agent that reads simple per-silo statistics can do better while also writing down its reasons.

To study both questions in one place, we built XFed-IDS-ByzAgent. It is one system built in five stages. The data stage and federated training come first; the explanation check and the trust check follow; a dashboard sits on top. The explanation check and the trust check run on the same federated training, but they are different experiments with different evidence, and this report keeps their findings apart throughout.

## Objectives {#sec:objectives}

The project set out to do the following.

- Prepare the corrected Distrinet release of CICIDS2017 as eight attack families plus a Benign class, with a documented cleaning record, a group-aware train/test split and a fixed validation set.
- Train a shared detector across 10 simulated organizations with FedAvg under realistic label skew, using Dirichlet partitions at three skew levels and three seeds, and select every model and every round on validation data only.
- Measure how closely each organization's SHAP explanation ranking matches the global model's ranking, using Jaccard@k and weighted Kendall's τ, and read each value against a chance level and a seed-noise floor built from centralized models.
- Tell the effect of label skew on explanation agreement apart from the effect of silo size, since the Dirichlet partitioner links the two.
- Build a trust check in which a worst-case label-flipping attack is run against the federation, and compare an LLM trust agent (ByzAgent) with three classical rules: Krum, Multi-Krum and trimmed mean.
- Audit the agent: how stable its decisions are, and how often the reasons it writes down match the numbers it was given.
- Run one preregistered comparison of federated optimizers, scored on the test set exactly once.
- Measure serving latency, communication per round and the effect of update compression.
- Deliver a working dashboard that shows live detection, explanations and trust decisions together, with every displayed number linked to the file it came from.
- Keep a record of each read of the test set and of each negative or null result, so the report never claims more than its evidence shows.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Background and Literature Survey {#sec:literature}

This section reviews the six bodies of work that the project draws on. It closes by stating how this project differs from them. Every work cited here is in the project's verified bibliography.

### Federated learning and federated intrusion detection

McMahan et al. introduced federated averaging (FedAvg), in which clients run several local steps of gradient descent and the server averages the resulting weights, weighted by each client's number of examples [@mcmahan2017]. FedAvg remains the default aggregation rule, and most federated IDS studies keep it.

Early applications in network security focused on the Internet of Things. DÏoT trained anomaly models for individual device types across home gateways and flagged compromised devices without collecting their traffic centrally [@nguyen2019diot]. Rahman et al. proposed a federated scheme for IoT intrusion detection that keeps training and inference on the devices, and set it against centralized and purely on-device learning [@rahman2020]. Mothukuri et al. used recurrent models trained federatedly to detect IoT attacks [@mothukuri2022], and Popoola et al. applied federated deep learning to zero-day botnet detection [@popoola2022]. Two reviews collect the open problems that still sit between federated detection and deployment, among them heterogeneous data, communication cost and poisoning [@campos2022; @agrawal2022].

Heterogeneous data, usually called non-IID data, is the central difficulty. When clients hold different label mixes, their local models pull in different directions and the averaged model can be worse than any client expects. Benchmarks create controlled non-IID splits by drawing each client's share of every class from a Dirichlet distribution whose concentration parameter sets the degree of skew [@hsu2019; @li2022noniid]. Several server-side and client-side remedies exist. FedProx adds a proximal term to each client's objective that keeps local weights close to the global model [@li2020fedprox]. Server momentum (FedAvgM) treats the averaged update as a gradient and applies momentum to it on the server [@hsu2019]. Adaptive server optimizers such as FedAdam and FedYogi apply Adam-style or Yogi-style updates on the server [@reddi2021]. We used the Flower framework to run all federated training [@beutel2020flower].

What these studies share is their yardstick: detection accuracy. What none of them checks is whether two silos flag an attack because of the same features.

### Explainable intrusion detection and federated explanations

SHAP attributes a model's output to its input features using Shapley values from cooperative game theory, and it has become the common way to explain individual IDS decisions [@lundberg2017; @wang2020xai]. Its gradient-based variant integrates gradients against a background sample and suits neural networks [@erion2021]. Neupane et al. surveyed explainable IDS and its open challenges, starting from the problem that deep-learning detectors give the analysts who rely on them no justification for their alerts [@neupane2022]. Warnecke et al. proposed criteria for judging explanation methods in security tasks, with robustness among them [@warnecke2020]. Arisdakessian et al. argued for combining explainability with federated learning in IoT intrusion detection [@arisdakessian2023].

Several systems now add explanations to a federated detector. FEDFOREST builds an interpretable federated detector on gradient-boosted trees [@dong2022fedforest]. XFedHunter explains the detection of advanced persistent threats in software-defined networks [@thi2023xfedhunter]. Bilal et al. combine FedAvg with SHAP and LIME for malicious IoT traffic [@bilal2025], and Gholamrezazadeh and Montazerolghaem present a federated SHAP-based framework for distributed IDS [@gholamrezazadeh2026]. These systems produce explanations, but none of them compares the explanations of different participants with each other.

Oki et al. come closest to our question [@oki2024]. They measured the distance between the per-class feature sets of a distributed IDS and a non-distributed one and reported that federated learning brings these explanations closer. The 2026 federated XAI survey of Gholizade et al. names explanation behaviour on non-IID clients as an open problem, and observes that no agreed metric yet exists for scoring the consistency of federated explanations [@gholizade2026].
<!-- src: paper/refs.bib -->

### Stability and consistency of explanations

Outside federated learning, explanation stability has been studied directly. Attributions can change under small perturbations of the input that do not change the prediction [@ghorbani2019; @alvarezmelis2018], and explainers that work by sampling add estimation noise of their own, which can be summarised with credible intervals [@slack2021]. Watson et al. retrained models of identical architecture with different random seeds and data orderings and found low agreement among their explanations [@watson2022]. So two models may give different reasons for a decision even when their training data are identical. Krishna et al. formalised disagreement between explanation methods and showed that practitioners meet it often [@krishna2024].

Two tools from this literature are used in our measurement. Kendall's rank correlation counts concordant and discordant pairs between two rankings [@kendall1938], and its weighted form gives more weight to disagreements near the top of the ranking, where an analyst actually looks [@vigna2015]. Deletion and insertion curves check faithfulness: they remove or add the highest-ranked inputs in order and track how the model's score changes [@petsiuk2018].

Federated studies, as far as we found, publish agreement values with no seed-noise reference beside them, even though Watson et al.'s result shows such a reference is needed. A federated agreement value means little until one knows how much agreement identical, centrally trained models reach.

### Byzantine-robust aggregation and poisoning

Krum chooses the single update whose summed distance to its nearest neighbours is smallest, and Multi-Krum keeps several such updates and averages them [@blanchard2017]. Coordinate-wise trimmed mean sorts each parameter across clients and discards a fixed fraction of the largest and smallest values before averaging [@yin2018]. Bulyan combines the two ideas [@mhamdi2018]. Later defences take other routes: FLTrust scores each update against one computed on a small root dataset held by the server [@cao2021fltrust]; FoolsGold looks at the diversity of client updates over time to catch coordinated sybils [@fung2020]; and centered clipping with worker momentum carries information across rounds [@karimireddy2021].

On the attack side, Fang et al. showed that crafted local updates can bypass distance-based rules [@fang2020local]. Tolpegin et al. studied label flipping, the attack used in this project, in federated settings [@tolpegin2020], and Nguyen et al. demonstrated poisoning and backdoor attacks against federated IoT intrusion detectors in particular [@nguyen2020poison].

Most of these evaluations assume that honest clients look alike. With strong label skew, honest clients differ a great deal, and few studies measure how this changes what the rules throw out.

### Language-model agents for security decisions

Language-model agents that alternate between reasoning steps and actions [@yao2023react] have been used for penetration testing [@deng2024pentestgpt] and for exploiting vulnerabilities that are already public [@fang2024oneday], and a recent survey maps many other uses of large language models in security [@xu2026llmsec]. Llama 3 is one family of openly available models that can be run locally for such work [@grattafiori2024llama3]. A known weakness matters for us: a model's written explanation may not match the factors that really produced its answer [@turpin2023]. An agent that sits inside an aggregation loop therefore needs its stated reasons compared with its inputs; they cannot simply be trusted.

### CICIDS2017 and its corrections

CICIDS2017 is one of the most widely used IDS benchmarks [@sharafaldin2018]. Engelen et al. found errors in how its flows were built, how features were extracted and how flows were labelled, and released corrected data with an extra label for attack attempts that carry no payload [@engelen2021]. Liu et al. traced further problems through the dataset's lifecycle and released the refined Distrinet version that we use [@liu2022]. Lanvin et al. corrected a separate set of issues in a different branch, which we did not use [@lanvin2023]. Arp et al. list data snooping, such as tuning on the test set, among the common pitfalls of machine learning in security [@arp2022]. That warning is the reason this project keeps a written audit of every way its test set was read.

### How this project differs from prior work

Our explanation check starts from the work of Oki et al. [@oki2024]. Their finding was that federated training pulls per-site explanations toward each other. We sweep label skew from severe to nearly IID to find where that pull stops working. We do not dispute their finding. We characterise where it stops holding.

We also measure a reference that the federated IDS papers above leave out: how much feature rankings differ between centralized models whose only difference is the random seed. A federated gap has to exceed this seed-noise floor before federation can be held responsible for it. The floor also offers one practical reply to the lack of a consistency metric that Gholizade et al. describe [@gholizade2026].

For the trust check, we test Krum and its variants on a federation of 10 silos with the true number of attackers handed to them as an oracle. We also audit how often the agent's own written reasons are accurate when checked against the statistics it saw.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Two limits on our claims follow from this survey. This report makes no priority claim for measuring explanation agreement in a federated IDS. Nor does it present the combination of federated learning, intrusion detection and explainability as new, since recent work already combines them [@dong2022fedforest; @thi2023xfedhunter; @bilal2025; @gholamrezazadeh2026]. The dashboard's one-sentence LLM summaries beside each alert exist for usability only; they are not a research result.

Table: How the closest works compare with this project. A mark means the property is shown in the work's abstract or text, as we read it. {#tab:related}
| Work | FL | IDS | XAI | Consistency metric | Seed control | Byzantine defence | LLM agent |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| DÏoT [@nguyen2019diot] | ✓ | ✓ | | | | | |
| Nguyen et al. [@nguyen2020poison] | ✓ | ✓ | | | | ✓ | |
| FLTrust [@cao2021fltrust] | ✓ | | | | | ✓ | |
| FEDFOREST [@dong2022fedforest] | ✓ | ✓ | ✓ | | | | |
| XFedHunter [@thi2023xfedhunter] | ✓ | ✓ | ✓ | | | | |
| Oki et al. [@oki2024] | ✓ | ✓ | ✓ | ✓ | | | |
| Bilal et al. [@bilal2025] | ✓ | ✓ | ✓ | | | | |
| XAI FL-IDS [@gholamrezazadeh2026] | ✓ | ✓ | ✓ | | | | |
| Watson et al. [@watson2022] | | | ✓ | ✓ | ✓ | | |
| PentestGPT [@deng2024pentestgpt] | | | | | | | ✓ |
| This project | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

@tab:related places the project among the closest works. The final row combines properties that the other rows show separately. We state that as a description of scope; it is not a claim that the combination is new.

## Organization of the Report {#sec:organization}

The remaining chapters of the report are organized as follows.

- Chapter 2 describes the proposed system, the working methodology of each stage, the standards the project uses, the software and hardware details, and how the system was tested.
- Chapter 3 gives the cost analysis and a summary of the measured compute.
- Chapter 4 presents the results: detection accuracy, the explanation check, the trust check, efficiency, negative and null results, limitations, and the challenges we met along the way.
- Chapter 5 concludes the report, outlines future work and records each member's contribution.
- Chapter 6 is the appendix. It holds the full detail behind every chapter, in sections 6.A onward, including key code excerpts, reference tables, the development timeline and the reproduction instructions.
- Chapter 7 lists the references.
<!-- numcheck: ignore -->
