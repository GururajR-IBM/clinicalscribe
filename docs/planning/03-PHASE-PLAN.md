# ClinicalScribe — Phase-Wise Delivery Plan

**Status:** Final · 2026-06-01
**Companion to:** `00-DECISIONS-REVIEW.md`, `01-PRD.md`, `02-ARCHITECTURE.md`, `04-AZURE-SERVICES.md`

Each phase is independently demoable, deployable, and producible as a portfolio artifact. No phase is "internal refactoring only."

---

## How to read this doc

- Each phase has **Exit Criteria** (when it's done), a **Demo** (what you can show), and **What you learn** (the resume bullet you earn).
- **Az** column in task tables = which Azure services from `04-AZURE-SERVICES.md` need to exist before the task runs.
- **Tasks are sized in "sessions"** — a session ≈ 1 focused 2–3 hour block. Use it to plan your week, not to commit a date.

---

## Phase 0 — Foundation (the boring stuff that pays compound interest)

**Goal:** Repo, tooling, CI skeleton, IaC bootstrap, one-time Azure setup. Nothing user-facing yet.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 0.1 | Create `c:\Working\clinicalscribe\` monorepo; init git; push empty to GitHub (`GururajR-IBM/clinicalscribe`) | — | 0.5 |
| 0.2 | Add monorepo tooling: pnpm workspaces (frontend) + uv workspaces (Python) + Turborepo for task orchestration | — | 1 |
| 0.3 | Pre-commit config: ruff, mypy, eslint, prettier, terraform-fmt, conventional-commits | — | 0.5 |
| 0.4 | Empty service stubs: `services/gateway`, `services/orchestrator`, `services/ingestion-worker`, `services/eval-runner`, `apps/web`, 4× `mcp-servers/*` — each with a Dockerfile and a "hello" endpoint | — | 2 |
| 0.5 | GitHub Actions CI skeleton: lint + type-check + unit test matrix per package | — | 1 |
| 0.6 | **Terraform bootstrap**: `infra/terraform/bootstrap/` creates the state-storage account + container with native blob locking. Run **once** manually. | A1 (Storage) | 1 |
| 0.7 | Terraform main skeleton + `azurerm` + `azapi` providers + remote backend wired; `dev.tfvars` + `dev.backend.hcl` | — | 1 |
| 0.8 | **Workload Identity Federation** from GitHub Actions to Azure (OIDC, no secrets) | Entra app reg | 1 |
| 0.9 | First Terraform module: `network/` (VNet, subnets, NSGs) using Azure Verified Module wrapper. Plan + apply to dev. | A2 (Network) | 1.5 |
| 0.10 | First ADRs: `0001-architecture.md`, `0006-iac-terraform.md` (you write these with Opus 4.7) | — | 1.5 |
| 0.11 | `docs/` Docusaurus site scaffold (deploy to GH Pages from `main`) | — | 1 |
| 0.12 | Root `README.md` v0: project pitch, "currently in Phase 0" status, architecture diagram embed | — | 0.5 |

**Exit Criteria**
- [ ] `git push` → CI green
- [ ] `terraform apply -var-file=environments/dev.tfvars` succeeds, creates VNet
- [ ] Docusaurus site live at `https://gururajr-ibm.github.io/clinicalscribe`
- [ ] All 8 services build their Docker image in CI

**Demo:** "Here's a clean monorepo with green CI, deployed docs site, and Terraform spinning up an Azure VNet via Workload Identity Federation — no secrets anywhere." That alone is a senior-grade Phase 0.

**What you learn:** Monorepo orchestration · Terraform with remote state + OIDC auth · Azure Verified Modules · Workload Identity Federation · Docusaurus + GH Pages CI/CD

---

## Phase 1 — Vertical Slice (one modality, one agent, end-to-end)

**Goal:** Upload audio → get back a SOAP draft. No multi-agent yet. Prove the pipe works end-to-end and is deployable.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 1.1 | Terraform: AKS cluster (1 system pool + 1 user pool, autoscale 1–3) using AVM module | A3 (AKS), A4 (ACR) | 2 |
| 1.2 | Terraform: Azure OpenAI resource + `gpt-4o-mini`, `gpt-4o`, `text-embedding-3-large` deployments | A5 (AOAI) | 1 |
| 1.3 | Terraform: Postgres Flexible Server + database + `pgcrypto` extension (NOT pgvector — Cosmos owns vectors) | A6 (Postgres) | 1 |
| 1.4 | Terraform: Cosmos DB NoSQL account + database + containers (`evidence`, `embeddings`, `agent_runs`) with vector indexing policy | A7 (Cosmos) | 1.5 |
| 1.5 | Terraform: Blob Storage account + container `encounter-media` + lifecycle policy (delete after 90 days) | A8 (Blob) | 0.5 |
| 1.6 | Terraform: Key Vault + access via workload identity | A9 (KV) | 1 |
| 1.7 | Terraform: Application Insights + Log Analytics workspace | A10 (App Insights) | 0.5 |
| 1.8 | Terraform: Azure AI Speech resource | A11 (Speech) | 0.5 |
| 1.9 | **Auth foundation**: Clerk app set up, JWT-validation middleware in `gateway` (FastAPI), `users` table in Postgres on first login | — | 2 |
| 1.10 | `gateway` API: `POST /encounters` (creates encounter, returns signed Blob upload URL), `GET /encounters/{id}` | A6, A8 | 2 |
| 1.11 | `gateway` SSE endpoint: `GET /encounters/{id}/events` (server-sent events for live progress) | — | 1 |
| 1.12 | `ingestion-worker`: polls `encounters` table (no Service Bus yet — keep it simple), downloads audio from Blob, calls Speech, writes raw transcript to Cosmos `evidence` container | A6, A7, A8, A11 | 2.5 |
| 1.13 | `orchestrator`: single MAF agent ("SOAP Drafter v0") — takes transcript evidence, calls AOAI gpt-4o-mini, returns SOAP JSON | A5, A7 | 2.5 |
| 1.14 | `apps/web`: Next.js 15 + Clerk auth + 3 pages: Login, Encounters List, Encounter Detail (upload + view draft) | — | 4 |
| 1.15 | Helm charts for `gateway`, `orchestrator`, `ingestion-worker` + Helmfile for orchestration | — | 2 |
| 1.16 | GH Actions CD: build → push to ACR → `helm upgrade --install` to dev AKS | A3, A4 | 2 |
| 1.17 | E2E test: upload sample audio via Playwright → expect SOAP appears within 60s | — | 1.5 |
| 1.18 | ADR: `0003-agent-topology.md` (v0 = single agent; will evolve in Phase 2) | — | 1 |

**Exit Criteria**
- [ ] User signs in via Clerk on `https://dev.clinicalscribe.<your-domain or AKS LB IP>`
- [ ] Uploads a 2-min audio clip, sees SOAP note in < 60s
- [ ] Trace ID visible in App Insights for the whole flow
- [ ] All infra reproducible from `terraform apply`

**Demo:** Record a 90-second screencap of the upload-to-SOAP flow. Put it in the README.

**What you learn:** AKS + Helm production patterns · Clerk JWT auth in FastAPI · Server-Sent Events · Azure Speech batch transcription · MAF single-agent basics · Cosmos vector container setup · End-to-end deployment with Workload Identity

---

## Phase 2 — Multi-agent + MCP + Hybrid RAG

**Goal:** Replace the single agent with the supervisor + specialist topology. Stand up MCP servers. Seed a medical knowledge base in AI Search.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 2.1 | Terraform: Azure AI Search Basic + index with semantic config + vector profile | A12 (AI Search) | 1.5 |
| 2.2 | Terraform: Service Bus namespace + queues (`ingest.requested`, `agentrun.requested`, `agentrun.completed`) | A13 (Service Bus) | 1 |
| 2.3 | **Knowledge seeder**: `scripts/seed-search-index.py` — pulls CDC + USPSTF + NIH guidelines (publicly licensed), chunks them, embeds with `text-embedding-3-large`, uploads to AI Search | A5, A12 | 3 |
| 2.4 | Refactor `ingestion-worker` to consume from Service Bus instead of polling | A13 | 1.5 |
| 2.5 | Refactor `orchestrator` to consume from Service Bus, publish completion events | A13 | 1.5 |
| 2.6 | **MCP server: `medical-kb`** — exposes `lookup_term`, `normalize_drug_name`, `verify_claim`. Backed by AI Search hybrid query. Deployed as a separate pod in AKS. | A12 | 2.5 |
| 2.7 | **MCP server: `coding`** — exposes `search_icd10`, `search_cpt`, `justify_code`. Backed by static ICD-10/CPT tables loaded into Postgres. | A6 | 2 |
| 2.8 | **MCP server: `ehr-mock`** — exposes `get_patient_history`, `get_active_medications`. Synthetic FHIR-style data. | A6 | 1.5 |
| 2.9 | **MCP server: `drug-interaction`** — exposes `check_combo`. Calls openFDA public API + local cache in Postgres. | A6 | 2 |
| 2.10 | MAF agent topology (full): Supervisor + Transcription + Entity Extraction + Retrieval + SOAP Drafter + Coder + Critic | A5 | 4 |
| 2.11 | Citation system: every SOAP sentence must reference an `evidence_id`. Drafter prompted to emit `[E:42]` tokens; post-processor validates all tokens resolve. | — | 2 |
| 2.12 | UI: side-by-side transcript ↔ SOAP with hover citations | — | 2.5 |
| 2.13 | UI: ICD-10 / CPT codes panel with rationale tooltips | — | 1.5 |
| 2.14 | OpenTelemetry instrumentation: spans for every agent call, every tool call, every LLM call (tokens + cost on each span) | A10 | 3 |
| 2.15 | ADR: `0003-agent-topology.md` (update), `0007-mcp-server-design.md` | — | 1.5 |

**Exit Criteria**
- [ ] 7 agents visible in App Insights distributed trace for one encounter
- [ ] 4 MCP servers running as separate pods, observable via OTel
- [ ] Every SOAP sentence has at least one citation that resolves
- [ ] Hybrid search returns sensible results for "metformin side effects" type queries

**Demo:** Same upload as Phase 1, but now: live agent progress in UI, SOAP with citations, ICD-10 codes with rationale. Click a sentence → highlights the audio span.

**What you learn:** MAF multi-agent orchestration · MCP server design (this is rare!) · Hybrid RAG (BM25 + vector + semantic reranker) · Service Bus async patterns · Distributed tracing through agent calls · Citation enforcement in LLM output

---

## Phase 3 — Multi-modal + memory

**Goal:** Accept scanned PDFs and images alongside audio. Add per-patient encounter memory.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 3.1 | Terraform: Azure Document Intelligence resource | A14 (Doc Intel) | 0.5 |
| 3.2 | `ingestion-worker`: detect attachment kind, route to Speech / Doc Intel / GPT-4o vision | A5, A11, A14 | 3 |
| 3.3 | Doc Intel: extract structured tables/key-value from lab PDFs; write to Cosmos as evidence with bbox provenance | A14 | 2 |
| 3.4 | GPT-4o vision: extract structured vitals from monitor photos (`{"bp": "142/88", "hr": 78, ...}`) with confidence scores | A5 | 2 |
| 3.5 | Cosmos: encounter-memory pattern — embeddings on past notes per `patient_id` | A7 | 2 |
| 3.6 | Retrieval agent enhancement: combine medical KB hits + patient history hits | A12, A7 | 2 |
| 3.7 | UI: multi-file dropzone, attachment thumbnails, per-attachment processing status | — | 3 |
| 3.8 | UI: citation hover works for text spans (transcript), PDF regions (with bbox highlight), and image regions | — | 3 |
| 3.9 | Synthetic data: `scripts/synth-encounters.py` generates 20 multi-modal encounters (audio via TTS, lab PDFs via reportlab, vitals images via PIL) for the demo + eval | — | 3 |

**Exit Criteria**
- [ ] Upload audio + 1 PDF + 1 image → unified SOAP referencing all three
- [ ] Hover any SOAP sentence → highlights audio timestamp OR PDF region OR image region
- [ ] Patient's previous visit summary surfaces in the "Subjective" section when relevant

**Demo:** Update screencap to show multi-modal upload + cross-modal citations.

**What you learn:** Multi-modal AI orchestration · Document Intelligence + GPT-4o vision in production · Cross-modal provenance tracking · Per-tenant vector memory patterns

---

## Phase 4 — Safety, guardrails, human-in-the-loop

**Goal:** This is what separates an "AI demo" from a "responsible-AI portfolio piece." Critical for FAANG signal.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 4.1 | Terraform: Azure AI Content Safety resource | A15 (Content Safety) | 0.5 |
| 4.2 | Prompt Shield: every user-derived prompt scanned before LLM call (middleware in orchestrator) | A15 | 1.5 |
| 4.3 | Output safety scan: every LLM response scanned for harm categories before persistence | A15 | 1 |
| 4.4 | Custom PII redactor using `presidio-analyzer` — scrubs outputs for the Patient persona view | — | 2 |
| 4.5 | Drug Interaction MCP hard-stop: if `severity >= MAJOR`, Critic blocks sign-off; clinician must explicitly override with reason recorded in `audits` | — | 2 |
| 4.6 | Pydantic schema validation on every LLM JSON output; single retry on failure, then fail-closed | — | 1 |
| 4.7 | Refusal pathway: agent refuses out-of-scope requests (legal, billing fraud, etc.) with explanation; logged in audits | — | 1.5 |
| 4.8 | **Approval workspace UI**: diff view (AI draft vs clinician edits), sign button, signed notes immutable, version history | — | 4 |
| 4.9 | **Audit log UI**: append-only timeline view per encounter — every state transition, override, warning, edit | — | 2.5 |
| 4.10 | Roles & RBAC: `clinician` / `admin` / `patient` roles in `users` table; Postgres row-level security policies; per-route guards in gateway | — | 2.5 |
| 4.11 | Threat model doc: `docs/safety-model.md` — STRIDE-style table covering each component | — | 2 |
| 4.12 | ADR: `0002-safety-model.md`, `0008-rbac-and-rls.md` | — | 1.5 |

**Exit Criteria**
- [ ] Inject a prompt injection in an uploaded audio (literally say "ignore previous instructions") → blocked by Prompt Shield, logged in audits
- [ ] Try generating a SOAP with a dangerous drug combo → red banner, sign blocked until override
- [ ] Sign a note → it becomes immutable; edits create v2
- [ ] Patient persona only sees redacted output

**Demo:** Record a 2-min "safety in action" video — prompt injection blocked, drug-interaction hard-stop, audit log walkthrough.

**What you learn:** Azure Content Safety + Prompt Shields · Microsoft Presidio · Postgres row-level security · STRIDE threat modeling · Append-only audit patterns · Schema-driven LLM output validation

---

## Phase 5 — Eval harness + production observability

**Goal:** Treat AI as software engineering. This phase is what makes the project FAANG-worthy.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 5.1 | `evals/datasets/golden/` — 50 synthetic encounters with hand-labeled expected SOAP key facts, expected ICD-10 top-3, expected safety flags | — | 5 |
| 5.2 | `eval-runner` service: loads dataset, runs encounters through full pipeline, computes metrics | A5, A7 | 3 |
| 5.3 | Metrics: Ragas (faithfulness, context recall, answer correctness) + custom (ICD-10 top-3 accuracy, citation coverage %, safety violation rate) | — | 3 |
| 5.4 | Azure AI Evaluations SDK integration — submit runs to Azure AI Studio for visualization | A16 (AI Foundry project) | 2 |
| 5.5 | **Eval-gate CI workflow**: PRs touching `services/orchestrator/`, `packages/prompts/`, or `mcp-servers/` run a 5-case smoke eval; block merge if faithfulness drops > 3% vs main | — | 2 |
| 5.6 | Nightly full-50 eval via GH Actions cron; publish report to Docusaurus site as `/evals/<date>.html` | — | 2 |
| 5.7 | **Prompt versioning**: `packages/prompts/` with semver; every LLM call tags the prompt version in OTel span | — | 1.5 |
| 5.8 | OTel trace viewer in admin UI: embeds App Insights iframe or builds a custom waterfall view | A10 | 3 |
| 5.9 | Token & cost dashboard: admin UI page showing $/encounter, tokens/agent, p50/p95 latency per agent | A10 | 3 |
| 5.10 | Load test: k6 script — 10 concurrent encounters; document p50/p95/p99 results in repo | — | 2 |
| 5.11 | ADR: `0009-eval-harness.md`, `0010-prompt-versioning.md` | — | 1.5 |

**Exit Criteria**
- [ ] Open a PR that worsens a prompt → CI blocks merge with diff in scores
- [ ] Nightly eval report shows up on Docusaurus
- [ ] Admin can see "this encounter cost $0.12 and took 47s, here's the per-agent breakdown"
- [ ] Documented load test result in `docs/perf.md`

**Demo:** Walk through an eval scorecard, a blocked PR, and a cost dashboard. **This is the segment that convinces senior interviewers.**

**What you learn:** Ragas + Azure AI Evaluations · CI eval gates · Prompt versioning · OTel waterfall analysis for LLM apps · k6 load testing · LLM cost engineering

---

## Phase 6 — Production polish, APIM AI Gateway, story-telling

**Goal:** Make the repo recruitable. Polish, document, story-tell.

| # | Task | Az needed | Sessions |
|---|---|---|---|
| 6.1 | Terraform: APIM Consumption tier + AI Gateway policies (token limit, semantic cache, content safety, backend = AOAI) | A17 (APIM) | 3 |
| 6.2 | Migrate orchestrator → call AOAI via APIM endpoint; remove direct AOAI keys | A17, A5 | 1.5 |
| 6.3 | Patient persona UI: minimal read-only summary page + "this is wrong" feedback button | — | 3 |
| 6.4 | Blue/green deploy: 2 helm releases per service (blue + green), traffic-split via ingress | — | 3 |
| 6.5 | Canary rollout for prod: 10% → 50% → 100% with eval-gate at each step | — | 2 |
| 6.6 | Cost optimization pass: AKS cron scale-to-zero overnight; AOAI semantic cache; reserved capacity analysis writeup | — | 2 |
| 6.7 | **The README** — recruiter magnet. Above-the-fold demo GIF, architecture diagram, "why this exists," screenshots, eval scorecard badge, OTel trace screenshot, "deploy your own" 5-step quickstart | — | 4 |
| 6.8 | Demo video: 4-min screencap with voiceover walking through the canonical T2DM+HTN encounter end-to-end | — | 3 |
| 6.9 | All ADRs finalized; Docusaurus site has full architecture deep-dive | — | 3 |
| 6.10 | LICENSE: MIT + explicit "not for clinical use" rider; SECURITY.md; CONTRIBUTING.md | — | 1 |
| 6.11 | Launch: post on r/MachineLearning, HackerNews "Show HN", LinkedIn, Twitter/X, dev.to writeup | — | 2 |
| 6.12 | Update your resume.tex to add ClinicalScribe as the lead project | — | 1 |

**Exit Criteria**
- [ ] README opens with a GIF that hooks in < 5 seconds
- [ ] `https://github.com/GururajR-IBM/clinicalscribe` looks polished enough that you'd star it yourself
- [ ] APIM dashboard shows token limits + semantic cache hit rate
- [ ] Resume updated; first 3 applications submitted

**Demo:** The repo *is* the demo.

**What you learn:** APIM AI Gateway policies · Blue/green + canary deployment · Cost engineering on Azure · Technical writing that ranks · Open-source project launch playbook

---

## Cross-phase: ongoing rules

- **Every merged PR must be deployable.** Never break `main`.
- **Every new service must have:** Dockerfile, helm chart, unit tests, integration test, OTel instrumentation, README.
- **Every new agent must have:** system prompt versioned in `packages/prompts/`, at least 2 golden eval cases, OTel span, schema-validated output.
- **Every Azure resource must be:** in Terraform (never created by hand after Phase 0), tagged with `project=clinicalscribe` and `env=dev|prod`, observable in App Insights.
- **Cost guardrail:** Daily Azure cost alert at $10/day. If hit, scale AKS user pool to 0 and investigate before next session.

---

## What goes on your resume after Phase 6

> **ClinicalScribe** — Open-source multi-agent medical documentation platform on Azure. Multi-modal ingestion (audio, PDF, image) via Azure Speech, Document Intelligence, and GPT-4o vision. 7-agent topology built on Microsoft Agent Framework with 4 custom MCP servers (Medical KB, ICD-10/CPT coding, drug interactions, mock FHIR). Hybrid RAG over CDC/NIH guidelines via Azure AI Search; per-patient memory in Cosmos DB. Full safety stack: Azure Content Safety + Prompt Shields, citation-enforcement, drug-interaction hard-stops, Postgres row-level security. Continuous eval with Ragas + Azure AI Evaluations gating PRs. End-to-end OpenTelemetry tracing with per-agent token/cost attribution. Deployed on AKS with Terraform + Workload Identity Federation; APIM AI Gateway for semantic caching and rate limiting. **Stack:** Python, FastAPI, MAF, MCP, Next.js 15, Clerk, Azure OpenAI, Azure AI Search, Cosmos DB, Postgres, AKS, Terraform.
