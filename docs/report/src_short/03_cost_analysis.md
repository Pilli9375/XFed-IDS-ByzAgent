# Cost Analysis

This chapter reports what the project cost. In short, the team bought nothing: no hardware, no cloud time and no paid API credits. Everything ran on a laptop the team already owned, using free and open-source software, a public dataset and a freely downloadable language model run locally. Because nothing was purchased, this chapter lists no prices. It records instead what was used and how much compute the work took, using only measured numbers.

## Hardware Already Owned {#sec:cost-hardware}

@tab:cost-hardware lists the only hardware used. It was owned by the team before the project began, and no part of it was bought for the project.

Table: Hardware used (already owned; no purchase) {#tab:cost-hardware}
| Item | Specification | Used for |
|---|---|---|
| Laptop GPU | NVIDIA RTX 4050, 6 GB memory | Centralized MLP, XGBoost, local LLM (Ollama) |
| Laptop CPU | AMD Ryzen 7 7435HS | Federated training, SHAP, serving, hot-swap retraining |
| Memory | 24 GB RAM | All stages |
| Operating system | Windows 11 | All stages |
<!-- src: PROJECT_INSTRUCTIONS.md; docs/efficiency_results.md -->

## Software, Data and Services {#sec:cost-software}

Every software component was free to use. @tab:cost-software groups them; versions are in @tab:tools.

Table: Software, data and model used at no cost {#tab:cost-software}
| Category | What was used |
|---|---|
| Language and environment | Python, the conda environment manager, Node.js for the front end |
| Machine learning | PyTorch, scikit-learn, XGBoost, SHAP, NumPy, pandas, SciPy |
| Federated learning | Flower |
| Serving and dashboard | FastAPI, Uvicorn, ONNX and ONNX Runtime, React, Vite, Streamlit |
| Language model | Ollama running Llama 3.1 8B instruct (4-bit), downloaded and run locally |
| Dataset | CICIDS2017, Distrinet corrected release (public) |
| Version control and hosting | Git and a public GitHub repository |
<!-- src: docs/contribution_b_results.md -->

Running the language model locally rather than through a paid API was a deliberate choice: it kept the trust agent within the 6 GB GPU budget, kept every statistic on the laptop, and cost nothing per call.
<!-- src: PROJECT_INSTRUCTIONS.md -->

## Measured Compute {#sec:cost-compute}

Since money was not spent, the real cost of the project is compute time and communication. @tab:cost-compute collects the measured figures. Every value comes from a results file or a results document, and no value is estimated.

Table: Measured compute and communication (one laptop) {#tab:cost-compute}
| Quantity | Measured value |
|---|---|
| Model size | 19,849 parameters; 79,396 bytes as fp32 tensors |
| Traffic per federated round, 10 silos, both directions | 1,587,920 bytes (793,960 each way) |
| Traffic per round as serialized Flower records | 1,623,600 bytes |
| Wall time per round, median over 500 rounds (25 runs) | 51.4 s |
| Wall time per round, range | 26.8 to 98.7 s |
| Wall time of round 1, median (includes start-up) | 84.2 s |
| Wall time per run, full FedAvg regression run | 12.7 min (34.7 s per round) |
| Per-flow latency p50, ONNX Runtime fp32 / PyTorch | 45.7 µs / 186.5 µs |
| Throughput at batch 1024, ONNX Runtime fp32 / PyTorch | 1,071,700 / 1,482,368 rows per second |
| ByzAgent call time, median per call (logged, no pre-screen) | 41.1 to 47.6 s |
| Parity monitor full sweep (9 configurations × 4 rounds) | 392.0 min |
| Preregistered study, elapsed when the budget guard triggered | 7.40 h |
<!-- src: docs/efficiency_results.md; docs/preregistration_accuracy.md; docs/contribution_a_results.md -->

Three things stand out. First, a federated round costs well under a minute on this laptop, so a full 20-round run takes minutes, and the experiments were limited by the number of runs rather than by any single run. Second, the communication per round is small, because the model itself is small. Third, the most expensive single operations were the LLM calls, which took tens of seconds each, and the multi-draw SHAP sweeps, which took hours. These two costs explain several scoping decisions recorded elsewhere in this report, such as cutting the preregistered candidate grid on wall-time grounds and keeping the trust-check baselines at one run each.
<!-- src: docs/efficiency_results.md -->
