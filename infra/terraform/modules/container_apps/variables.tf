variable "name_prefix" {
  description = "Shared naming prefix (<project>-<env>)."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group to deploy into."
  type        = string
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default     = {}
}

variable "log_analytics_workspace_id" {
  description = "LAW resource ID for the ACA environment (required by ACA)."
  type        = string
}

variable "acr_sku" {
  description = "Container Registry SKU. Basic is cheapest (~$5/mo)."
  type        = string
  default     = "Basic"
}

variable "image_tag" {
  description = "Image tag used for every service (e.g. git short SHA or 'latest')."
  type        = string
  default     = "latest"
}

# -----------------------------------------------------------------------------
# Per-service knobs. Map-driven so adding a 10th service is one entry.
# Defaults: scale-to-zero, min 0.25 vCPU / 0.5 GiB (cheapest ACA workload profile).
# -----------------------------------------------------------------------------
variable "services" {
  description = <<-EOT
    Map of container-app definitions. Key = app name (used in DNS).
      image_repo : repo name inside the ACR (e.g. "orchestrator")
      port       : ingress target port; null disables external ingress
      external   : true = public Internet, false = internal-only (env-scope DNS)
      cpu / memory : container resources
      min_replicas / max_replicas : autoscale bounds
      env        : map of plain env vars
      secret_env : map of env-var-name -> Key Vault secret name (resolved via KV ref)
  EOT
  type = map(object({
    image_repo   = string
    port         = optional(number)
    external     = optional(bool, false)
    cpu          = optional(number, 0.25)
    memory       = optional(string, "0.5Gi")
    min_replicas = optional(number, 0)
    max_replicas = optional(number, 2)
    env          = optional(map(string), {})
    secret_env   = optional(map(string), {})
  }))
  default = {}
}

variable "key_vault_id" {
  description = "Key Vault ID used to resolve secret_env entries. Empty = disabled."
  type        = string
  default     = ""
}
