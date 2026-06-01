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

variable "log_retention_days" {
  description = "Log Analytics workspace retention in days (30–730)."
  type        = number
  default     = 30
}
