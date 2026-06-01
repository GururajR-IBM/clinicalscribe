# ClinicalScribe — Architecture Document

**Status:** Draft v0.1 · awaiting approval
**Companion to:** `00-DECISIONS-REVIEW.md`, `01-PRD.md`

---

## 1. C4 — System context

```mermaid
flowchart LR
    DR[Dr. Patel<br/>Clinician]
    AD[Sarah<br/>Admin]
    PT[John Doe<br/>Patient]

    CS[ClinicalScribe<br/>Platform]

    EID[Entra External ID]
    AOAI[Azure OpenAI]
    SP[Azure Speech]
    DI[Doc Intelligence]
    CSAFE[Content Safety]
    AISR[Azure AI Search]
    OFDA[openFDA API]
    SNMD[SNOMED / RxNorm<br/>public terminology]

    DR -->|records encounter| CS
    AD -->|reviews metrics| CS
    PT -->|reads summary| CS
    CS --> EID
    CS --> AOAI
    CS --> SP
    CS --> DI
    CS --> CSAFE
    CS --> AISR
    CS --> OFDA
    CS --> SNMD
```

## 2. C4 — Container view

```mermaid
flowchart TB
    subgraph User["Browser"]
        WEB[Next.js 15 App<br/>React, TS, Tailwind, MSAL]
    end

    subgraph APIM["Azure API Management"]
        GW[AI Gateway Policies<br/>auth, rate limit, semantic cache,<br/>token limit, content safety]
    end

    subgraph AKS["AKS Cluster"]
        subgraph Pods["Application pods"]
            GATE[Gateway API<br/>FastAPI]
            ORC[Orchestrator<br/>FastAPI + MAF runtime]
            ING[Ingestion Worker<br/>Service Bus consumer]
            EVAL[Eval Runner<br/>scheduled CronJob]
        end
        subgraph MCPSidecars["MCP Sidecars / Pods"]
            MKB[Medical KB MCP]
            MDI[Drug Interaction MCP]
            MCD[Coding MCP]
            MEHR[EHR Mock MCP]
        end
        WI[Workload Identity]
    end

    subgraph Data["Data plane"]
        PG[(Postgres Flex<br/>+ pgvector)]
        BLOB[(Blob Storage<br/>encounter media)]
        SB[(Service Bus)]
        SRCH[(AI Search<br/>hybrid index)]
    end

    subgraph AI["Azure AI"]
        AOAI[Azure OpenAI<br/>gpt-4o, gpt-4o-mini,<br/>embedding-3-large]
        SPEECH[Speech Service]
        DOCI[Document Intelligence]
        CSF[Content Safety<br/>+ Prompt Shields]
    end

    subgraph Ops["Ops"]
        AI_INS[App Insights<br/>OTel collector]
        KV[Key Vault]
        ACR[Container Registry]
    end

    WEB <-->|HTTPS + SSE| GW
    GW <--> GATE
    GATE -->|publish job| SB
    SB --> ING
    ING --> BLOB
    ING --> SPEECH
    ING --> DOCI
    ING -->|enqueue agent run| SB
    SB --> ORC
    ORC --> MKB & MDI & MCD & MEHR
    ORC --> AOAI
    ORC --> SRCH
    ORC --> PG
    ORC --> CSF
    GATE --> PG
    GATE --> BLOB
    EVAL --> PG
    EVAL --> AOAI
    Pods -.uses.-> WI
    WI -.workload identity.-> AOAI & SRCH & PG & BLOB & KV
    Pods --> AI_INS
```

## 3. Agent topology (MAF)

```mermaid
flowchart TB
    SUP{{Supervisor}}
    TRN[Transcription Agent]
    EXT[Entity Extraction Agent]
    RET[Retrieval Agent]
    DRF[SOAP Drafter Agent]
    COD[Coder Agent]
    CRT{{Critic / Safety Agent}}

    SUP -->|after ingestion| TRN
    TRN --> EXT
    EXT --> RET
    RET --> DRF
    DRF --> COD
    COD --> CRT
    CRT -->|approve| SUP
    CRT -.->|revise N=2| DRF
```

**Tools per agent** (every tool is either an MCP call or a typed Python function exposed via MAF):

