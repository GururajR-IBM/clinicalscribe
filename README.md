# ClinicalScribe

> **Status:** Phases 0–6 implemented (services + Helm + IaC). `terraform apply` is gated behind opt-in (all module blocks commented in `infra/terraform/main.tf`).

**ClinicalScribe** is an open-source, **multi-agent, multi-modal medical documentation platform** built on Azure. It turns a doctor–patient encounter (audio + scanned labs + vitals photos) into a structured SOAP note, suggested ICD-10/CPT codes, drug-interaction warnings, and a plain-English patient summary — with **mandatory clinician sign-off**, **end-to-end citations**, and a **full safety + eval stack**.

This repo is a reference architecture for production-grade **agentic AI on Azure**, designed as a portfolio piece demonstrating senior-level engineering across the modern AI stack.

---

## Bring-your-own LLM (BYO-AOAI)

This stack does **not** provision an Azure OpenAI resource. Point the services at any AOAI account (in any subscription) via environment variables — no Terraform module is created for AOAI, and the orchestrator silently degrades to stub data when the key is absent so local dev still boots cleanly.

```bash
# Required for live runs
AOAI_ENDPOINT=https://<your-aoai-account>.openai.azure.com
AOAI_KEY=<your-key>

# Optional overrides (defaults are the cheapest models)
AOAI_DRAFT_MODEL=gpt-4o-mini
AOAI_REVIEW_MODEL=gpt-4o-mini          # bump to gpt-4o for prod
AOAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dims, matches the index
AOAI_WHISPER_DEPLOYMENT=whisper        # ingestion-worker only
```

---

## Cost posture (idle deployment)

All Terraform defaults target the cheapest viable SKU per service:

| Service | Default SKU | ~$/mo idle |
|---|---|---|
| Cosmos DB | **Serverless** (pay per RU) | ~$0–5 |
| Postgres Flexible | _disabled_ -- SQLite file used instead | $0 |
| AI Search | `basic` (1 replica) | ~$75 |
| APIM | `Consumption_0` | ~$0 (pay per call) |
| Storage | LRS, StandardV2 | ~$1 |
| Log Analytics | PerGB2018, 30-day retention | ~$0 idle |
| Container Registry | Basic | ~$5 |
| Container Apps | Consumption, scale-to-zero | ~$0 idle |
| AKS | not provisioned by Terraform | — |

Bring-your-own AOAI sits outside this stack. AI Search basic dominates the bill; comment out that module and use Postgres + `pgvector` for sub-$30/mo total. Switch Cosmos to autoscale only above ~3 M RU/day per container.

**Laptop / lab DB:** SQLite (via `aiosqlite`) is the default, kept in `./clinicalscribe.db`. Zero infra, no network surface, FIPS-validatable, HIPAA-compatible on encrypted disk — the right call for a work laptop and for compliance-bound demos. Provision the Terraform `postgres` module only if you outgrow it; just flip `DATABASE_URL` to a Postgres URI and apply the Alembic migrations under `db/`.

---

## Compute plane: Azure Container Apps

All 9 services (gateway, orchestrator, ingestion-worker, eval-runner, 4 MCP servers, web) run on **Azure Container Apps** with scale-to-zero. The `container_apps` Terraform module provisions:

- **Azure Container Registry** (Basic SKU, ~$5/mo) for images
- **Container Apps Environment** wired to Log Analytics
- One **user-assigned managed identity** shared by every app, granted `AcrPull` on the registry and `Key Vault Secrets User` on the vault (secrets injected via `secret_env`)
- Nine **Container Apps**, `min_replicas = 0`, internal DNS for everything except `gateway` + `web`

Build + push images (one tag for all services):
```powershell
.\scripts\containers\build-and-push.ps1 -AcrName <acr-name> -Tag <git-sha>
terraform -chdir=infra/terraform apply -var image_tag=<git-sha>
```

Helm charts in `infra/helm/` remain for the AKS path if you ever need it.

