variable "environment" {
  description = "Environment name (dev | prod). Used in resource naming and tagging."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be one of: dev, prod."
  }
}

variable "location" {
  description = "Primary Azure region."
  type        = string
  default     = "eastus2"
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
