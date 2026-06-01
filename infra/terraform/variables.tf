variable "environment" {
  description = "Environment name (lab | dev | prod). Used in resource naming and tagging."
  type        = string
  validation {
    condition     = contains(["lab", "dev", "prod"], var.environment)
    error_message = "environment must be one of: lab, dev, prod."
  }
}

variable "location" {
  description = "Primary Azure region."
  type        = string
  default     = "eastus"
}

variable "project" {
  description = "Project short name (used in resource naming)."
  type        = string
  default     = "clinicalscribe"
}

variable "owner" {
  description = "Owner email — used as a tag and for break-glass alerts."
  type        = string
}

variable "tags" {
  description = "Extra tags merged onto the defaults."
  type        = map(string)
  default     = {}
}

variable "tenant_id" {
  description = "Azure AD tenant ID — used for Key Vault. Defaults to current client tenant."
  type        = string
  default     = ""
}

variable "kv_admin_object_ids" {
  description = "AAD object IDs granted Key Vault Administrator role (e.g. your user, CI SP)."
  type        = list(string)
  default     = []
}
