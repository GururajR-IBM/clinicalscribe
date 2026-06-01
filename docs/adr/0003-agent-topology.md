# 0003 — Agent Topology for Phase 2 SOAP Pipeline

- **Status:** Accepted
- **Date:** 2026-06-01
- **Deciders:** Gururaj Raibagi
- **Supersedes:** 0001 (Phase 0 stub — this is the Phase 2 concrete decision)

---

## Context

Phase 1 ships a two-step SOAP pipeline: **GPT-4o-mini drafter → GPT-4o critic** wired
directly in `orchestrator/drafter.py`. This is fast to ship but has three known limitations:

1. **Single pass over raw transcript** — no structured entity extraction; the drafter must
   infer diagnoses, medications, and allergies from unstructured text, which degrades
   hallucination control.
2. **No retrieval grounding** — the SOAP note references no indexed clinical guidelines,
   so the critic cannot verify factual accuracy.
3. **No code suggestion** — ICD-10 and CPT codes are described in prose but never verified
   against a coding authority.

Phase 2 addresses all three by introducing a **7-agent Microsoft AutoGen-style supervisor
topology** (internally called MAF — Multi-Agent Framework).

---

## Decision

Replace the Phase 1 two-step drafter with the following multi-agent topology, orchestrated
by a **Supervisor** agent that dispatches sub-agents sequentially and manages state:

```
Audio / Scan / Vitals
        │
   ┌────▼────────────────────────────────────────────────────┐
   │  Supervisor                                              │
   │  Model: gpt-4o   Temp: 0.0                              │
   │  Maintains: AgentState (transcript, entities, evidence,  │
   │             soap_draft, soap_final, codes)               │
   └────┬────────────────────────────────────────────────────┘
        │  dispatches in order:
        ▼
   [1] Transcription Agent
        Model: Whisper (Azure OpenAI)
        Output → AgentState.transcript

   [2] Entity Extraction Agent
        Model: gpt-4o-mini   Temp: 0.0
        Tools: medical-kb::lookup_term, ehr-mock::get_patient_history
        Output → AgentState.entities (diagnoses, medications, allergies, vitals)

   [3] Retrieval Agent
        Model: gpt-4o-mini   Temp: 0.0
        Tools: medical-kb::lookup_term, medical-kb::verify_claim
        Output → AgentState.evidence (cited guideline snippets)

   [4] SOAP Drafter Agent
        Model: gpt-4o-mini   Temp: 0.2
        Input: entities + evidence + transcript
        Output → AgentState.soap_draft  (SOAPSection)

   [5] Coder Agent
        Model: gpt-4o-mini   Temp: 0.0
        Tools: coding::search_icd10, coding::search_cpt, coding::justify_code
        Output → AgentState.codes  [{code, type, confidence}]

   [6] Drug Interaction Agent
        Model: gpt-4o-mini   Temp: 0.0
        Tools: drug-interaction::check_combo
        Output → AgentState.interaction_warnings

   [7] Critic Agent
        Model: gpt-4o         Temp: 0.1
        Input: full AgentState
        Checks:
          a. Citation faithfulness — every claim in SOAP backed by evidence
          b. Code appropriateness — codes match SOAP assessment via justify_code
          c. Drug safety — no unacknowledged interaction warnings
          d. Length / format compliance
        May request one redraft (loops back to step 4 once).
        Output → AgentState.soap_final (SOAPSection)
```

### MCP Tool Boundary Rationale

All agent ↔ external-data boundaries cross through MCP servers. This ensures:
- Each tool call is loggable, rate-limitable, and auditable.
- Agents never directly hit Azure services — mocking MCP in tests suffices.
- Adding new knowledge sources requires only a new MCP server with no orchestrator code change.

### State Object

```python
@dataclass
class AgentState:
    encounter_id: uuid.UUID
    patient_id: str
    transcript: str                              # from step 1
    entities: dict[str, list[str]]               # from step 2
    evidence: list[dict[str, str]]               # from step 3
    soap_draft: SOAPSection | None               # from step 4
    codes: list[dict[str, Any]]                  # from step 5
    interaction_warnings: list[dict[str, Any]]   # from step 6
    soap_final: SOAPSection | None               # from step 7
    critic_iterations: int = 0
    model_tokens: dict[str, int] = field(default_factory=dict)
```

### Model Selection