---

## Why this exists

US primary-care physicians spend ~2 hours on documentation for every 1 hour of patient care. Commercial AI scribes exist but are closed and opaque. ClinicalScribe is the open, auditable, **engineer-friendly** counterpart — a system you can fork, study, deploy, and extend.

> ⚠️ **Not for clinical use.** This is a portfolio / research project. Uses synthetic data only. See [LICENSE](LICENSE) for the explicit non-clinical-use rider.

---

## What it demonstrates

| Capability | Implementation |
|---|---|
| **Multi-agent orchestration** | 7-agent topology on **Microsoft Agent Framework (MAF)** with Supervisor + Critic reflection loop |
| **MCP servers** | 4 custom Model Context Protocol servers (Medical KB, Drug Interaction, ICD/CPT Coding, FHIR EHR Mock) |
| **Multi-modal ingestion** | Audio → Azure AI Speech / Whisper |
| **Hybrid RAG** | Azure AI Search (BM25 + vector + semantic reranker) over CDC/NIH/USPSTF guidelines |
| **Polyglot persistence** | Cosmos DB NoSQL (agent telemetry + vectors) + Postgres (transactional + audit + RBAC) |
| **Safety stack** | OWASP A03 system-prompt isolation, drug-interaction hard-stops, citation enforcement, Critic redraft loop |
| **Eval harness** | 5-dimension LLM-judge rubric against a golden dataset, gating PR merges in CI |
| **Observability** | Structlog JSON + per-agent token/cost spans → Cosmos `traces` + LAW (when wired) |
| **Production infra** | Terraform (azurerm) + Helm charts per service |
| **AI Gateway** | Azure API Management Consumption tier with Clerk JWT validation + rate limit |

---

## Architecture (high level)

See [docs/planning/02-ARCHITECTURE.md](docs/planning/02-ARCHITECTURE.md) for full diagrams.

```
Browser → APIM → FastAPI Gateway → Service Bus → Orchestrator (MAF)
                                                       ↓
   ┌───────────────────────────────────────────────────┴────────────────────┐
   │  Supervisor → Transcription → Entity Extraction → Retrieval            │
   │             → SOAP Drafter → Coder → Drug Interaction → Critic         │
   └────────────────────────────────────────────────────────────────────────┘
                              ↓                  ↓                ↓
                       MCP Servers       Azure AI Search    Cosmos + Postgres
                       (4 sidecars)         (hybrid KB)        (polyglot)
```

---

## Stack

**Frontend** Next.js 15 · TypeScript · Tailwind · shadcn/ui · TanStack Query · Clerk
**Backend** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · uv
**Agents** Custom MAF-style supervisor · MCP Python SDK
**AI (BYO)** Azure OpenAI (gpt-4o-mini default · text-embedding-3-small · whisper)
**Data** Azure Cosmos DB NoSQL (serverless) · PostgreSQL Flexible Server · Azure AI Search · Blob Storage
**Infra** Terraform (azurerm + azapi) · Helm
**Ops** Structlog · OpenTelemetry-style spans · APIM Consumption AI Gateway
**Quality** ruff · mypy · pytest · eslint · playwright · tflint

---

## Repository layout

```
clinicalscribe/
├── apps/                # Next.js web app
├── services/            # FastAPI services: gateway, orchestrator, ingestion-worker, eval-runner
├── mcp-servers/         # 4 Model Context Protocol servers
├── packages/            # Shared schemas + prompts
├── db/                  # Alembic migrations for Postgres
├── infra/
│   ├── terraform/       # All Azure infrastructure (modules + per-env config)
│   └── helm/            # Helm charts per service
├── scripts/             # Azure account switch + AI Search index deploy
└── docs/
    ├── adr/             # Architecture Decision Records
    └── planning/        # Initial planning docs
```

---

## License

MIT, with explicit **not for clinical use** rider. See [LICENSE](LICENSE).