| Agent | Tools |
|---|---|
| Transcription | `medical_kb.lookup_term`, `medical_kb.normalize_drug_name` |
| Entity Extraction | `medical_kb.lookup_term`, structured JSON output (no tools) |
| Retrieval | `ai_search.hybrid_query`, `pgvector.find_similar_encounters`, `ehr_mock.get_patient_history` |
| SOAP Drafter | `pgvector.cite_evidence`, structured output |
| Coder | `coding.search_icd10`, `coding.search_cpt`, `coding.justify_code` |
| Critic | `content_safety.scan_output`, `drug_interaction.check_combo`, `medical_kb.verify_claim`, fact-grounding rubric |

## 4. Data model (Postgres)

```
users(id, entra_oid, role, email, created_at)
patients(id, external_ref, name_synthetic, dob, sex)
encounters(id, patient_id, clinician_id, status, created_at, signed_at)
attachments(id, encounter_id, kind, blob_url, byte_size, sha256)
evidence(id, encounter_id, source_attachment_id, span, modality, content, embedding vector(3072))
agent_runs(id, encounter_id, agent, parent_run_id, status, prompt_version, started_at, finished_at,
           prompt_tokens, completion_tokens, cost_usd, error)
notes(id, encounter_id, version, soap_json, citations_json, created_at, created_by)
codes(id, encounter_id, system, code, rationale, accepted bool)
audits(id, encounter_id, actor_id, action, before_json, after_json, at)
patient_messages(id, patient_id, encounter_id, body, sent_at)
```

All FK constrained. Row-level security via Postgres policies keyed on `clinician_id` / `patient_id`.

## 5. Key sequence — "Generate SOAP from encounter"

```mermaid
sequenceDiagram
    autonumber
    participant U as Clinician (Browser)
    participant GW as Gateway API
    participant SB as Service Bus
    participant ING as Ingestion Worker
    participant ORC as Orchestrator (MAF)
    participant AOAI as Azure OpenAI
    participant SRCH as AI Search
    participant CSF as Content Safety
    participant PG as Postgres

    U->>GW: POST /encounters (audio + attachments uploaded to Blob)
    GW->>PG: insert encounter, attachments
    GW->>SB: publish ingest.requested
    GW-->>U: 202 + SSE channel
    SB->>ING: consume
    ING->>AOAI: Speech transcribe (medical)
    ING->>AOAI: Doc Intelligence + GPT-4o vision
    ING->>PG: write evidence rows + embeddings
    ING->>SB: publish agentrun.requested
    SB->>ORC: consume
    ORC->>CSF: Prompt Shield on user-derived content
    loop per agent in topology
        ORC->>AOAI: LLM call (with tools)
        AOAI-->>ORC: tool calls
        ORC->>SRCH: hybrid query (if Retrieval)
        ORC->>PG: persist agent_run + tokens + cost
        ORC-->>GW: SSE progress event
        GW-->>U: SSE event
    end
    ORC->>CSF: scan final draft
    ORC->>PG: insert notes (version=1, status=draft)
    ORC-->>GW: SSE complete
    GW-->>U: render draft + citations
```

## 6. Safety model (summary)

Three layers, defense in depth:

1. **Input layer** — Prompt Shields on anything user-derived, file scanning on uploads, schema validation on every external response.
2. **Reasoning layer** — Critic agent runs after every draft; tool-level hard stops (drug interactions); citation enforcement (every SOAP sentence must reference an Evidence id).
3. **Output layer** — Content Safety on outbound text, PII redaction for patient persona, mandatory clinician sign-off before any artifact is "final," append-only audit log.

Full doc in `docs/safety-model.md` once we start the repo.

## 7. Repository layout (final)

