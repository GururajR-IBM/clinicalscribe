# ClinicalScribe — Azure Services Checklist

**Status:** Final · 2026-06-01
**Purpose:** Single source of truth for every Azure resource. Includes recommended SKU, est. monthly cost, which phase introduces it, and ready-to-run `az` CLI commands. **You will create these manually only if Terraform fails or for the one-time bootstrap.** Otherwise, Terraform handles creation.

---

## Resource group + naming convention

| Item | Value |
|---|---|
| **Subscription** | (yours — to be confirmed) |
| **Resource Group (dev)** | `rg-clinicalscribe-dev-eastus2` |
| **Resource Group (prod)** | `rg-clinicalscribe-prod-eastus2` |
| **Region (primary)** | `eastus2` (best AOAI + Speech availability) |
| **Naming convention** | `<type>-clinicalscribe-<env>-<region>-<suffix>` |
| **Required tags** | `project=clinicalscribe`, `env=dev|prod`, `owner=gururaj`, `costcenter=portfolio` |

> ⚠️ **Region check first:** Confirm `eastus2` has quota for `gpt-4o`, `gpt-4o-mini`, `text-embedding-3-large`, and `aks` D2s_v5. Fall back to `eastus` or `swedencentral` if not.

---

## A1 — Azure Storage (Terraform state backend) · **Phase 0** · One-time manual

**Purpose:** Stores Terraform state files with native blob locking (Terraform 1.11+).

| Field | Value |
|---|---|
| Resource type | Storage Account (StorageV2, GRS, LRS for dev) |
| Name | `sttfstateclinscbe` (3–24 chars, lowercase, no hyphens) |
| SKU | `Standard_LRS` (dev), `Standard_GRS` (prod state) |
| Containers | `tfstate-dev`, `tfstate-prod` |
| Public access | **Disabled** |
| Versioning | **Enabled** (critical — state corruption recovery) |
| Soft delete | 30 days |
| Est. cost | ~$1/mo |

```powershell
az group create -n rg-clinicalscribe-bootstrap -l eastus2
az storage account create -n sttfstateclinscbe -g rg-clinicalscribe-bootstrap -l eastus2 `
  --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false `
  --min-tls-version TLS1_2
az storage account blob-service-properties update --account-name sttfstateclinscbe `
  --enable-versioning true --enable-delete-retention true --delete-retention-days 30
az storage container create -n tfstate-dev --account-name sttfstateclinscbe --auth-mode login
az storage container create -n tfstate-prod --account-name sttfstateclinscbe --auth-mode login
```

---

## Entra ID — App registration for GitHub Actions OIDC · **Phase 0** · One-time manual

**Purpose:** Federated identity from GitHub Actions to Azure — no client secrets stored in GitHub.

| Field | Value |
|---|---|
| App name | `gh-clinicalscribe-oidc` |
| Federated credentials | Per env: `repo:GururajR-IBM/clinicalscribe:environment:dev`, `…:environment:prod`, `…:ref:refs/heads/main`, `…:pull_request` |
| RBAC | `Contributor` + `User Access Administrator` on each RG (scope-limited) |

```powershell
# Create the app + service principal
az ad app create --display-name gh-clinicalscribe-oidc
$APP_ID = az ad app list --display-name gh-clinicalscribe-oidc --query "[0].appId" -o tsv
az ad sp create --id $APP_ID

# Add federated credential for main branch
az ad app federated-credential create --id $APP_ID --parameters '{
  \"name\": \"main-branch\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:GururajR-IBM/clinicalscribe:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}'
