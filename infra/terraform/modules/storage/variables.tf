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
  description = "Tags to apply to all resources."
  type        = map(string)
  default     = {}
}

variable "media_retention_days" {
  description = "Days after which blobs in encounter-media are auto-deleted."
  type        = number
  default     = 90
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings."
  type        = string
}
