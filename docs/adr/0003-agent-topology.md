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

**Positive:**
- Citation-grounded SOAP notes with explicit evidence links → auditable, inspectable.
- Structured code suggestions with `justify_code` confidence levels.
- Drug-drug interaction warnings surfaced in the clinical note before sign-off.
- Each agent is independently unit-testable with mocked MCP tools.
- Future agents (e.g. Radiology Interpreter, Vitals Analyser) slot in without orchestrator changes.

**Negative / Mitigations:**
- **Latency**: 7 sequential steps add ~8–15 s per encounter vs ~3 s for Phase 1.
  Mitigated by: parallelising steps 2–3 (entity extraction + retrieval run concurrently),
  parallelising steps 5–6 (coder + drug checker run concurrently).
- **Cost**: ~3× more tokens than Phase 1. Mitigated by using gpt-4o-mini for steps 2–6;
  gpt-4o only for Supervisor and Critic.
- **Complexity**: More moving parts. Mitigated by the clean `AgentState` dataclass as
  single source of truth; each agent is a pure `async def run(state) → state` function.

---

## Implementation Notes

- Phase 2 entry point: `services/orchestrator/src/orchestrator/supervisor.py`.
- `drafter.py` (Phase 1) is retained as a fallback when `AOAI_KEY` is absent.
- Cosmos DB schema for `agent_runs` defined in `infra/terraform/modules/cosmos/` (Phase 3).
- Eval rubric for grading SOAP quality defined in `services/eval-runner/` (Phase 5).
- Before external review, regenerate the Consequences section with Claude Opus 4.7 using
  the actual Phase 5 eval results.
