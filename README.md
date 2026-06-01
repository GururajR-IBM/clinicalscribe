# ClinicalScribe

> **Status:** 🚧 Phase 0 — Foundation. Not yet deployable. See [docs/planning/03-PHASE-PLAN.md](docs/planning/03-PHASE-PLAN.md).

**ClinicalScribe** is an open-source, **multi-agent, multi-modal medical documentation platform** built on Azure. It turns a doctor–patient encounter (audio recording + scanned labs + vitals photos) into a structured SOAP note, suggested ICD-10/CPT codes, and a plain-English patient summary — with **mandatory clinician sign-off**, **end-to-end citations**, and a **full safety + eval stack**.

This repo is a reference architecture for production-grade **agentic AI on Azure**, designed as a portfolio piece demonstrating senior-level engineering across the modern AI stack.

---

## Why this exists

US primary-care physicians spend ~2 hours on documentation for every 1 hour of patient care. Commercial AI scribes exist but are closed and opaque. ClinicalScribe is the open, auditable, **engineer-friendly** counterpart — a system you can fork, study, deploy, and extend.

> ⚠️ **Not for clinical use.** This is a portfolio / research project. Uses synthetic data only. See [LICENSE](LICENSE) for the explicit non-clinical-use rider.

---

## What it demonstrates

| Capability | Implementation |
|---|---|
| **Multi-agent orchestration** | 7-agent topology on **Microsoft Agent Framework (MAF)** with Supervisor + reflection loop via Critic agent |
| **MCP servers** | 4 custom Model Context Protocol servers (Medical KB, Drug Interaction, ICD/CPT Coding, FHIR EHR Mock) |
| **Multi-modal ingestion** | Audio → Azure AI Speech · Scanned PDFs → Document Intelligence · Vitals images → GPT-4o vision |
| **Hybrid RAG** | Azure AI Search (BM25 + vector + semantic reranker) over CDC/NIH/USPSTF guidelines |
| **Polyglot persistence** | Cosmos DB NoSQL (vectors + agent telemetry) + Postgres (transactional audit + RBAC) |
| **Safety stack** | Azure AI Content Safety + Prompt Shields + custom PII redaction + drug-interaction hard-stops + citation enforcement |
| **Eval harness** | Ragas + Azure AI Evaluations against 50-case golden dataset, gating PR merges in CI |
| **Observability** | OpenTelemetry → Application Insights with per-agent token/cost spans |
| **Production infra** | AKS + Terraform (+ Azure Verified Modules) + Workload Identity Federation (no secrets in CI) |
| **AI Gateway** | Azure API Management with semantic caching + token limits in Phase 6 |

---

## Architecture (high level)

See [docs/planning/02-ARCHITECTURE.md](docs/planning/02-ARCHITECTURE.md) for full diagrams.

```
Browser → APIM → FastAPI Gateway → Service Bus → Orchestrator (MAF)
                                                       ↓
   ┌───────────────────────────────────────────────────┴────────────────────┐
   │  Supervisor → Transcription → Entity Extraction → Retrieval            │
   │             → SOAP Drafter → Coder → Critic (safety + grounding loop)  │
   └────────────────────────────────────────────────────────────────────────┘
                              ↓                  ↓                ↓
                       MCP Servers       Azure AI Search    Cosmos + Postgres
                       (4 sidecars)         (hybrid KB)        (polyglot)
```

---

## Stack

**Frontend** Next.js 15 · TypeScript · Tailwind · shadcn/ui · TanStack Query · Clerk
**Backend** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · uv
**Agents** Microsoft Agent Framework · MCP Python SDK
**AI** Azure OpenAI (gpt-4o · gpt-4o-mini · text-embedding-3-large) · Azure AI Speech · Document Intelligence · Content Safety
**Data** Azure Cosmos DB NoSQL · PostgreSQL Flexible Server · Azure AI Search · Blob Storage · Service Bus
**Infra** AKS · Terraform 1.15+ (azurerm + azapi + Azure Verified Modules) · Workload Identity Federation
**Ops** OpenTelemetry · Application Insights · APIM AI Gateway (Phase 6)
**Quality** ruff · mypy strict · pytest · eslint · vitest · playwright · tflint · tfsec · checkov

---

## Repository layout

```
clinicalscribe/
├── apps/                # Next.js web app + Docusaurus docs site
├── services/            # FastAPI services: gateway, orchestrator, ingestion-worker, eval-runner
├── mcp-servers/         # 4 Model Context Protocol servers
├── packages/            # Shared Pydantic + TS schemas, versioned prompts
├── infra/
│   ├── terraform/       # All Azure infrastructure (modules + per-env config)
│   └── helm/            # Helm charts per service
├── evals/               # Golden datasets + eval runners + reports
├── scripts/             # Seed scripts, synthetic data generators, cost reports
└── docs/
    ├── adr/             # Architecture Decision Records (0001+)
    └── planning/        # Initial planning docs (5 files)
```

---

## Phase roadmap

| Phase | Focus | Status |
|---|---|---|
| **0** | Foundation: monorepo, CI, Terraform skeleton, ADRs | 🚧 In progress |
| 1 | Vertical slice: audio → single-agent SOAP draft on AKS | ⏳ |
| 2 | Multi-agent + 4 MCP servers + hybrid RAG | ⏳ |
| 3 | Multi-modal (PDF + image) + per-patient memory | ⏳ |
| 4 | Safety, guardrails, human-in-the-loop, RBAC | ⏳ |
| 5 | Eval harness + observability + CI eval gate | ⏳ |
| 6 | APIM AI Gateway + production polish + launch | ⏳ |

Full plan in [docs/planning/03-PHASE-PLAN.md](docs/planning/03-PHASE-PLAN.md).

---

## License

MIT, with explicit **not for clinical use** rider. See [LICENSE](LICENSE).