# Repeat for env:dev, env:prod, pull_request
```

Add these as **GitHub repo secrets**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (no secret needed for the SP itself — that's the point of OIDC).

---

# Resources provisioned via Terraform (by phase)

> All resources below are created by `terraform apply`. The `az` commands here are for **manual fallback / debugging only**.

## A2 — Virtual Network · **Phase 0**

| Field | Value |
|---|---|
| Type | `Microsoft.Network/virtualNetworks` |
| Name | `vnet-clinicalscribe-dev-eastus2` |
| Address space | `10.20.0.0/16` |
| Subnets | `snet-aks` (10.20.0.0/22), `snet-data` (10.20.4.0/24 — private endpoints), `snet-apim` (10.20.5.0/27) |
| Est. cost | $0 (VNet itself is free; private endpoints ~$7/mo each — kept to data tier only) |
| Terraform module | `Azure/avm-res-network-virtualnetwork/azurerm` |

---

## A3 — AKS · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.ContainerService/managedClusters` |
| Name | `aks-clinicalscribe-dev-eastus2` |
| K8s version | `1.30.x` (latest stable) |
| System pool | 2× `Standard_B2s` (cost-optimized) |
| User pool | 1–3× `Standard_D2s_v5` (cluster autoscaler) |
| Network plugin | Azure CNI Overlay |
| Identity | System-assigned managed identity + **Workload Identity enabled** |
| OIDC issuer | **Enabled** (required for workload identity) |
| Add-ons | Azure Monitor for containers, Key Vault Secrets Provider |
| Est. cost | ~$70/mo (with overnight scale-to-zero of user pool: ~$45/mo) |
| Terraform module | `Azure/avm-res-containerservice-managedcluster/azurerm` |

---

## A4 — Container Registry · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.ContainerRegistry/registries` |
| Name | `acrclinicalscribedev` (no hyphens, lowercase) |
| SKU | `Basic` (10 GB included, sufficient for portfolio) |
| Admin user | **Disabled** (use workload identity to pull) |
| AKS attach | `az aks update --attach-acr` |
| Est. cost | ~$5/mo |

---

## A5 — Azure OpenAI · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.CognitiveServices/accounts` kind `OpenAI` |
| Name | `aoai-clinicalscribe-dev-eastus2` |
| SKU | `S0` |
| Deployments | `gpt-4o` (Standard, 30K TPM), `gpt-4o-mini` (Standard, 200K TPM), `text-embedding-3-large` (Standard, 350K TPM) |
| Auth | Microsoft Entra ID only (no keys) — workload identity from AKS |
| Networking | Public for dev; private endpoint for prod |
| Est. cost | Phase 1–5: ~$30/mo (semantic cache in Phase 6 cuts ~40%) |

**Pre-check quota:**
```powershell
az cognitiveservices usage list -l eastus2 -o table
```

---

## A6 — Postgres Flexible Server · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.DBforPostgreSQL/flexibleServers` |
| Name | `pg-clinicalscribe-dev-eastus2` |
| Version | PostgreSQL 16 |
| SKU | `Standard_B1ms` Burstable, 32 GB storage |
| HA | Disabled in dev, Zone-Redundant in prod |
| Auth | Entra ID only (no password auth) |
| Extensions | `pgcrypto`, `pg_trgm`, `uuid-ossp` (NOT pgvector — Cosmos owns vectors per ADR-0004) |
| Networking | Private endpoint on `snet-data` |
| Backup | 7 days dev, 35 days prod |
| Est. cost | ~$30/mo |

---

## A7 — Cosmos DB NoSQL · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.DocumentDB/databaseAccounts` kind `GlobalDocumentDB` |
| Name | `cosmos-clinicalscribe-dev-eastus2` |
| Capacity mode | **Serverless** in dev, Autoscale 1000 RU/s in prod |
| Consistency | Session |
| Database | `clinicalscribe` |
| Containers | `evidence` (partition `/encounterId`), `embeddings` (partition `/encounterId`, vector index on `/vector`), `agent_runs` (partition `/encounterId`), `traces` (partition `/traceId`) |
| Vector indexing policy | `text-embedding-3-large` → 3072 dims, `quantizedFlat` for embeddings container |
| Networking | Private endpoint on `snet-data` for prod |
| Est. cost | Dev: ~$25/mo. Prod: ~$60/mo |

---

## A8 — Blob Storage · **Phase 1**

| Field | Value |
|---|---|
| Type | Storage Account (StorageV2) |
| Name | `stclinscbedev` |
| SKU | `Standard_LRS` dev, `Standard_ZRS` prod |
| Containers | `encounter-media` (private), `eval-artifacts` (private) |
| Lifecycle | Move to Cool after 30 days, delete after 90 days (dev) |
| CORS | Allow `https://*.clinicalscribe.<your-domain>` for signed URL uploads |
| Est. cost | ~$3/mo at portfolio volume |

