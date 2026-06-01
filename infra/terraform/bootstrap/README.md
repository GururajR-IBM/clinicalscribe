# Bootstrap

One-time, **local-state** Terraform that creates the Azure Storage account used
as the remote backend for the main config. Run this once per environment.

```powershell
cd infra/terraform/bootstrap
terraform init
terraform apply -var "environment=dev" -var "owner=Gururajraibagi7@gmail.com"
```

Outputs `storage_account_name` — copy that into `environments/dev.backend.hcl`.

After this runs once you can delete local `terraform.tfstate*` files and never
touch this folder again unless you need to add a new environment.
