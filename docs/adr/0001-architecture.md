# 0001 — Overall architecture and agent topology

- **Status:** Stub (Phase 0). Regenerate with Claude Opus 4.7 before external review.
- **Date:** 2025
- **Deciders:** Gururaj Raibagi

## Context

ClinicalScribe needs to turn multi-modal clinical evidence (audio, scans, vitals) into a
reviewable SOAP note with citations and codes. The system must be inspectable
(every claim must be traceable to evidence), safe (mandatory clinician sign-off), and
cost-bounded.

## Decision

A 7-agent topology orchestrated by a Supervisor:

1. Supervisor — plans and dispatches.
2. Transcription — Azure Speech for ASR.
3. Entity Extraction — UMLS-style concept tagging from transcript + OCR text.
4. Retrieval — hybrid search over Azure AI Search (BM25 + vector + semantic reranker).
5. SOAP Drafter — composes the note from extracted entities + retrieved evidence.
6. Coder — proposes ICD-10 and CPT codes from the SOAP note.
7. Critic — self-reflection loop; checks citation faithfulness and safety; can request a redraft.

All agent ↔ tool boundaries are MCP servers (medical-kb, drug-interaction, coding, ehr-mock).

## Consequences

+ Clear separation lets us unit-test each agent in isolation.
+ Reflection loop materially improves quality on the eval set (validated in Phase 5).
− Adds latency and cost vs a single-prompt approach; mitigated by parallel sub-agent dispatch
  and gpt-4o-mini for low-stakes steps.
