# scripts

Operational helpers for ClinicalScribe.

## `Switch-AzureAccount.ps1`

Pick (or login to) an Azure account and pin it for this repo. Writes
`azure-context.local.json` (gitignored) so other tooling knows the current
profile, subscription, tenant, and user.

```powershell
pwsh ./scripts/Switch-AzureAccount.ps1 -Profile lab
pwsh ./scripts/Switch-AzureAccount.ps1 -Profile dev
```

Profiles:

| Profile | When to use | Backend | Notes |
| ------- | ----------- | ------- | ----- |
| `lab`   | Microsoft Learn / MOC sandbox subs | local tfstate | Subscription expires; back up before it dies |
| `dev`   | Personal PAYG dev sub | Azure Storage (after bootstrap) | Long-lived |
| `prod`  | Personal PAYG prod sub | Azure Storage (after bootstrap) | Long-lived |

## `Backup-AzureContext.ps1`

Snapshot everything needed to remember what's deployed **before** you lose
access to a subscription. Run this at end of every lab session.

```powershell
pwsh ./scripts/Backup-AzureContext.ps1
```

Outputs to `backups/<utc-timestamp>/`:

- `state/` — copies of all local `terraform.tfstate*` files
- `azure/account-show.json` — active account JSON
- `azure/resource-groups.json` — all RGs in the sub
- `azure/resources.json` — every resource in the sub
- `azure-context.local.json` — the active profile pin
- `SUMMARY.md` — human-readable overview

The whole `backups/` folder is gitignored. Copy it somewhere safe (OneDrive,
external drive, etc.) before the sub expires.

## Migrating from `lab` → `dev` later

When you get a real PAYG sub:

1. Run `pwsh ./scripts/Backup-AzureContext.ps1` while still on lab.
2. Run `pwsh ./scripts/Switch-AzureAccount.ps1 -Profile dev`.
3. Edit `infra/terraform/backend.tf` — uncomment the `backend "azurerm" {}` block.
4. Run `terraform -chdir=infra/terraform/bootstrap apply` to create the state SA.
5. Run `terraform -chdir=infra/terraform init -migrate-state -backend-config=environments/dev.backend.hcl`.
6. `terraform apply -var-file=environments/dev.tfvars` against the new account.

Resource definitions stay identical; only state location and account change.
