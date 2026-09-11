"""LLM-based per-round Byzantine-robust trust agent. ByzAgent Contribution B,
Phase 3 (current-round path) + Phase 4 (rolling-history path).

ONE Ollama call per round, batched across every client in that round (never
one call per client). Two input modes, selected by configs/agent.yaml's
agent.history.mode:

  "current_round"   -- Phase 3 baseline, UNCHANGED. Each client's 5 stats are
                        this round's scalar values only. decide_round() /
                        build_prompt() / PROMPT_TEMPLATE, all untouched by
                        Phase 4.
  "rolling_history"  -- Phase 4. Each client's 5 stats are a SEQUENCE of its
                        own most recent up-to-N per-round values (oldest to
                        newest, ending with the current round), not a single
                        scalar. decide_round_history() / build_prompt_history()
                        / PROMPT_TEMPLATE_HISTORY. The ONLY intended
                        difference from the current-round prompt is
                        scalar->sequence presentation -- same stat
                        definitions, same val_accuracy caveat verbatim, same
                        citation instruction, same JSON schema, same
                        trust/downweight/quarantine semantics and weights.
                        build_client_history() is the pure function that
                        slices client_stats.jsonl-shaped rows (already
                        written by src/monitoring/client_stats.py) into this
                        per-client window; it takes plain row dicts, not a
                        file path, so it works identically whether the rows
                        come from a live in-memory accumulation
                        (federated/xfed_federated/server_app.py) or a
                        retrospective read of client_stats.jsonl off disk.

Both modes are one Ollama call per round either way -- rolling-history mode
does not multiply calls by N, it only changes what each client's block in
that one prompt contains.

Local inference via Ollama, selected empirically (Phase 3 Step 1):
llama3.1:8b-instruct-q4_K_M -- 100% JSON-schema parse success, 100%
id-coverage, and by far the highest rate of explanations that cite the
specific numeric values given (91.6% with the citation instruction below,
vs 65.1% without it, vs <1% for qwen2.5:7b-instruct-q4_K_M and 0% for
phi3.5, both eliminated). VRAM footprint ~4.8GB resident, confirmed
empirically to unload to baseline within 3-8s of a keep_alive:0 call --
this module always passes keep_alive=0 (see AgentConfig), so nothing stays
resident in VRAM between rounds, by design, not by assumption.

PROMPT DESIGN -- locked per 01_Planning, each constraint traceable to a
specific ground-truth requirement:

INCLUDED (mandatory):
  - a one-sentence definition of each of the 5 Phase 1 stats
    (src/monitoring/client_stats.py).
  - the val_accuracy Benign-skew caveat, worded exactly as specified
    (results/monitoring/PHASE1_SUMMARY.md, "VAL_ACCURACY INVERSION"
    section) -- this corrects a CONFIRMED measurement bias (this attack
    flips attack-family labels to Benign, and the centralized validation
    set is ~75% Benign, so a malicious client's raw accuracy on it tends
    to look artificially healthy). It is corrective context about a
    measured bias, not a hint about which stat is predictive.
  - a brief, generic (non-specific) description of what Byzantine /
    label-flipping client behavior can look like.

EXCLUDED (mandatory -- the whole point of Phase 3/4 is testing whether an
LLM reasoning over raw behavioral stats can find the signal itself; any of
the below would quietly invalidate that test):
  - no indication that train_loss is expected to be the strongest signal,
    or that the 3 geometry stats (update_norm / cosine_to_global /
    cosine_to_peer_mean) showed near-null separation in Phase 1/2.
  - no ground-truth malicious-silo identity, ever, in any form.
  - no oracle f (the true attack strength). Unlike Krum / trimmed-mean
    (Phase 2, which ARE given the true f), ByzAgent infers everything
    from behavior. This asymmetry is intentional and must be stated
    explicitly in every ByzAgent-vs-baseline comparison.

The final prompt sentence ("cite the specific numeric value(s)...") was
added and kept after an explicit empirical check (Phase 3 Step 1
prompt-iteration, 01_Planning go-ahead): it raised the grounded-explanation
rate from 65.1% to 91.6% on a 12-case held-out synthetic batch, with 100%
JSON parse / id-coverage either way. Not tuned further against synthetic
data past that one check -- the real gate is Step 3a/3b against actual
client_stats.jsonl.

CANONICAL SOURCE. federated/xfed_federated/ runs inside Flower's isolated
simulation runtime and cannot see this src/ tree, same reason
src/monitoring/client_stats.py and src/attacks/label_flip.py are vendored
there. This file is vendored too, at
federated/xfed_federated/_vendored/byz_agent.py -- edit HERE, then re-copy
before your next `flwr run`.

Place at: src/agents/byz_agent.py
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DECISIONS = ("trust", "downweight", "quarantine")

# trust -> normal (sample-count) weight; downweight -> AgentConfig's
# downweight_multiplier (default 0.3); quarantine -> excluded entirely
# (weight 0), never merely downweighted further. See decisions_to_weights().
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

PROMPT_TEMPLATE = """You are assisting a federated-learning server in deciding, each round, how much to trust each participating client ("silo") before its model update is included in this round's aggregation.

