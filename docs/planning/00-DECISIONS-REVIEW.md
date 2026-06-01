# ClinicalScribe — Decision Review (FINAL)

> You asked me to critically review your selections from the planning questionnaire and override where suboptimal for the stated goal (**land interviews at Microsoft / FAANG-class companies, on a $100–300/mo Azure budget, open-ended timeline, public repo from day 1**).

**Status:** Decisions finalized 2026-06-01. User reviewed both overrides and chose to **keep the original picks**. This doc captures the final stack and the reasoning we will use to defend each choice in interviews.

## Final decisions at a glance

| Decision | Choice | Notes |
|---|---|---|
| Database | **Cosmos DB NoSQL + Postgres Flex** | Polyglot persistence — needs ADR-0004 to justify |
| Auth | **Clerk** | Time-to-market choice; Entra External ID listed as roadmap |
| Compute | **AKS** | Confirmed |
| Framework | **Microsoft Agent Framework (MAF)** | Confirmed |
| UI | **Full SaaS, 3 personas** | Sequenced: Clinician → Admin → Patient |
| **IaC** | **Terraform 1.9+ (`azurerm` + `azapi`)** | Switched from Bicep. State in Azure Storage with native blob locking; separate state per env. ADR-0006. |
| Repo | `c:\Working\clinicalscribe\` → `github.com/GururajR-IBM/clinicalscribe` (public) | |
| Demo scenario | 60yo T2DM + HTN annual visit | Canonical README demo |

---

## Decision #1 — Database (Cosmos + Postgres, both)

**Final:** Polyglot persistence. Cosmos DB NoSQL for high-volume vector-queried data, Postgres Flex for transactional relational data.

### Defensible split (must be implemented exactly this way to justify the dual DB)

| Store | Owns | Why this store |
|---|---|---|
| **Cosmos DB NoSQL** (with integrated vector search) | `evidence` (transcript spans, OCR regions, image features), `embeddings`, `agent_runs` (telemetry trail), `traces` | High write volume, append-mostly, schema-flexible per modality, vector queries at p95 < 50ms, autoscale RUs match bursty ingest |
| **Postgres Flexible Server** | `users`, `patients`, `encounters`, `notes`, `codes`, `audits`, `approvals` | ACID multi-row transactions on sign-off, FK integrity, row-level security policies, mature migrations (Alembic) |

### How they interact (transactional integrity rule)
Writes are **idempotent + eventually consistent** across the two stores. The pattern:
1. Postgres holds the *source of truth* for entity identity (encounter_id, note_id).
2. Cosmos rows reference Postgres ids but are written first (cheaper retry).
3. A Postgres write closes the transaction ("encounter committed").
4. Background reconciliation job verifies Cosmos rows for every committed Postgres encounter (catches dropped writes).

### Interview defense for this choice
> *"I split the data plane because vector search and audit-grade transactions have different consistency and cost profiles. Cosmos owns the append-mostly evidence and embedding layer where I need cheap vector queries and schema flexibility per modality. Postgres owns the relational audit and approval tier where I need ACID for sign-off and row-level security per clinician. I wrote a reconciliation job to catch the two-phase write failure mode. The polyglot cost is ~$60/mo extra, justified by clear separation of concerns and matching each workload to its native engine."*

### Cost impact
- Cosmos NoSQL serverless: ~$25–60/mo at portfolio scale
- Postgres B1ms: ~$30/mo
- **Total data tier: ~$55–90/mo** (up from $30 single-DB)
- Stays within the $250/mo overall ceiling.

### Required ADR
`docs/adr/0004-polyglot-persistence-cosmos-and-postgres.md` — must document the split, the consistency model, the reconciliation job, and explicitly state the alternative considered (Postgres-only with pgvector).

---

## Decision #2 — Authentication (Clerk)

**Final:** Clerk for end-user auth. Entra External ID listed on roadmap as a v2 migration.

### Interview defense for this choice
> *"I chose Clerk for v1 to compress time-to-first-deploy on the auth surface and focus engineering effort on the agentic core. The auth boundary is intentionally thin (JWT issuer + JWKS endpoint), so swapping to Entra External ID is a contained change — I documented the migration path in ADR-0005. For a production deployment targeting Azure-native identity, I'd move to Entra External ID for the workforce + free-tier MAU advantage; for the portfolio v1, Clerk shipped faster."*

### What we must build to keep this defensible
1. **Thin auth boundary**: FastAPI middleware reads any JWT issuer via JWKS — no Clerk-specific code in business logic.
2. **Roles modeled in our DB** (`users.role`), not in Clerk. Clerk only provides identity (`sub`, `email`, `oid`).
3. **Workforce Entra ID still used** for service-to-service auth via AKS workload identity (Azure resources don't see Clerk at all).
4. **ADR-0005**: `auth-clerk-with-entra-migration-path.md` — explicitly documents this is a v1 choice and lists the migration steps to Entra External ID.

### Cost impact
- Clerk free tier: 10,000 MAU (more than enough for a portfolio)
- $0/mo at portfolio scale; would be $25/mo at 10K+ MAU.

---

## 🟡 Caution (kept, but flagged) — 3 personas

You picked Clinician + Admin + Patient. That triples UI surface area:
- 3 dashboards
- 3 navigation models
- 3 permission tiers in RBAC
- 3 sets of e2e tests

**My take:** Keep all 3 because your timeline is open-ended **and** the Patient persona is what makes this look like a *product* rather than a *tech demo*. But we will ship them in order: Clinician (Phase 1–3) → Admin (Phase 4–5) → Patient (Phase 6). The Patient view will be deliberately minimal (read-only summary + sign-language-free plain-English version).

**Decision:** ✅ **3 personas, sequenced.**

---

## 🟢 Confirmed picks

| Question | Your pick | Verdict |
|---|---|---|
| Project | ClinicalScribe (multi-modal medical documentation) | ✅ Coherent, leverages Baxter healthcare background, multi-modal is hot |
| Timeline | Open-ended | ✅ Lets us hit the FAANG bar |
| Budget | $100–300/mo | ✅ Enough for AKS + AOAI + Search; we'll target the lower end |
| Framework | Microsoft Agent Framework (MAF) | ✅ You already use it at IBM, fastest start, strong MS signal |
| UI scope | Full SaaS-style product | ✅ Quality-over-speed mandates this |
| Open source | Public from day 1 | ✅ Recruiter discovery + GitHub stars compound over time |
| Specialty | General internal medicine | ✅ Largest synthetic corpus, broadest demo |
| Dataset | Public + LLM-generated synthetic | ✅ Best of both |
| First step | PRD + architecture doc before code | ✅ Senior move |
| Compute (deferred to me) | — | ✅ **AKS** — justified by budget + full-SaaS scope + adds K8s to resume. Sized small: 2× Standard_B2s system, 1× Standard_D2s_v5 user, cluster autoscaler 1–3. |

---

## Final stack (locked)

- **Frontend:** Next.js 15 (App Router) · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zustand · Clerk React SDK
- **Auth:** Clerk (end users, JWT) + Entra workforce ID via AKS workload identity (service-to-service to Azure resources)
- **Backend:** FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · uv · Python 3.12
- **Agents:** Microsoft Agent Framework (Python)
- **MCP:** `mcp` Python SDK — 4 servers (Medical KB, Drug Interaction, Coding, EHR Mock)
- **AI:** Azure OpenAI (gpt-4o + gpt-4o-mini + text-embedding-3-large) · Azure AI Speech · Azure Document Intelligence · Azure AI Content Safety (+ Prompt Shields)
- **Search:** Azure AI Search Basic (hybrid: BM25 + vector + semantic reranker)
- **Data:** **Azure Cosmos DB NoSQL** (evidence, embeddings, agent_runs, traces — vector queries) + **Azure Database for PostgreSQL Flexible Server** (users, encounters, notes, audits, approvals — transactional) · Azure Blob Storage · Azure Service Bus
- **Compute:** AKS (Terraform + Helm) · Azure Container Registry
- **IaC:** Terraform 1.9+ with `azurerm` + `azapi` providers; remote state in Azure Storage with native blob locking; per-env state via `-backend-config`; linted with tflint, scanned with tfsec + checkov; docs via terraform-docs
- **Edge:** Azure API Management (AI Gateway: semantic cache, token limits, content safety policy)
- **Ops:** OpenTelemetry → Application Insights · Azure Monitor · Azure Key Vault · Workload Identity
- **Eval:** Azure AI Evaluations SDK + Ragas + custom medical-correctness rubrics
- **CI/CD:** GitHub Actions (lint → type-check → unit → integration → eval-gate → build → push ACR → helm deploy)
- **Quality:** ruff · mypy strict · pytest · pytest-asyncio · eslint · vitest · playwright · pre-commit
- **Docs:** Docusaurus site + ADRs in repo

## Estimated monthly Azure cost (steady-state, low traffic)

| Service | SKU | Est. $/mo |
|---|---|---|
| AKS | 2× B2s system + 1× D2s_v5 user (autoscaled) | ~$70 |
| Azure OpenAI (gpt-4o-mini bulk + gpt-4o for drafts) | PAYG | ~$30 (controlled by APIM token limits + semantic cache) |
| Azure AI Search | Basic | ~$75 |
| Cosmos DB NoSQL (serverless or autoscale 1000 RU/s) | PAYG | ~$25–50 |
| PostgreSQL Flex | B1ms 32GB | ~$30 |
| Azure Speech | PAYG | ~$5 |
| Doc Intelligence | PAYG | ~$5 |
| Content Safety | PAYG | ~$2 |
| Blob + Service Bus + ACR + KV + App Insights | mixed | ~$15 |
| APIM | Consumption tier | ~$5 (or Developer ~$50 if needed) |
| Clerk | Free tier | $0 |
| **Total** | | **~$260–285/mo** (~$25–50 above the original estimate due to Cosmos addition; still within $300 ceiling) |

> Tactic: scale AKS to 0 user nodes overnight via cron; AI Search Basic is the biggest fixed cost — accept it, it's a portfolio centerpiece. We'll publish the cost dashboard in the README.
