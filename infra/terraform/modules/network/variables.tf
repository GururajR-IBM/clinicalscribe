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

variable "vnet_address_space" {
  type    = list(string)
  default = ["10.10.0.0/16"]
}

# Subnet CIDRs — must not overlap
variable "subnet_aks_cidr" {
  type    = string
  default = "10.10.0.0/22" # 1022 hosts for AKS node pool
}

variable "subnet_postgres_cidr" {
  type    = string
  default = "10.10.4.0/27" # /27 — delegated to Postgres Flexible Server
}

variable "subnet_private_endpoints_cidr" {
  type    = string
  default = "10.10.5.0/24" # private endpoints for storage, kv, cosmos, search
}

# Resource IDs for private endpoints — set after resources are provisioned
variable "storage_account_id" {
  type    = string
  default = ""
}

variable "keyvault_id" {
  type    = string
  default = ""
}

variable "cosmos_id" {
  type    = string
  default = ""
}

variable "search_id" {
  type    = string
  default = ""
}

variable "log_analytics_workspace_id" {
  type    = string
  default = ""
}