You are given, for each client, five behavioral statistics computed for the current round only:
- update_norm: the L2 (Euclidean) distance between the client's post-training model weights and the previous round's global model weights.
- cosine_to_global: the cosine similarity between the client's weight update and this round's actual aggregated update.
- cosine_to_peer_mean: the cosine similarity between the client's weight update and the unweighted mean of all clients' updates this round.
- train_loss: the client's own final local-epoch training loss.
- val_accuracy: the client's post-training model accuracy, evaluated by the server against a centralized validation set (not the client's own local data).

Important caveat: this specific attack biases val_accuracy upward for malicious clients on this Benign-heavy validation set -- do not read high val_accuracy alone as evidence of trustworthiness.

Byzantine or label-flipping clients may train on data with corrupted or mislabeled examples, which can cause their local model updates to diverge from honest clients' behavior in various ways -- for example unusually high training loss, or weight updates that point in a different direction from the rest of the fleet. Not every deviation is necessarily an attack; natural non-IID data differences between clients can also cause some of these statistics to vary.

For each client listed below, decide one of: trust, downweight, or quarantine. Respond ONLY with a JSON object matching this schema, one decision entry per client_id listed. In each explanation, cite the specific numeric value(s) that informed this decision:
{{"round": <int>, "decisions": [{{"client_id": <string>, "decision": "trust"|"downweight"|"quarantine", "explanation": <string>}}]}}

Round: {round_num}
Clients this round:
{client_block}
"""

# Phase 4. Identical to PROMPT_TEMPLATE except: (1) the intro sentence is
# rewritten to say each stat is a sequence, not a scalar -- the original
# sentence ("computed for the current round only") would otherwise describe
# the client block inaccurately; (2) {client_block} is built by
# _client_block_history instead of _client_block. The 5 stat definitions,
# the val_accuracy caveat, the Byzantine-behavior paragraph, the citation
# instruction, and the JSON schema line are byte-identical to PROMPT_TEMPLATE.
PROMPT_TEMPLATE_HISTORY = """You are assisting a federated-learning server in deciding, each round, how much to trust each participating client ("silo") before its model update is included in this round's aggregation.

You are given, for each client, five behavioral statistics, each shown as a sequence of that client's own most recent per-round values (oldest to newest, ending with the current round) rather than a single current-round number:
- update_norm: the L2 (Euclidean) distance between the client's post-training model weights and the previous round's global model weights.
- cosine_to_global: the cosine similarity between the client's weight update and this round's actual aggregated update.
- cosine_to_peer_mean: the cosine similarity between the client's weight update and the unweighted mean of all clients' updates this round.
- train_loss: the client's own final local-epoch training loss.
- val_accuracy: the client's post-training model accuracy, evaluated by the server against a centralized validation set (not the client's own local data).

Important caveat: this specific attack biases val_accuracy upward for malicious clients on this Benign-heavy validation set -- do not read high val_accuracy alone as evidence of trustworthiness.