```
clinicalscribe/
├── apps/
│   ├── web/                    # Next.js SaaS UI (3 personas)
│   └── docs-site/              # Docusaurus
├── services/
│   ├── gateway/                # FastAPI public API
│   ├── orchestrator/           # MAF runtime
│   ├── ingestion-worker/       # Service Bus consumer
│   └── eval-runner/            # CronJob / GH Action
├── mcp-servers/
│   ├── medical-kb/
│   ├── drug-interaction/
│   ├── coding/
│   └── ehr-mock/
├── packages/
│   ├── schemas-py/             # Pydantic models, shared across services
│   ├── schemas-ts/             # Generated from OpenAPI for the web app
│   └── prompts/                # Versioned Jinja prompts, prompt registry
├── infra/
│   ├── terraform/
│   │   ├── backend.tf              # Azure Storage remote state (blob locking)
│   │   ├── providers.tf            # azurerm + azapi
│   │   ├── main.tf                 # composes modules
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── environments/
│   │   │   ├── dev.tfvars
│   │   │   ├── dev.backend.hcl
│   │   │   ├── prod.tfvars
│   │   │   └── prod.backend.hcl
│   │   └── modules/
│   │       ├── network/        # vnet, subnets, NSGs, private endpoints
│   │       ├── aks/            # cluster, node pools, workload identity
│   │       ├── data/           # cosmos, postgres flex, blob
│   │       ├── ai/             # aoai, speech, doc-intel, content-safety
│   │       ├── search/         # ai search
│   │       ├── messaging/      # service bus
│   │       ├── observability/  # app insights, log analytics
│   │       └── apim/           # ai gateway
│   │   bootstrap/                  # one-time: creates the state-backend storage account
│   └── helm/
│       ├── gateway/
│       ├── orchestrator/
│       ├── ingestion/
│       └── mcp-*/
├── evals/
│   ├── datasets/golden/        # 50 synthetic encounters
│   ├── runners/
│   └── reports/
├── scripts/
│   ├── seed-search-index.py    # CDC/NIH guidelines
│   ├── synth-encounters.py     # LLM-driven synthetic data
│   └── cost-report.py
├── .github/workflows/
│   ├── ci.yml
│   ├── eval-gate.yml
│   ├── cd-dev.yml
│   └── cd-prod.yml
├── docs/
│   ├── adr/
│   │   ├── 0001-architecture.md
│   │   ├── 0002-safety-model.md
│   │   ├── 0003-agent-topology.md
│   │   ├── 0004-polyglot-persistence-cosmos-and-postgres.md
│   │   ├── 0005-auth-clerk-with-entra-migration-path.md
│   │   └── 0006-iac-terraform.md
│   ├── architecture.md
│   ├── safety-model.md
│   ├── demo.md
│   └── images/
├── LICENSE                     # MIT, with explicit "not for clinical use" rider
├── README.md
└── SECURITY.md
```

## 8. Environments

| Env | Where | Purpose |
|---|---|---|
| `local` | Docker Compose | All services + Postgres + Azurite + a fake AOAI proxy |
| `dev` | AKS in `cs-dev-rg` | Continuous deploy from `main` |
| `prod` | AKS in `cs-prod-rg` | Deploy on tagged release |

## 9. CI/CD pipeline

```
PR opened ─► lint ─► type-check ─► unit ─► integration
          ─► terraform fmt + validate + tflint + tfsec + checkov
          ─► eval-gate (smoke 5 cases) ─► allow merge
main merged ─► full eval (50 cases)
            ─► terraform plan against dev (artifact uploaded for review)
            ─► terraform apply dev (auto, with state lock)
            ─► build + push images ─► helm upgrade dev ─► smoke e2e ─► notify
tag v* ─► gates as above
       ─► terraform plan against prod (MANUAL approval gate via GH Environments)
       ─► terraform apply prod
       ─► helm upgrade prod ─► canary 10% 30min ─► full rollout
```

**Auth from GitHub Actions to Azure:** Workload Identity Federation (OIDC) — no service principal secrets in GitHub. Federated credential per environment.

## 10. Open questions (need your call before Phase 0)

| # | Question | Default if you don't answer |
|---|---|---|
| Q1 | Repo location — create the new repo at `c:\Working\clinicalscribe\` or alongside existing at `c:\Working\RAGwithAzureOpenAI\clinicalscribe\`? | New folder `c:\Working\clinicalscribe\` |
| Q2 | GitHub org/account — push to your personal `github.com/<your-user>/clinicalscribe`? | Yes, personal account |
| Q3 | Azure subscription — do you already have one allocated for this, or do we set up a fresh resource group? | New RG `cs-dev-rg` in `eastus2` |
| Q4 | Should we host the Docusaurus site on **GitHub Pages** or **Azure Static Web Apps**? | GitHub Pages (free, simpler) |
| Q5 | Demo data: any specific medical scenario you want as the headline demo (e.g., "60yo with T2DM and hypertension annual visit")? | Yes, that exact scenario as canonical demo |
| Q6 | License — MIT with non-clinical-use disclaimer OK, or do you prefer Apache 2.0 / AGPL? | MIT + disclaimer |