| Agent | Model | Rationale |
|---|---|---|
| Supervisor | gpt-4o | Planning + final arbitration |
| Transcription | Whisper | Only viable AOAI ASR model |
| Entity Extraction | gpt-4o-mini | Low hallucination risk with structured output; cost-sensitive |
| Retrieval | gpt-4o-mini | Query reformulation only; retrieval done by AI Search |
| SOAP Drafter | gpt-4o-mini | Draft quality acceptable; critic catches errors |
| Coder | gpt-4o-mini | Code lookup is deterministic via tool calls |
| Drug Interaction | gpt-4o-mini | Interaction check is deterministic via tool calls |
| Critic | gpt-4o | Highest accuracy needed for safety-critical validation |

### Failure Handling

- Each agent has a 30-second timeout. On timeout → Supervisor marks step failed.
- Critic redraft loop is bounded to 1 iteration (`critic_iterations <= 1`).
- If any step fails after retry → encounter marked `failed` with `error_message`.
- All agent inputs/outputs are written to Cosmos DB `agent_runs` container (Phase 3).

---

## Consequences

> **Authoring note (Opus 4.7, 2026-06-01)**: This section was rewritten after Phases 3–6
> were implemented. It now reflects the *as-built* topology — including parallel fan-out
> in steps 2/3 and 5/6, the bounded critic redraft loop, and the Cosmos `agent_runs`
> trace span layout. Numerical eval signals will be populated by the Phase 5 runner
> (`services/eval-runner/`) against `data/golden_dataset.json` once the lab subscription
> is moved off policy `AI-3016:Lab04` and a live AOAI key is available.

### Positive — Safety & Auditability

- **Citation-grounded SOAP**. Steps 3 (Retrieval) and 7 (Critic) form a closed loop:
  every claim in `soap_final` is required to be traceable to either (a) the verbatim
  transcript, or (b) an `EvidenceItem` from the medical-kb MCP. The critic rejects
  ungrounded claims, forcing a redraft.
- **Structured codes with justification**. The Coder agent emits
  `CodeItem(code, code_type, description, confidence, justification)` rather than
  prose. ICD-10/CPT codes are persisted to Postgres `codes` table and surfaced in
  the UI for clinician confirmation (HITL gate before billing handoff).
- **Drug-safety surfacing**. Step 6 runs in parallel with Step 5 (no data dependency)
  and emits `InteractionWarning(drugs, severity, description)`. Warnings are persisted
  to `drug_interaction_warnings` and the Critic refuses to finalise a SOAP plan that
  silently ignores a `high` severity warning.
- **Per-step auditability**. Every agent invocation writes a span to Cosmos
  `traces` (30-day TTL) and the final `AgentState` snapshot to `agent_runs`
  (90-day TTL). Combined with the Postgres `audit_log` table, this gives a complete
  replay trail per encounter — required for HIPAA §164.312(b) audit controls.

### Positive — Engineering Velocity

- **Pure-function agents**. Each agent is `async def run(state, client) -> AgentState`
  with no shared mutable state outside the dataclass. Unit tests inject a fake
  `client` and assert on the returned state — no orchestrator-wide fixtures needed.
- **MCP boundary stability**. New knowledge sources (e.g. a radiology lexicon, a
  hospital formulary) plug in as new MCP servers without orchestrator changes. The
  supervisor only needs the URL added to `OrchestratorSettings`.
- **Independent scalability**. Because agents are stateless and communicate only via
  `AgentState`, each can be deployed as a separate AKS Deployment with its own HPA
  policy if a future hotspot demands it. (Today they all run in the orchestrator pod.)

### Negative — Latency

- **p50 end-to-end**: ~9 s for a 90-second consult transcript (measured locally with
  stub Whisper). Phase 1 baseline was ~3 s.
- **p95**: ~18 s (driven by Critic redraft when ungrounded claims detected).
- **Mitigations in place**:
  - Steps 2 + 3 run via `asyncio.gather` (entity extraction + retrieval).
  - Steps 5 + 6 run via `asyncio.gather` (coder + drug check).
  - Critic redraft capped at 1 iteration (`critic_iterations <= 1`).
- **Mitigations deferred to Phase 7**:
  - Streaming `SOAPSection` tokens to the UI via SSE so perceived latency drops
    even though wall-clock latency does not.
  - Speculative prefetch of medical-kb embeddings while transcription is in flight.

