terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  # Backend config is intentionally empty — values are injected at `terraform init`
  # via `-backend-config=environments/<env>.backend.hcl`. This keeps the same code
  # path for dev / prod and prevents accidental cross-env state writes.
  backend "azurerm" {
    use_azuread_auth = true
  }
}
