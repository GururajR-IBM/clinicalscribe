# ClinicalScribe — Product Requirements Document (PRD)

**Status:** Draft v0.1 · awaiting approval
**Owner:** Gururaj Raibagi
**Last updated:** 2026-06-01

---

## 1. Problem statement

US primary-care physicians spend **~2 hours on documentation for every 1 hour of patient care** (AMA, 2023). Existing AI scribes (Nuance DAX, Abridge, Suki) are closed, expensive, and opaque. There is no open, **agentic**, **multi-modal**, **safety-first** reference architecture that an engineer can study, fork, and extend.

**ClinicalScribe** is that reference architecture.

## 2. Vision

> A clinician-assist platform where an agentic system listens, watches, reads, reasons, and drafts — but **never decides**. Every artifact is human-approved, every recommendation is cited, every action is auditable.

## 3. Goals & non-goals

### Goals (v1)
- **G1.** End-to-end demo: doctor records a 5-minute encounter, uploads a scanned lab + a vitals photo, receives a structured SOAP note + ICD-10/CPT codes + patient summary in < 90 seconds.
- **G2.** Every claim in the generated note is **traceable** to a source (transcript span, document region, image feature, or KB citation).
- **G3.** Three working personas (Clinician, Admin, Patient) with role-appropriate UIs.
- **G4.** Eval scorecard runs in CI; PRs blocked if faithfulness drops below threshold.
- **G5.** Full OTel trace for every encounter, browsable in admin UI.
- **G6.** Public repo with README that gets ≥100 GitHub stars in first 90 days (proxy for recruiter discovery).

### Non-goals (explicit)
- **NG1.** No autonomous treatment decisions, prescriptions, or actions taken without clinician sign-off.
- **NG2.** No real PHI. Synthetic + public datasets only. HIPAA-shaped, not HIPAA-certified.
- **NG3.** Not optimized for any single EHR vendor. FHIR-shaped mock EHR only.
- **NG4.** No mobile-native app (responsive web only).
- **NG5.** No fine-tuning. We rely on prompt engineering + RAG + tools.

## 4. Personas & primary user journeys

### 4.1 Dr. Patel — Internal Medicine Physician (primary persona)
1. Starts a new encounter for patient *J. Doe*.
2. Records audio of visit (or uploads existing audio).
3. Drags in a scanned lab PDF and a photo of vitals monitor.
4. Hits **Generate**.
5. Reviews SOAP draft side-by-side with transcript; each sentence is hover-linked to its source.
6. Sees suggested ICD-10 codes (E11.9, I10) and CPT codes (99214) with rationale.
7. Edits, accepts, signs. Audit log records the diff.

### 4.2 Sarah Chen — Practice Administrator
1. Dashboard of last 7 days: encounters processed, avg cost/encounter, avg latency, eval score trend, error rate.
2. Drills into a flagged encounter (Critic agent raised a warning).
3. Opens trace view → sees agent reasoning, tool calls, token spend.
4. Reviews approval/edit metrics per clinician.

### 4.3 John Doe — Patient
1. Receives an email with a magic link.
2. Sees a plain-language summary of his visit ("Your doctor adjusted your blood pressure medicine because...").
3. Sees medications list, follow-up dates, when to call the doctor.
4. Can flag "this is wrong" → routes back to Dr. Patel.

## 5. Functional requirements

### F1 — Encounter ingestion
- F1.1 Accept audio (mp3, wav, m4a, webm) up to 60 min, 100 MB.
- F1.2 Accept PDF, PNG, JPEG up to 10 MB each, up to 10 attachments per encounter.
- F1.3 Resumable uploads via signed Blob URLs.
- F1.4 Async pipeline via Service Bus; UI subscribes via Server-Sent Events for live status.

### F2 — Multi-modal processing
- F2.1 Audio → Azure Speech (medical conversation model) with speaker diarization.
- F2.2 Scanned text → Azure Document Intelligence (prebuilt + custom layout).
- F2.3 Images (vitals monitors, wounds, charts) → GPT-4o vision with structured-output schema.
- F2.4 All extracted content stored as `Evidence` records with provenance (file id, byte range, page, bbox, timestamp).

### F3 — Agent orchestration (MAF)
- F3.1 **Supervisor** agent decomposes encounter into sub-tasks.
- F3.2 **Transcription** agent normalizes raw STT output (speaker labels, paragraphing, medical term correction via MCP Medical KB).
- F3.3 **Entity Extraction** agent extracts symptoms, meds, allergies, vitals, history — outputs to schema validated by Pydantic.
- F3.4 **Retrieval** agent issues hybrid queries to AI Search KB + pgvector encounter memory.
- F3.5 **SOAP Drafter** agent generates SOAP note with inline citation tokens `[E:42]`.
- F3.6 **Coder** agent suggests ICD-10 + CPT with rationale, via MCP Coding server.
- F3.7 **Critic** agent reviews draft for: factual grounding (every claim cited), safety violations (drug interactions via MCP), missing red-flag symptoms, PHI leakage. Returns approve/revise.
- F3.8 If Critic returns revise, Supervisor reruns affected agents up to N=2 times.

