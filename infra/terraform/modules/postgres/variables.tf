variable "name_prefix" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "sku_name" {
  description = "Flexible Server SKU. B_Standard_B1ms for lab/dev; GP_Standard_D2s_v3 for prod."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "storage_mb" {
  description = "Storage in MB. Minimum 32768 (32 GB)."
  type        = number
  default     = 32768
}

variable "postgres_version" {
  type    = string
  default = "16"
}

variable "admin_username" {
  description = "Postgres admin username. Stored in Key Vault after provisioning."
  type        = string
  default     = "csadmin"
}

variable "delegated_subnet_id" {
  description = "Subnet ID delegated to Microsoft.DBforPostgreSQL/flexibleServers (private access)."
  type        = string
  default     = "" # empty = public access for lab; set in prod
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID for private-access Flexible Server."
  type        = string
  default     = ""
}

variable "log_analytics_workspace_id" {
  type    = string
  default = ""
}
