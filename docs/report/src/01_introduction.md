# Introduction

A network intrusion detection system (IDS) watches traffic and raises an alert when a flow looks like an attack. Modern detectors are trained on labelled flow records, and their quality depends heavily on how varied those records are. A university, a hospital and a bank each see a different slice of the attack landscape. A detector trained by any one of them alone will miss attack types that only the others have seen. The obvious fix, pooling every organization's flow records in one place, is usually not allowed. Flow records name internal hosts, users and services, and contracts, privacy rules and plain caution keep them inside the organization that collected them.

Federated learning (FL) offers a way to train a shared model without moving the data [@mcmahan2017]. Each participant, called a client or silo, trains a copy of the model on its own data, and only the resulting weights go to a coordinating server, which averages them into a new global model. Several groups have applied this idea to intrusion detection and report accuracy close to that of a centrally trained detector [@nguyen2019diot; @rahman2020; @mothukuri2022; @campos2022; @agrawal2022].

When we started the project, we noticed that most of this work stops at accuracy. For a system that people would actually run, two further questions matter just as much, and they are the reason this project exists.

The first question concerns explanations. When an analyst receives an alert, the label alone is not enough: the analyst wants to know which features of the flow made the model call it an attack. In a federation, every silo holds its own copy of the model, trained on its own skewed share of the traffic. If those copies rely on different features, the explanation an analyst sees depends on whose model was asked, and the explanation stops being a property of "the detector" at all. We wanted to measure how far the silos' explanations agree, how that agreement changes as the silos' data grows more different, and how much disagreement random seeds alone produce.

The second question concerns the participants. The server sees only weight updates, never data. A silo that quietly relabels its own training data can bend the shared model, and nothing in plain averaging would notice [@tolpegin2020; @nguyen2020poison]. Byzantine-robust aggregation rules were designed for this threat [@blanchard2017; @yin2018], but they look for updates that are geometric outliers. In a federation where honest silos hold very different data, an honest but unusual silo can look like an outlier too. We wanted to test what these rules actually exclude in such a setting, and whether a language-model agent that reads simple per-silo statistics can do better while also writing down its reasons.

To study both questions in one place, we built XFed-IDS-ByzAgent. It is one system with five stages: data, federated training, an explanation check, a trust check and a dashboard. The explanation check and the trust check run on the same federated training, but they are different experiments with different evidence, and this report keeps their findings apart throughout.

## Objectives {#sec:objectives}

The project set out to do the following.