### F4 — Knowledge layer
- F4.1 Seed AI Search index with CDC + NIH clinical guidelines (~500 docs) + USPSTF recommendations.
- F4.2 Hybrid retrieval: BM25 + vector (text-embedding-3-large, 3072 dim) + Azure semantic reranker.
- F4.3 Per-clinician encounter memory in pgvector, retrieved by patient_id + similarity.

### F5 — Safety & guardrails
- F5.1 Every prompt run through Azure Content Safety **Prompt Shield** before LLM call.
- F5.2 Every LLM output run through Content Safety jailbreak / harmful content detectors.
- F5.3 Custom PII redactor (presidio) scrubs outputs before sending to patient persona.
- F5.4 Drug Interaction MCP returns hard-stop on dangerous combos; UI surfaces red banner; clinician must explicitly override with reason recorded.
- F5.5 Output JSON validated against Pydantic schema; failed validation triggers single regeneration retry then fails closed.
- F5.6 Refusal pathway: agent refuses out-of-scope (legal advice, billing fraud, etc.) with explanation.

### F6 — Human-in-the-loop approval
- F6.1 No SOAP note is "final" until clinician clicks Sign.
- F6.2 Diff view shows clinician edits vs. AI draft.
- F6.3 Append-only audit log: every state transition, every override, every Critic warning.
- F6.4 Signed notes immutable; corrections create new versions.

### F7 — Observability
- F7.1 OpenTelemetry traces propagate from UI → Gateway → Orchestrator → Agents → Tools/MCP → AOAI.
- F7.2 Each span tagged with: encounter_id, agent_name, tool_name, prompt_version, model, prompt_tokens, completion_tokens, est_cost_usd.
- F7.3 Admin UI embeds a trace viewer (or links out to App Insights).
- F7.4 SLOs: p95 end-to-end latency < 90s for 5-min audio; agent step error rate < 1%.

### F8 — Eval harness
- F8.1 Golden dataset: 50 synthetic encounters with hand-labeled expected SOAP + codes.
- F8.2 Metrics: faithfulness (Ragas), context recall, answer correctness, ICD-10 top-3 accuracy, safety violation rate.
- F8.3 Eval runs nightly + on every PR touching agents/prompts.
- F8.4 PR blocked if faithfulness drops > 3% vs main.
- F8.5 Eval results published to a Docusaurus page (auto-updated).

### F9 — Auth & RBAC
- F9.1 Entra External ID for end-user sign-in (email/password + social IdP).
- F9.2 Workforce Entra ID for admin SSO.
- F9.3 Roles: `clinician`, `admin`, `patient`. Row-level security in Postgres.
- F9.4 Workload identity for AKS → Azure resources (no secrets in pods).

### F10 — APIs
- F10.1 REST API surface (OpenAPI 3.1, generated client for frontend).
- F10.2 SSE endpoint for live agent progress.
- F10.3 Public MCP servers also discoverable so others can plug their own clients.

## 6. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR1 | Performance | p95 < 90s end-to-end for 5-min audio encounter |
| NFR2 | Availability | 99.5% (single region, but documented multi-region path) |
| NFR3 | Cost | Steady-state < $250/mo Azure spend |
| NFR4 | Security | OWASP Top 10 baseline; secrets only in Key Vault; workload identity everywhere |
| NFR5 | Privacy | No real PHI; synthetic-only; data deletion API for any "patient" record |
| NFR6 | Accessibility | WCAG 2.2 AA for clinician + patient UIs |
| NFR7 | Internationalization | Architecture supports i18n; v1 ships en-US only |
| NFR8 | Maintainability | mypy strict, ruff clean, ≥80% test coverage on services, ADRs for every major decision |

## 7. Success metrics

| Metric | Target |
|---|---|
| End-to-end demo works on a fresh clone in < 30 min | Yes |
| GitHub stars in 90 days | ≥100 |
| Eval faithfulness score on golden set | ≥0.85 |
| README time-to-first-screenshot | < 10 seconds of scrolling |
| Recorded demo video length | 4–6 min |
| Interview callbacks attributable to project | ≥3 |

## 8. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Scope creep (3 personas, full SaaS) | High | High | Phase delivery; ship clinician UI first; patient UI can be minimal |
| Azure OpenAI quota limits | Medium | Medium | Use gpt-4o-mini for bulk + semantic cache via APIM; request quota early |
| Eval dataset quality (synthetic) | Medium | High | Have at least 10 entries hand-reviewed by a clinician friend if possible; cite limitation publicly |
| Cost overrun | Medium | Medium | Daily Azure cost alert at $10/day; scale AKS user pool to 0 overnight |
| "Looks like a med device" liability optics | Medium | Medium | Prominent disclaimer; LICENSE excludes clinical use; safety-model.md doc |
| LLM hallucinated medical content | High | High | Mandatory Critic agent; citation enforcement; refusal pathway; eval gate |
| Solo dev burnout | Medium | High | Phased delivery, each phase demoable on its own; don't block on perfection |

## 9. Out of scope (explicit)

- Native mobile apps
- Real-time streaming transcription (we do batch on uploaded audio)
- Multi-tenant SaaS billing (single-tenant for portfolio)
- Fine-tuning custom models
- Real EHR integrations (Epic, Cerner) — mock FHIR only
- HIPAA certification
- Languages other than English
