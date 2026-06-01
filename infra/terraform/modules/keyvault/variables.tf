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

variable "tenant_id" {
  description = "Azure AD tenant ID (used for Key Vault access)."
  type        = string
}

variable "admin_object_ids" {
  description = "List of AAD object IDs (users/groups/SPs) to grant Key Vault Administrator role."
  type        = list(string)
  default     = []
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings."
  type        = string
}