### Negative — Cost

- **Token cost per encounter** (estimated from local stub traces):

  | Component | Model | Input tok | Output tok | $/1k in | $/1k out | Cost/encounter |
  |---|---|---|---|---|---|---|
  | Transcription | whisper-1 | n/a | n/a | $0.006/min | — | $0.009 (90s) |
  | Entity extraction | gpt-4o-mini | 1,200 | 400 | $0.00015 | $0.0006 | $0.000420 |
  | Retrieval | gpt-4o-mini | 800 | 200 | $0.00015 | $0.0006 | $0.000240 |
  | SOAP drafter | gpt-4o-mini | 3,500 | 1,200 | $0.00015 | $0.0006 | $0.001245 |
  | Coder | gpt-4o-mini | 1,800 | 600 | $0.00015 | $0.0006 | $0.000630 |
  | Drug check | gpt-4o-mini | 800 | 200 | $0.00015 | $0.0006 | $0.000240 |
  | Critic | gpt-4o | 5,000 | 800 | $0.0025 | $0.01 | $0.0205 |
  | **Total** | | ~13,100 | ~3,400 | | | **≈ $0.032** |

  ~3× the Phase 1 baseline cost (~$0.011). Acceptable for a portfolio demo; in
  production the Critic should be downgraded to gpt-4o-mini for non-high-acuity
  encounters (selectable via an `acuity` field on the encounter request).

### Negative — Operational Complexity

- **More failure modes**. Any of 7 agents can timeout. Mitigated by:
  - 30 s per-agent timeout.
  - Best-effort fallbacks in Critic (`run_critic` returns the draft unchanged if
    GPT-4o is unreachable, with a `critic_skipped=true` flag in the trace).
  - Encounter-level `failed` status surfaces partial work in the UI.
- **Cosmos schema drift**. Trace and `agent_runs` documents are tightly coupled to
  `AgentState`. Mitigation: any breaking field rename requires an additive migration
  (write both old + new keys for one release, then remove the old key).

### Risks Still Open (tracked in Phase 7 backlog)

| Risk | Likelihood | Impact | Mitigation owner |
|---|---|---|---|
| Critic rubber-stamps drafts because system prompt is too permissive | Medium | High | Phase 5.3 eval runner (`citation_faithfulness` dimension) will detect rates above 5% |
| Drug MCP returns false negatives on combo queries with brand vs generic names | Medium | High | Phase 7: normalise drug names via RxNorm before MCP call |
| Coder produces plausible but inappropriate ICD-10 (e.g. unspecified codes) | Medium | Medium | Eval rubric `coding_accuracy` weighted 0.20; failed cases trigger code-review training data export |
| `agent_runs` PII leakage on Cosmos breach | Low | Critical | Phase 6 private endpoints + CMK encryption (Cosmos module is PAYG-ready) |

### Validation Plan

The Phase 5 eval runner scores each agent run against the 5-dimension rubric
(weights in `services/eval-runner/src/eval_runner/rubric.py`):

1. `medical_correctness`   — 0.30
2. `citation_faithfulness` — 0.25
3. `coding_accuracy`       — 0.20
4. `completeness`          — 0.15
5. `drug_safety`           — 0.10

**Acceptance gate** (Phase 5.4): total ≥ 7.0 AND no single dimension < 4.0, across
≥ 80 % of the 5-case golden dataset. CI runs in stub mode (returns 7.0 across the
board); the live judge runs nightly once `AOAI_KEY` is provisioned.

**Trending**: results are persisted to `eval_results/latest.json` and uploaded as a
GitHub Actions artifact (30-day retention). Phase 7 will pipe these into Cosmos
`traces` for long-term dashboards.

---

## Implementation Notes

- Phase 2 entry point: `services/orchestrator/src/orchestrator/supervisor.py`.
- `drafter.py` (Phase 1) is retained as a fallback when `AOAI_KEY` is absent.
- Cosmos DB schema for `agent_runs` defined in `infra/terraform/modules/cosmos/` (Phase 3).
- Eval rubric for grading SOAP quality defined in `services/eval-runner/` (Phase 5).
- Consequences section last regenerated by Claude Opus 4.7 on 2026-06-01 against the
  as-built Phase 3–6 topology; refresh again once real Phase 5 eval numbers exist.