---

## A9 — Key Vault · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.KeyVault/vaults` |
| Name | `kv-clinscbe-dev-eu2` (max 24 chars) |
| SKU | `standard` |
| RBAC | Enabled (no access policies) |
| Soft delete | 90 days |
| Networking | Private endpoint in prod |
| Secrets | `clerk-jwks-url`, `clerk-jwt-issuer`, `openfda-api-key`, `eval-runner-token` |
| Est. cost | ~$1/mo |

---

## A10 — Application Insights + Log Analytics · **Phase 1**

| Field | Value |
|---|---|
| Log Analytics workspace | `log-clinicalscribe-dev-eastus2` |
| App Insights | `appi-clinicalscribe-dev-eastus2` (workspace-based) |
| Retention | 30 days dev, 90 days prod |
| Daily cap | 1 GB/day dev (cost guard) |
| Est. cost | ~$5–10/mo |

---

## A11 — Azure AI Speech · **Phase 1**

| Field | Value |
|---|---|
| Type | `Microsoft.CognitiveServices/accounts` kind `SpeechServices` |
| Name | `speech-clinicalscribe-dev-eastus2` |
| SKU | `S0` |
| Models used | Conversation transcription (medical conversation preset if available in region; else standard + custom vocabulary) |
| Auth | Entra ID, workload identity from AKS |
| Est. cost | ~$5/mo at low volume (~10 encounters/day @ 5 min) |

---

## A12 — Azure AI Search · **Phase 2**