- Prepare the corrected Distrinet release of CICIDS2017 as eight attack families plus a Benign class, with a documented cleaning record, a group-aware train/test split and a fixed validation set.
- Train a shared detector across 10 simulated organizations with FedAvg under realistic label skew, using Dirichlet partitions at three skew levels and three seeds, and select every model and every round on validation data only.
- Measure how closely each organization's SHAP explanation ranking matches the global model's ranking, using Jaccard@k and weighted Kendall's τ, and read each value against a chance level and a seed-noise floor built from centralized models.
- Separate the effect of label skew on explanation agreement from the effect of silo size, which the Dirichlet partitioner ties together.
- Build a trust check in which a worst-case label-flipping attack is run against the federation, and compare an LLM trust agent (ByzAgent) with Krum, Multi-Krum and coordinate-wise trimmed mean.
- Audit the agent: how stable its decisions are, and how often the reasons it writes down match the numbers it was given.
- Run one preregistered comparison of federated optimizers, scored on the test set exactly once.
- Measure serving latency, communication per round and the effect of update compression.
- Deliver a working dashboard that shows live detection, explanations and trust decisions together, with every displayed number linked to the file it came from.
- Record every way the test set was read, and every negative or null result, so that nothing in the report claims more than the evidence supports.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Background and Literature Survey {#sec:literature}

This section reviews the six bodies of work that the project draws on. It closes by stating how this project differs from them. Every work cited here is in the project's verified bibliography.

### Federated learning and federated intrusion detection

McMahan et al. introduced federated averaging (FedAvg), in which clients run several local steps of gradient descent and the server averages the resulting weights, weighted by each client's number of examples [@mcmahan2017]. FedAvg remains the default aggregation rule, and most federated IDS studies keep it.

Early applications in network security focused on the Internet of Things. DÏoT trained anomaly models for individual device types across home gateways and flagged compromised devices without collecting their traffic centrally [@nguyen2019diot]. Rahman et al. proposed a federated scheme for IoT intrusion detection that keeps training and inference on the devices, and set it against centralized and purely on-device learning [@rahman2020]. Mothukuri et al. used recurrent models trained federatedly to detect IoT attacks [@mothukuri2022], and Popoola et al. applied federated deep learning to zero-day botnet detection [@popoola2022]. Two reviews collect the open problems that still sit between federated detection and deployment, among them heterogeneous data, communication cost and poisoning [@campos2022; @agrawal2022].

Heterogeneous data, usually called non-IID data, is the central difficulty. When clients hold different label mixes, their local models pull in different directions and the averaged model can be worse than any client expects. Benchmarks create controlled non-IID splits by drawing each client's share of every class from a Dirichlet distribution whose concentration parameter sets the degree of skew [@hsu2019; @li2022noniid]. Several server-side and client-side remedies exist. FedProx adds a proximal term to each client's objective that keeps local weights close to the global model [@li2020fedprox]. Server momentum (FedAvgM) treats the averaged update as a gradient and applies momentum to it on the server [@hsu2019]. Adaptive server optimizers such as FedAdam and FedYogi apply Adam-style or Yogi-style updates on the server [@reddi2021]. We used the Flower framework to run all federated training [@beutel2020flower].

What these studies share is their yardstick: detection accuracy. None of them asks whether the silo models detect the same attack for the same reason.

### Explainable intrusion detection and federated explanations

SHAP attributes a model's output to its input features using Shapley values from cooperative game theory, and it has become the common way to explain individual IDS decisions [@lundberg2017; @wang2020xai]. Its gradient-based variant integrates gradients against a background sample and suits neural networks [@erion2021]. Neupane et al. surveyed explainable IDS and its open challenges, starting from the problem that deep-learning detectors give the analysts who rely on them no justification for their alerts [@neupane2022]. Warnecke et al. proposed criteria for judging explanation methods in security tasks, with robustness among them [@warnecke2020]. Arisdakessian et al. argued for combining explainability with federated learning in IoT intrusion detection [@arisdakessian2023].

Several systems now add explanations to a federated detector. FEDFOREST builds an interpretable federated detector on gradient-boosted trees [@dong2022fedforest]. XFedHunter explains the detection of advanced persistent threats in software-defined networks [@thi2023xfedhunter]. Bilal et al. combine FedAvg with SHAP and LIME for malicious IoT traffic [@bilal2025], and Gholamrezazadeh and Montazerolghaem present a federated SHAP-based framework for distributed IDS [@gholamrezazadeh2026]. These systems produce explanations, but none of them compares the explanations of different participants with each other.

Oki et al. come closest to our question [@oki2024]. They measured the distance between the per-class feature sets of a distributed IDS and a non-distributed one and reported that federated learning brings these explanations closer. The 2026 federated XAI survey of Gholizade et al. lists the behaviour of explanations on non-IID clients among the field's unsolved problems and notes that there is still no standard way to score how consistent federated explanations are [@gholizade2026].
<!-- src: paper/refs.bib -->

### Stability and consistency of explanations

Outside federated learning, explanation stability has been studied directly. Attributions can change under small perturbations of the input that do not change the prediction [@ghorbani2019; @alvarezmelis2018], and sampling-based explainers carry their own estimation noise, for which credible intervals can be computed [@slack2021]. Watson et al. retrained models of identical architecture with different random seeds and data orderings and found low agreement among their explanations [@watson2022]. Their result means that two models can disagree about reasons even when nothing about their data differs. Krishna et al. formalised disagreement between explanation methods and showed that practitioners meet it often [@krishna2024].

Two tools from this literature are used in our measurement. Kendall's rank correlation counts concordant and discordant pairs between two rankings [@kendall1938], and its weighted form gives more weight to disagreements near the top of the ranking, where an analyst actually looks [@vigna2015]. Deletion and insertion curves check faithfulness: they remove or add the highest-ranked inputs in order and track how the model's score changes [@petsiuk2018].

The gap we saw is that federated studies report agreement numbers without the seed-noise reference that Watson et al.'s result implies they need. A federated agreement value means little until one knows how much agreement identical, centrally trained models reach.

### Byzantine-robust aggregation and poisoning

Krum chooses the single update whose summed distance to its nearest neighbours is smallest, and Multi-Krum keeps several such updates and averages them [@blanchard2017]. Coordinate-wise trimmed mean sorts each parameter across clients and discards a fixed fraction of the largest and smallest values before averaging [@yin2018]. Bulyan combines the two ideas [@mhamdi2018]. Later defences take other routes: FLTrust scores each update against one computed on a small root dataset held by the server [@cao2021fltrust]; FoolsGold looks at the diversity of client updates over time to catch coordinated sybils [@fung2020]; and centered clipping with worker momentum carries information across rounds [@karimireddy2021].

On the attack side, Fang et al. showed that crafted local updates can bypass distance-based rules [@fang2020local]. Tolpegin et al. studied label flipping, the attack used in this project, in federated settings [@tolpegin2020], and Nguyen et al. demonstrated poisoning and backdoor attacks against federated IoT intrusion detectors in particular [@nguyen2020poison].

Most of these evaluations assume that honest clients look alike. Under strong label skew they do not, and how that affects what the rules exclude is rarely measured.

### Language-model agents for security decisions

Agents that interleave written reasoning with actions [@yao2023react] have been applied to penetration testing [@deng2024pentestgpt] and to exploiting known vulnerabilities [@fang2024oneday], and a recent survey maps many other uses of large language models in security [@xu2026llmsec]. Llama 3 is one family of openly available models that can be run locally for such work [@grattafiori2024llama3]. A known weakness matters for us: the reasons a model writes down need not reflect what actually drove its answer [@turpin2023]. If an agent is placed inside an aggregation loop, its rationale has to be checked against the data it was given rather than taken at face value.

### CICIDS2017 and its corrections

CICIDS2017 is one of the most widely used IDS benchmarks [@sharafaldin2018]. Engelen et al. found errors in how its flows were built, how features were extracted and how flows were labelled, and released corrected data with an extra label for attack attempts that carry no payload [@engelen2021]. Liu et al. traced further problems through the dataset's lifecycle and released the refined Distrinet version that we use [@liu2022]. Lanvin et al. corrected a separate set of issues in a different branch, which we did not use [@lanvin2023]. Arp et al. list data snooping, such as tuning on the test set, among the common pitfalls of machine learning in security [@arp2022]. That warning is the reason this project keeps a written audit of every way its test set was read.

### How this project differs from prior work

The explanation check builds directly on Oki et al. [@oki2024]. They found that federated learning brings per-site explanations closer together; we vary label skew from severe to near-IID and look for the point where that effect gives out. We do not dispute their finding. We characterise where it stops holding.

We also measure a reference that the federated IDS papers above leave out: how much feature rankings differ between centralized models whose only difference is the random seed. This seed-noise floor is the bar a federated difference has to clear before it can be blamed on federation, and it is one concrete answer to the missing consistency metric that Gholizade et al. point to [@gholizade2026].

For the trust check, we test Krum and its variants on a federation of 10 silos with the true number of attackers handed to them as an oracle. We also audit how often the agent's own written reasons are accurate when checked against the statistics it saw.
<!-- src: PROJECT_INSTRUCTIONS.md -->

Two limits on our claims follow from this survey. We do not claim to be the first to measure explanation agreement in a federated IDS, and we do not present the combination of federated learning, intrusion detection and explainability as new, since recent work already combines them [@dong2022fedforest; @thi2023xfedhunter; @bilal2025; @gholamrezazadeh2026]. The one-sentence LLM summaries shown next to alerts in the dashboard are a usability feature, and we make no research claim about them.

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

@tab:related places the project among the closest works. The final row combines properties that the other rows show separately. We state that as a description of scope, not as a claim of novelty.

## Organization of the Report {#sec:organization}

The remaining chapters of the report are organized as follows.

- Chapter 2 describes the proposed system, the working methodology of each stage, the standards the project uses, the software and hardware details, and how the system was tested.
- Chapter 3 gives the cost analysis and a summary of the measured compute.
- Chapter 4 presents the results: detection accuracy, the explanation check, the trust check, efficiency, negative and null results, limitations, and the challenges we met along the way.
- Chapter 5 concludes the report, outlines future work and records each member's contribution.
- Chapter 6 is the appendix. It holds the full detail behind every chapter, in sections 6.A onward, including key code excerpts, reference tables, the development timeline and the reproduction instructions.
- Chapter 7 lists the references.
<!-- numcheck: ignore -->