Byzantine or label-flipping clients may train on data with corrupted or mislabeled examples, which can cause their local model updates to diverge from honest clients' behavior in various ways -- for example unusually high training loss, or weight updates that point in a different direction from the rest of the fleet. Not every deviation is necessarily an attack; natural non-IID data differences between clients can also cause some of these statistics to vary.

For each client listed below, decide one of: trust, downweight, or quarantine. Respond ONLY with a JSON object matching this schema, one decision entry per client_id listed. In each explanation, cite the specific numeric value(s) that informed this decision:
{{"round": <int>, "decisions": [{{"client_id": <string>, "decision": "trust"|"downweight"|"quarantine", "explanation": <string>}}]}}

Round: {round_num}
Clients this round:
{client_block}
"""


def _fmt_val(v: Any) -> str:
    if v is None:
        return "null (missing/not reported this round)"
    if isinstance(v, float) and v != v:  # NaN
        return "NaN"
    return str(v)


def _client_block(clients: list[dict[str, Any]]) -> str:
    lines = []
    for c in clients:
        lines.append(
            f"- client_id: {c['client_id']}, update_norm: {_fmt_val(c.get('update_norm'))}, "
            f"cosine_to_global: {_fmt_val(c.get('cosine_to_global'))}, "
            f"cosine_to_peer_mean: {_fmt_val(c.get('cosine_to_peer_mean'))}, "
            f"train_loss: {_fmt_val(c.get('train_loss'))}, "
            f"val_accuracy: {_fmt_val(c.get('val_accuracy'))}"
        )
    return "\n".join(lines)


def build_prompt(round_num: int, clients: list[dict[str, Any]]) -> str:
    """clients: list of dicts with client_id + the 5 current-round stats.
    Exposed standalone (not just inlined in decide_round) so Step 3a's
    manual check can print the exact prompt sent without duplicating this
    logic, and so a caller can log the prompt itself if desired.
    """
    return PROMPT_TEMPLATE.format(round_num=round_num, client_block=_client_block(clients))


# ---------------------------------------------------------------------------
# Phase 4 -- rolling-history window construction + prompt building
# ---------------------------------------------------------------------------

HISTORY_STAT_FIELDS = (
    "update_norm", "cosine_to_global", "cosine_to_peer_mean", "train_loss", "val_accuracy",
)


def build_client_history(
    all_rows: list[dict[str, Any]],
    current_round: int,
    window: int,
) -> list[dict[str, Any]]:
    """Slice client_stats.jsonl-shaped rows (each a dict with at least
    "round", "silo_id", and the 5 HISTORY_STAT_FIELDS keys -- the exact
    schema src/monitoring/client_stats.py's ClientStatsRecorder writes) down
    to, per silo, that silo's own most recent up-to-`window` rows with
    round <= current_round, oldest first.

    PARTIAL WINDOW, not pad or skip -- the explicit, reported choice for
    early rounds (round < window) or any round where a client's history has
    gaps (e.g. an earlier round's reply errored and was never recorded):
    a client gets however many of its own real rows it actually has, down
    to a minimum of 1 (this round's own row), never a fabricated/padded
    value standing in for a round that didn't happen, and never a
    dropped/skipped round for the agent to silently not decide on. Round 1
    therefore has a window of exactly 1 (byte-for-byte the same information
    the current-round-only path would show); the window reaches full size
    only once `window` rounds of real history exist for that client.
    window_size (how many real rows this specific client's entry actually
    holds this round) is returned per-client so the prompt can say "last k
    rounds" truthfully instead of a hardcoded N that early rounds don't have.

    Returns one dict per silo_id present in `current_round`'s rows (a silo
    with no row this round has nothing to attach history to and is excluded,
    matching the current-round-only path's own behavior for a missing
    reply): {"client_id": "silo_{id}", "window_size": k, <stat>: [v_oldest,
    ..., v_newest]} for each of the 5 HISTORY_STAT_FIELDS.

    Raises RuntimeError if a silo that has a current_round row is somehow
    not present with round==current_round after windowing -- this would
    only happen from a caller bug (e.g. passing rows that exclude the round
    just finalized), and silently returning a stale window would let the
    agent decide this round's trust using only past data, never told the
    round it's deciding on is missing from its own view.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")

    current_round_ids = sorted({int(r["silo_id"]) for r in all_rows if int(r["round"]) == current_round})
    by_silo: dict[int, list[dict[str, Any]]] = {}
    for r in all_rows:
        if int(r["round"]) > current_round:
            continue
        by_silo.setdefault(int(r["silo_id"]), []).append(r)

    out = []
    for silo_id in current_round_ids:
        rows = sorted(by_silo.get(silo_id, []), key=lambda r: int(r["round"]))
        windowed = rows[-window:]
        if not windowed or int(windowed[-1]["round"]) != current_round:
            raise RuntimeError(
                f"build_client_history: silo_id={silo_id} has no row for "
                f"current_round={current_round} after windowing -- caller "
                f"must pass all_rows including this round's just-finalized "
                f"stats before calling this function."
            )
        entry: dict[str, Any] = {"client_id": f"silo_{silo_id}", "window_size": len(windowed)}
        for stat in HISTORY_STAT_FIELDS:
            entry[stat] = [row.get(stat) for row in windowed]
        out.append(entry)
    return out


def _fmt_series(values: list[Any]) -> str:
    return ", ".join(_fmt_val(v) for v in values)


def _client_block_history(clients: list[dict[str, Any]]) -> str:
    lines = []
    for c in clients:
        k = c["window_size"]
        note = f"last {k} round" + ("s" if k != 1 else "") + ", oldest to newest"
        lines.append(
            f"- client_id: {c['client_id']}\n"
            f"    update_norm ({note}): {_fmt_series(c['update_norm'])}\n"
            f"    cosine_to_global ({note}): {_fmt_series(c['cosine_to_global'])}\n"
            f"    cosine_to_peer_mean ({note}): {_fmt_series(c['cosine_to_peer_mean'])}\n"
            f"    train_loss ({note}): {_fmt_series(c['train_loss'])}\n"
            f"    val_accuracy ({note}): {_fmt_series(c['val_accuracy'])}"
        )
    return "\n".join(lines)


def build_prompt_history(round_num: int, clients: list[dict[str, Any]]) -> str:
    """clients: build_client_history()'s output -- client_id + window_size +
    the 5 stats as oldest-to-newest lists. Mirrors build_prompt(); exposed
    standalone for the same reasons (manual single-round checks, caller-side
    logging of the exact prompt sent).
    """
    return PROMPT_TEMPLATE_HISTORY.format(round_num=round_num, client_block=_client_block_history(clients))


@dataclass
class AgentConfig:
    model: str = "llama3.1:8b-instruct-q4_K_M"
    host: str = "http://localhost:11434"
    # ALWAYS 0 by default -- nothing stays resident in VRAM between rounds
    # (empirically confirmed, see module docstring). Overridable only for
    # ad-hoc local testing (e.g. Step 1's batch reliability test kept a
    # model loaded across many calls); never override this for a live
    # server_app.py run without re-confirming the VRAM math against the
    # 6GB ceiling.
    keep_alive: int | str = 0
    temperature: float = 0.2
    timeout_seconds: int = 120
    max_retries: int = 1  # one retry on a malformed response before failing loudly
    downweight_multiplier: float = DEFAULT_DOWNWEIGHT_MULTIPLIER

    # Phase 4. "current_round" is the Phase 3 baseline (default, unchanged
    # behavior for any caller/config that predates Phase 4 or omits the new
    # `history` block entirely). "rolling_history" switches the prompt to
    # the sequence presentation (build_client_history / build_prompt_history
    # / decide_round_history) with a window of history_window rounds.
    history_mode: str = "current_round"
    history_window: int = 5

    @classmethod
    def from_yaml_dict(cls, agent_cfg: dict[str, Any]) -> "AgentConfig":
        history_cfg = agent_cfg.get("history") or {}
        history_mode = str(history_cfg.get("mode", cls.history_mode))
        if history_mode not in ("current_round", "rolling_history"):
            raise ValueError(
                f"configs/agent.yaml: agent.history.mode must be "
                f"'current_round' or 'rolling_history', got {history_mode!r}"
            )
        return cls(
            model=str(agent_cfg.get("model", cls.model)),
            host=str(agent_cfg.get("host", cls.host)),
            keep_alive=agent_cfg.get("keep_alive", cls.keep_alive),
            temperature=float(agent_cfg.get("temperature", cls.temperature)),
            timeout_seconds=int(agent_cfg.get("timeout_seconds", cls.timeout_seconds)),
            max_retries=int(agent_cfg.get("max_retries", cls.max_retries)),
            downweight_multiplier=float(
                agent_cfg.get("downweight_multiplier", cls.downweight_multiplier)
            ),
            history_mode=history_mode,
            history_window=int(history_cfg.get("window", cls.history_window)),
        )


class AgentResponseError(RuntimeError):
    """Raised when the model fails to produce a schema-valid, id-complete
    response after max_retries+1 attempts. Fail loudly -- same posture as
    ClientStatsRecorder's guards in src/monitoring/client_stats.py. A
    single malformed round is never silently defaulted to any particular
    decision; per 01_Planning, a malformed response could corrupt that
    round's aggregation, so the caller must see the failure, not have it
    papered over.
    """


def _call_ollama(prompt: str, cfg: AgentConfig) -> str:
    payload = {
        "model": cfg.model,
        "prompt": prompt,
        "stream": False,
        "format": RESPONSE_SCHEMA,
        "keep_alive": cfg.keep_alive,
        "options": {"temperature": cfg.temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{cfg.host}/api/generate", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("response", "")


def _parse_and_validate(
    raw_text: str, expected_ids: set[str]
) -> list[dict[str, Any]]:
    obj = json.loads(raw_text)  # raises json.JSONDecodeError on malformed JSON
    if not isinstance(obj, dict) or "decisions" not in obj or not isinstance(obj["decisions"], list):
        raise ValueError("response missing/invalid top-level 'decisions' array")

    decisions = obj["decisions"]
    returned_ids = set()
    for d in decisions:
        if not isinstance(d, dict):
            raise ValueError(f"decision entry is not an object: {d!r}")
        for key in ("client_id", "decision", "explanation"):
            if key not in d:
                raise ValueError(f"decision entry missing required key {key!r}: {d!r}")
        if d["decision"] not in DECISIONS:
            raise ValueError(f"decision {d['decision']!r} not one of {DECISIONS}")
        returned_ids.add(d["client_id"])

    if returned_ids != expected_ids:
        raise ValueError(
            f"id coverage mismatch: expected {sorted(expected_ids)}, "
            f"got {sorted(returned_ids)}"
        )
    return decisions


def _decide_round_core(
    round_num: int,
    expected_ids: set[str],
    prompt: str,
    cfg: AgentConfig,
) -> tuple[list[dict[str, Any]], str, str]:
    """Shared call+retry+validate loop behind both decide_round (Phase 3,
    current-round scalars) and decide_round_history (Phase 4, rolling
    sequences) -- the two differ only in how `prompt` and `expected_ids` were
    built, never in how a response is solicited, retried, or validated.
    Extracted so Phase 4 does not duplicate (and risk silently diverging
    from) Phase 3's already-verified retry/failure semantics.
    """
    last_error: Exception | None = None
    raw_text = ""
    for attempt in range(cfg.max_retries + 1):
        try:
            raw_text = _call_ollama(prompt, cfg)
            decisions = _parse_and_validate(raw_text, expected_ids)
            return decisions, prompt, raw_text
        except (json.JSONDecodeError, ValueError, urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            continue

    raise AgentResponseError(
        f"ByzAgent failed to produce a valid decision for round {round_num} "
        f"after {cfg.max_retries + 1} attempt(s): {last_error}. "
        f"Last raw response: {raw_text!r}"
    )


def decide_round(
    round_num: int,
    client_stats: list[dict[str, Any]],
    cfg: AgentConfig | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    """ONE LLM call, batched across every entry in client_stats -- never one
    call per client, per 01_Planning's explicit Phase 3 spec.

    client_stats: list of dicts, each with keys client_id, update_norm,
    cosine_to_global, cosine_to_peer_mean, train_loss, val_accuracy --
    CURRENT-ROUND values only. No rolling history is read or passed here.
    UNCHANGED by Phase 4 -- this is the current-round-only baseline
    selectable via configs/agent.yaml's agent.history.mode: current_round.

    Returns (decisions, prompt, raw_response):
      decisions   -- list of {"client_id", "decision", "explanation"}
                      dicts, one per client_stats entry, in no guaranteed
                      order relative to the input (key by client_id, not
                      position).
      prompt      -- the exact prompt sent on the attempt that succeeded
                      (needed verbatim for Step 3a's manual check).
      raw_response -- the exact raw text returned on that attempt.

    Raises AgentResponseError after cfg.max_retries+1 failed attempts.
    Deterministic decision variance (running this 3x on identical input to
    check stability) is a caller-level concern -- call this function
    multiple times, it does not retry-for-agreement internally.
    """
    cfg = cfg or AgentConfig()
    expected_ids = {str(c["client_id"]) for c in client_stats}
    prompt = build_prompt(round_num, client_stats)
    return _decide_round_core(round_num, expected_ids, prompt, cfg)


def decide_round_history(
    round_num: int,
    client_history: list[dict[str, Any]],
    cfg: AgentConfig | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    """Phase 4 counterpart to decide_round: same one-call-per-round,
    same retry/validate/failure semantics (via _decide_round_core), same
    return shape -- the only difference is client_history is
    build_client_history()'s output (each stat a sequence, not a scalar)
    and the prompt is built by build_prompt_history / PROMPT_TEMPLATE_HISTORY
    instead of build_prompt / PROMPT_TEMPLATE.
    """
    cfg = cfg or AgentConfig()
    expected_ids = {str(c["client_id"]) for c in client_history}
    prompt = build_prompt_history(round_num, client_history)
    return _decide_round_core(round_num, expected_ids, prompt, cfg)


def decisions_to_weights(
    decisions: list[dict[str, Any]],
    num_examples: dict[str, int],
    downweight_multiplier: float = DEFAULT_DOWNWEIGHT_MULTIPLIER,
) -> dict[str, float]:
    """Per-client UNNORMALIZED aggregation weight (num_examples * decision
    multiplier). Caller normalizes by the sum before use, same convention
    as plain FedAvg's own sample-count weighting.

    trust      -> 1.0 * num_examples (identical to plain FedAvg for that client)
    downweight -> downweight_multiplier * num_examples
    quarantine -> 0.0 (excluded entirely from this round's aggregation --
                  not merely downweighted further)
    """
    multipliers = {"trust": 1.0, "downweight": downweight_multiplier, "quarantine": 0.0}
    weights = {}
    for d in decisions:
        cid = d["client_id"]
        weights[cid] = multipliers[d["decision"]] * num_examples[cid]
    return weights


def log_decisions(
    out_path: Path,
    round_num: int,
    decisions: list[dict[str, Any]],
    raw_stats_by_client: dict[str, dict[str, Any]],
) -> None:
    """Append one JSONL row per (round, silo) to
    results/federated/{tag}/agent_decisions.jsonl, per 01_Planning's
    explicit logging spec: round, silo_id, decision, explanation,
    raw_stats_given. `silo_id` here holds whatever value was used as
    client_id when the prompt was built (this module is client-id-agnostic
    by design, same "architecture-agnostic" posture as client_stats.py --
    it does not know about silo_id as a domain concept, only generic
    client_id strings; the caller is responsible for the silo_id<->client_id
    mapping).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a") as f:
        for d in decisions:
            cid = d["client_id"]
            row = {
                "round": round_num,
                "silo_id": cid,
                "decision": d["decision"],
                "explanation": d["explanation"],
                "raw_stats_given": raw_stats_by_client.get(cid, {}),
            }
            f.write(json.dumps(row) + "\n")


__all__ = [
    "AgentConfig",
    "AgentResponseError",
    "DECISIONS",
    "DEFAULT_DOWNWEIGHT_MULTIPLIER",
    "HISTORY_STAT_FIELDS",
    "RESPONSE_SCHEMA",
    "build_client_history",
    "build_prompt",
    "build_prompt_history",
    "decide_round",
    "decide_round_history",
    "decisions_to_weights",
    "log_decisions",
]
