# Terraform · ClinicalScribe

Per-environment Terraform configuration. Wraps Azure Verified Modules (AVM) and adds
ClinicalScribe-specific composition (network, AKS, data, search, AI, messaging, APIM).

## Layout

```
infra/terraform/
├── bootstrap/         # one-time: create the state storage account itself
├── environments/      # per-env tfvars + backend configs (gitignored except .example)
├── modules/           # composition modules wrapping AVM
├── backend.tf         # backend "azurerm" {} declaration (config injected via -backend-config)
├── providers.tf       # azurerm + azapi
├── variables.tf       # input contract
├── main.tf            # module wiring
└── outputs.tf         # exported values (consumed by GH Actions)
```

## Workflow

```powershell
# one-time per env
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap apply

# normal flow
terraform -chdir=infra/terraform init -backend-config=environments/dev.backend.hcl
terraform -chdir=infra/terraform plan  -var-file=environments/dev.tfvars
terraform -chdir=infra/terraform apply -var-file=environments/dev.tfvars
```

> **Phase 0:** these are scaffolding stubs. Real resources land in Phase 1 (network + AKS +
> Postgres + Cosmos + Key Vault) and following phases. Subscription provisioning is **paused**
> pending the user's IBM-vs-personal subscription decision.