| Field | Value |
|---|---|
| Type | `Microsoft.Search/searchServices` |
| Name | `srch-clinicalscribe-dev-eastus2` |
| SKU | `basic` (1 replica, 1 partition — 2 GB storage) |
| Semantic ranker | **Enabled** (free up to 1000 queries/mo on Basic) |
| Indexes | `medical-guidelines` (text + vector hybrid, semantic config) |
| Vector dims | 3072 (matches `text-embedding-3-large`) |
| Auth | Entra ID, workload identity |
| Est. cost | ~$75/mo (largest fixed cost — accept it, it's a portfolio centerpiece) |

---

## A13 — Service Bus · **Phase 2**

| Field | Value |
|---|---|
| Type | `Microsoft.ServiceBus/namespaces` |
| Name | `sb-clinicalscribe-dev-eastus2` |
| SKU | `Standard` (required for topics; we use queues but Standard is cheapest with private endpoint) |
| Queues | `ingest.requested`, `agentrun.requested`, `agentrun.completed`, `eval.requested` (max delivery count 5, DLQ enabled) |
| Auth | Entra ID, workload identity |
| Est. cost | ~$10/mo |

---

## A14 — Azure Document Intelligence · **Phase 3**

| Field | Value |
|---|---|
| Type | `Microsoft.CognitiveServices/accounts` kind `FormRecognizer` |
| Name | `di-clinicalscribe-dev-eastus2` |
| SKU | `S0` |
| Models used | `prebuilt-layout`, `prebuilt-document` (no custom model in v1) |
| Auth | Entra ID |
| Est. cost | ~$5/mo |

---

## A15 — Azure AI Content Safety · **Phase 4**

| Field | Value |
|---|---|
| Type | `Microsoft.CognitiveServices/accounts` kind `ContentSafety` |
| Name | `cs-clinicalscribe-dev-eastus2` |
| SKU | `S0` |
| Features used | Text moderation, Prompt Shields, Groundedness detection |
| Est. cost | ~$2/mo |

---

## A16 — Azure AI Foundry project · **Phase 5**

| Field | Value |
|---|---|
| Type | `Microsoft.MachineLearningServices/workspaces` kind `Project` (under a hub) + AI Foundry Hub |
| Hub name | `hub-clinicalscribe-eastus2` |
| Project name | `proj-clinicalscribe-evals` |
| Used for | Azure AI Evaluations dashboards + dataset versioning + trace inspection |
| Est. cost | ~$0 (free; storage + AI services already billed elsewhere) |

---

## A17 — APIM (AI Gateway) · **Phase 6**

| Field | Value |
|---|---|
| Type | `Microsoft.ApiManagement/service` |
| Name | `apim-clinicalscribe-dev-eastus2` |
| SKU | `Consumption` (~$0 fixed, pay-per-call); upgrade to `Developer` (~$50/mo) if you need built-in dev portal |
| Backend | Azure OpenAI |
| Policies | `azure-openai-token-limit`, `azure-openai-emit-token-metric`, `azure-openai-semantic-cache-lookup`, `azure-openai-semantic-cache-store`, `llm-content-safety` |
| Auth | Workload identity to AOAI backend |
| Est. cost | ~$5/mo (Consumption) |

---

# Cost summary by phase (steady-state, dev only)

| Phase | New monthly cost | Cumulative |
|---|---|---|
| Phase 0 | $1 (state storage) | $1 |
| Phase 1 | +$140 (AKS, ACR, AOAI, PG, Cosmos, Blob, KV, App Insights, Speech) | ~$141 |
| Phase 2 | +$90 (AI Search Basic + Service Bus + extra AOAI from embeddings) | ~$231 |
| Phase 3 | +$5 (Doc Intelligence) | ~$236 |
| Phase 4 | +$2 (Content Safety) | ~$238 |
| Phase 5 | +$0 (AI Foundry free; some extra App Insights) | ~$240 |
| Phase 6 | +$5 / -$15 (APIM +$5, semantic cache saves ~$15 on AOAI) | **~$230** |

**Tactics to stay below $200:**
- AKS user pool scale-to-zero overnight (cron) → -$25/mo
- AI Search Basic is the biggest fixed cost — accept it (centerpiece of RAG story)
- Cosmos serverless in dev (vs autoscale in prod) → -$30/mo
- AOAI semantic cache (Phase 6) → -$15/mo

---

# Pre-flight checks before you click "create"

When you reach the resource-creation step:

```powershell
# 1. Confirm subscription
az account show --query "{subscription: name, id: id, tenant: tenantId}" -o table

# 2. Check region quotas (especially AOAI models)
az cognitiveservices usage list -l eastus2 -o table | Select-String "gpt-4o|embedding"

# 3. Check AKS VM SKU availability in region
az vm list-skus -l eastus2 --size Standard_D2s_v5 --query "[?capabilities[?name=='CapacityReservationSupported']]" -o table

# 4. Confirm subscription has the needed providers registered
az provider list --query "[?registrationState=='Registered'].namespace" -o tsv | Select-String "ContainerService|CognitiveServices|DocumentDB|DBforPostgreSQL|KeyVault|Search|ServiceBus|ApiManagement|Insights|Storage|Network|MachineLearningServices"

# 5. Set a $10/day budget alert immediately (do this BEFORE Phase 1!)
az consumption budget create --budget-name budget-clinicalscribe-dev `
  --amount 300 --time-grain Monthly --resource-group rg-clinicalscribe-dev-eastus2 `
  --start-date 2026-06-01 --end-date 2027-06-01
```

---

# What you DO NOT need (explicit non-list)

To prevent scope creep:

- ❌ **Azure Front Door / CDN** — single region, AKS Ingress is enough
- ❌ **Azure Firewall** — overkill for portfolio; NSGs + private endpoints suffice
- ❌ **Azure DevOps** — using GitHub Actions
- ❌ **Azure Functions** — workloads fit AKS pods cleanly
- ❌ **Azure Cache for Redis** — APIM semantic cache covers the LLM caching need; nothing else needs Redis at this scale
- ❌ **Azure Bastion** — kubectl + AAD auth doesn't need it
- ❌ **Azure Backup vaults** — Postgres + Cosmos + Blob have built-in backup; that's enough
- ❌ **Azure Synapse / Fabric** — eval datasets fit in Blob + Postgres
- ❌ **Defender for Cloud (paid plans)** — free tier is enough for portfolio

If any of these come up in a design conversation, the answer is "documented as out of scope for v1."
