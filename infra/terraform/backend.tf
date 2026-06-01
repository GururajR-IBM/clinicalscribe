terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  # ── Backend strategy ──────────────────────────────────────────────────
  # Lab / sandbox subscriptions (e.g. Microsoft Learn MOC): use LOCAL state.
  #   - No dependency on an Azure storage account that dies with the lab.
  #   - Back the state file up with `scripts/Backup-AzureContext.ps1` before
  #     switching accounts.
  #
  # Personal PAYG / shared dev / prod: enable the Azure backend below and run:
  #   terraform init -migrate-state -backend-config=environments/dev.backend.hcl
  #
  # The backend block is intentionally empty so values flow from -backend-config.

  # backend "azurerm" {
  #   use_azuread_auth = true
  # }
}
