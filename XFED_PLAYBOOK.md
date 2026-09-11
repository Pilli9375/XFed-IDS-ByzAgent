# XFed-IDS-ByzAgent — Playbook

Operating manual. Read alongside `PROJECT_INSTRUCTIONS.md`.

---

## 1. Chat structure

| Chat | Purpose | Status |
|---|---|---|
| **01_Planning** | Decisions, scope, novelty framing, routing. **Never code.** | Active — the hub |
| **06_Parity** | Round-wise agreement, parity monitoring, size-controlled partitions, FedProx sweep | Open next |
| **07_App** | FastAPI + React port, traffic simulator, alert stream, hot-swap, LLM layer | Open when A is moving |
| **08_ByzAgent** | Poisoning sim, agent, baselines, eval, dashboard panel | Open with Phase 0 |
| **09_Paper** | Drafting. Dormant until results are in (~mid-October) | Dormant |
| **Viva** | Opens two weeks before each review | Dormant |

Chats 02–05 are archived. Don't reopen them — pull artifacts off disk instead.

**Why ByzAgent gets its own chat:** different contribution, different lineage, different framing. Mixing it into parity work is how the two blur in your head, then in your slides, then in the viva.

**Split rule:** split a chat only on your signal (~150 messages), never proactively.

---

## 2. The four-step workflow

**1 — Decide in 01_Planning.**
Anything touching scope, a locked decision, a novelty claim, or "should we add X." Claude Code implements whatever you ask without asking whether it's a good idea. That pushback is what's kept this project correct.

**2 — Verify schemas empirically.**
Before any code is written against a file, confirm actual columns and shapes yourself. Agentic tools generate confidently against column names that don't exist.

**3 — Build in Claude Code.**
One task at a time. "Write the round-wise agreement script that reads X and writes Y" — not "build the parity monitoring system." Small tasks, verified output, next one.

**4 — Report back to 01_Planning.**
What shipped, what the numbers say. That's where claims get softened and confounds get caught — the way the row-vs-silo bootstrap and the size confound were caught.

**The one rule:** Claude Code does not make research decisions.

---

## 3. Build order

```
1. Round-wise agreement          ← start here, data already on disk
2. Protocol write-up             ← answers the guide's novelty question
3. ByzAgent Phase 0 + Phase 4    ← the only real finding in that track
4. Parity monitoring             ← the 8/10 item
5. React port (FastAPI + Recharts)
6. ByzAgent Phases 2, 3, 5, 6
7. Hot-swap retraining
8. Size-controlled partitions
9. Full FedProx sweep
10. LLM explanation layer        ← bolts onto ByzAgent infra, near-free
```

Front-loaded so that at any stopping point there is completed work behind you. Compute-bound items (FedProx sweep, size-controlled partitions, ByzAgent eval runs) sit late because no tool makes them faster.

---

## 4. Item specs

**1. Round-wise agreement**
Compute agreement at rounds 5, 10, 15, 20 instead of only at R*. Per-round global and per-silo checkpoints already exist for all 9 configs. Question: does explanation consistency converge at the same rate as accuracy, or lag it? If accuracy plateaus at round 8 while agreement is still climbing at round 20, that's a new observation and a strong figure.

**2. Protocol write-up**
Formalise the measurement protocol as something others can reuse: fixed stratified eval set, ground-truth reference class, chance-level baseline, centralized-seed null control, Jaccard@k + weighted τ, faithfulness gate. The June 2026 survey says these metrics aren't standardised. Papers that propose a metric get cited more than papers that report a number.

**3. ByzAgent Phase 0 + Phase 4**
Phase 0: `PoisonedClient` wrapper, label-flip attack, two modes (`sudden`, `gradual`). Verify global accuracy visibly drops before proceeding.
Phase 4: feed the agent trend-across-N-rounds instead of current-round-only. **This is the only real finding** — Krum is provably good at sudden attacks, so Core alone likely shows no advantage. Gradual poisoning is where fixed thresholds miss and rolling history catches.

**4. Parity monitoring**
Server computes pairwise agreement across silo top-k rankings each round → one fleet parity score. Flag silos drifting beyond threshold. Privacy-consistent by construction: locked decision 4 already sends exactly this and nothing more. Novel because every FL monitoring paper watches weights, gradients, or accuracy — none watch explanations.

**5. React port**
FastAPI serving the model; React + Recharts porting the 6 existing sections. Reuse `theme.py` tokens — design decisions are made, this is translation not redesign.

**6–7. ByzAgent remaining + hot-swap**
Baselines (Krum, trimmed-mean), agent core with structured JSON output, eval harness, dashboard panel. Hot-swap: log seed and round every time so the retrained model stays auditable.

**8. Size-controlled partitions**
Every silo gets identical sample counts, labels stay α-skewed. Resolves the r=0.46 confound. If divergence persists at equal sizes, label heterogeneity is isolated as the cause — a causal claim nobody has made, because vanilla Dirichlet tangles size and skew.

**9. FedProx sweep**
Full 9-config × 3-seed. Compute agreement on it too — free. Does drift control improve *explanation* parity, or only accuracy? Either answer is a result.

**10. LLM layer**
SHAP output → analyst-readable sentence. Uses the LangChain setup ByzAgent already needs. Usability framing in every slide.

---

## 5. What was rejected, and why

Keep this list. The same proposals return in new clothing.

| Rejected | Reason |
|---|---|
| Poisoning as a standalone contribution | Occupied — AGAT-FL (Nov 2025), WeiDetect, FLDetector, FedDefense. Survives only as ByzAgent Phase 0. |
| Causal AI replacing SHAP | Causal-FL-ID (Springer, Feb 2026) already does it; would discard four months of validated SHAP work; causal discovery on 82 correlated features is a PhD chapter. |
| RAG / multimodal / agents-as-novelty | No defensible connection to the finding. Adds attack surface, not science. |
| "First to measure" framing | False. Oki et al. 2024 measured it. |
| Accuracy improvements | 99.46% already. The last half-percent is noise; nobody wins there. |

---

## 6. Talking points

**To the guide, on novelty:**
> "A June 2026 systematic survey of federated XAI (Gholizade et al., arXiv 2607.13045) identifies explanation consistency under non-IID data as an open challenge and notes no standardised metrics exist. The closest prior work (Oki et al., IEEE Networking Letters 2024) reports that federated feature importance converges toward centralized importance. We test that across a systematic heterogeneity sweep and find it holds at moderate heterogeneity but breaks down at severe heterogeneity — quantified against a null control that no prior work reports."

**On why not more technology:**
> "I considered adding causal reasoning, found Causal-FL-ID from February 2026, determined it would replace rather than extend my contribution, and chose to deepen the existing result instead."

**On ByzAgent, if asked and it isn't your part:**
> "That's the trust-decision layer — the agent reasons over per-client update statistics rather than applying a fixed threshold. My component is the explanation-parity measurement."

Never say "I didn't work on that."

---

## 7. Come back to 01_Planning when

- A locked decision comes under pressure
- ByzAgent Phase 4 fails against the baselines
- Federated explanation beats centralized (leakage check)
- Agreement stops being computable at any α
- Anyone proposes something from the rejected list
- A result looks unexpectedly strong
- A stage completes and needs routing

---

## 8. Standing reminders

- Test set: touched once. Already spent.
- Every number in a slide has a CSV and a script behind it.
- Softened claims stay softened. The below-floor result is directional.
- Bot/WebAttack caveat: tested and **not** confirmed — don't restate it as assumed truth.
- Contribution A and Contribution B stay visibly separate everywhere.
- 6GB VRAM is a hard ceiling.
