# Appendix

This chapter shows short excerpts of the code behind the main steps of the system, each with its repository path; long comments and logging lines are shortened and marked with "...". The full experimental record, with every table, figure, audit and negative result, is kept in the repository and in the full version of this report.

The complete source code, configuration and results are available at https://github.com/Pilli9375/XFed-IDS-ByzAgent
<!-- numcheck: ignore -->

## The client training step

@fig:code-train shows one silo's local training. The same function implements FedAvg and FedProx: when μ is zero, the proximal term vanishes.

Code: Client training step: local epochs with an optional FedProx term {#fig:code-train} [federated/xfed_federated/task.py]
```python
def local_train_epochs(model, splits, epochs, model_cfg, mu=0.0):
    X = torch.from_numpy(splits.X_train.copy()).to(DEVICE)
    y = torch.from_numpy(splits.y_train.copy()).to(DEVICE)
    weights = torch.from_numpy(splits.class_weights.copy()).to(DEVICE)
    global_params = ([p.detach().clone() for p in model.parameters()]
                     if mu > 0 else None)
    tr = model_cfg["training"]
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(tr["lr"]),
                                  weight_decay=float(tr["weight_decay"]))
    batch_size, n = int(tr["batch_size"]), len(y)
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n, device=DEVICE)
        total = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(X[idx]), y[idx])
            if mu > 0:
                prox = sum(((p - gp) ** 2).sum()
                           for p, gp in zip(model.parameters(), global_params))
                loss = loss + (mu / 2.0) * prox
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        epoch_loss = total / n
    return epoch_loss
```

## The SHAP explanation and the top-k export

@fig:code-shap computes one model's SHAP values and its additivity residual. @fig:code-topk turns a silo's per-row rankings into the single ordered top-k list that it sends to the server; only these feature indices cross the boundary.

Code: Explaining one model with GradientExplainer and measuring the additivity residual {#fig:code-shap} [tools/local_shap_pipeline.py]
```python
def explain_one_model(model, background_X, eval_X_scaled):
    background_t = torch.from_numpy(background_X.copy())
    eval_t = torch.from_numpy(eval_X_scaled.copy())
    explainer = shap.GradientExplainer(model, background_t)
    shap_values = explainer.shap_values(eval_t, nsamples=NSAMPLES)
    sv = np.array(shap_values)
    with torch.no_grad():
        f_eval = model(eval_t).numpy()
        f_bg_mean = model(background_t).numpy().mean(axis=0)
    diff = sv.sum(axis=1) - (f_eval - f_bg_mean[None, :])
    max_additivity_diff = float(np.abs(diff).max())
    return sv, max_additivity_diff, ...
```

Code: A silo's top-k export: per-row top-k sets combined by vote into one ordered list {#fig:code-topk} [tools/parity_monitor.py]
```python
def aggregate_topk_for_silo(shap_values, eval_y, eligible_mask, k):
    votes, rank_sum = Counter(), defaultdict(float)
    for idx in range(len(eval_y)):
        if not eligible_mask[idx]:
            continue
        true_class = int(eval_y[idx])
        vec = shap_values[idx, :, true_class]
        order = np.argsort(-np.abs(vec))[:k]
        for rank_pos, feat in enumerate(order):
            votes[int(feat)] += 1
            rank_sum[int(feat)] += rank_pos
    if not votes:
        return None
    def sort_key(feat):
        return (-votes[feat], rank_sum[feat] / votes[feat], feat)
    return sorted(votes.keys(), key=sort_key)[:k]
```

## The agreement metrics

@fig:code-agree shows the two agreement measures and the chance level. Weighted τ comes from SciPy, applied to the attribution vectors of the row's true class.

Code: Jaccard@k, the chance level and weighted Kendall's τ {#fig:code-agree} [tools/agreement_metrics.py]
```python
def jaccard_topk(a, b, k):
    """a, b: per-feature attribution vectors (signed). Top-k by |value|."""
    top_a = set(np.argsort(-np.abs(a))[:k])
    top_b = set(np.argsort(-np.abs(b))[:k])
    union = top_a | top_b
    return len(top_a & top_b) / len(union) if union else float("nan")

def chance_jaccard(k, n=N_FEATURES):
    """Expected Jaccard between two random k-subsets of n items."""
    exp_intersect = k * k / n
    return exp_intersect / (2 * k - exp_intersect)

# per evaluation row, true-class attribution vectors:
g_vec = global_sv[sample_idx, :, true_class]
s_vec = silo_sv[sample_idx, :, true_class]
tau_w, _ = weightedtau(g_vec, s_vec)          # scipy.stats.weightedtau
```

## ByzAgent: prompt summary and JSON schema

@fig:code-schema shows the JSON schema that Ollama enforces on every reply, and @fig:code-prompt the closing lines of the prompt. The opening part of the prompt, not repeated here, defines the five statistics, cautions that under this attack a malicious client tends to score higher on the mostly Benign validation set, and points out that ordinary differences between clients' data can also shift the statistics.

Code: ByzAgent's response schema {#fig:code-schema} [src/agents/byz_agent.py]
```python
DECISIONS = ("trust", "downweight", "quarantine")
DEFAULT_DOWNWEIGHT_MULTIPLIER = 0.3

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "round": {"type": "integer"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "decision": {"type": "string", "enum": list(DECISIONS)},
                    "explanation": {"type": "string"},
                },
                "required": ["client_id", "decision", "explanation"],
            },
        },
    },
    "required": ["round", "decisions"],
}
```

Code: Closing lines of ByzAgent's prompt template {#fig:code-prompt} [src/agents/byz_agent.py]
```text
For each client listed below, decide one of: trust, downweight, or
quarantine. Respond ONLY with a JSON object matching this schema, one
decision entry per client_id listed. In each explanation, cite the
specific numeric value(s) that informed this decision:
{"round": <int>, "decisions": [{"client_id": <string>, "decision":
"trust"|"downweight"|"quarantine", "explanation": <string>}]}

Round: {round_num}
Clients this round:
{client_block}
```

## The hot-swap gate

@fig:code-gate shows the non-regression gate. Every candidate round is scored on validation; the earliest round that reaches the incumbent's score is accepted, and if none does, the served model is left unchanged and nothing is logged.

Code: The hot-swap non-regression gate {#fig:code-gate} [src/hotswap/retrain.py]
```python
for r in range(1, num_rounds + 1):
    ...                                   # local training in every silo
    current_state = fedavg_aggregate(local_states, ns)
    candidate_metric = float(eval_global(current_state)[metric_key])
    round_candidates.append((r, current_state, candidate_metric))

# Strict non-regression gate, no tolerance: best candidate must be >=
# incumbent. Ties broken toward the EARLIEST round.
passing = [c for c in round_candidates if c[2] >= incumbent_metric]
if not passing:
    best_seen = max(m for _, _, m in round_candidates)
    raise HotSwapGateRejected(
        f"no candidate round cleared the gate: best {metric_name}="
        f"{best_seen:.4f} < incumbent {incumbent_metric:.4f} ... "
        f"Served model unchanged; nothing logged.")
best_round, best_state, best_metric = min(passing, key=lambda c: c[0])
```
