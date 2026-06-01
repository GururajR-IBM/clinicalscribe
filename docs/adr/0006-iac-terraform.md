# 0006 — Terraform (not Bicep) for IaC

- **Status:** Stub (Phase 0). Regenerate with Claude Opus 4.7 before external review.
- **Date:** 2025
- **Deciders:** Gururaj Raibagi

## Context

ClinicalScribe is single-cloud (Azure) but the target audience for this repo includes
FAANG-style platform interviews. Bicep is Azure-native; Terraform is the industry default
for multi-cloud and is what most senior platform roles ask about.

## Decision

Use **Terraform 1.10+** with the `azurerm` and `azapi` providers. Wrap **Azure Verified
Modules (AVM)** where they exist; fall back to direct resources when AVM is missing or
significantly behind.

State lives in an Azure Storage account created by a one-time `bootstrap/` config. The main
config has an empty backend block; values are injected at `init` time via
`-backend-config=environments/<env>.backend.hcl`. Per-env tfvars hold the rest. Native
blob lease locking is used (no separate DynamoDB-style locking is needed).

## Consequences

+ Transferable skill set; clearer signal in interviews.
+ AVM still gives Microsoft-blessed defaults where they exist.
+ State backend pattern is auditable and tamper-resistant (RBAC + AAD auth on the storage account).
− Azure-specific resources sometimes lag in `azurerm`; mitigation = `azapi` provider for new APIs.
− Slightly more boilerplate than Bicep; accepted as the cost of portability.
