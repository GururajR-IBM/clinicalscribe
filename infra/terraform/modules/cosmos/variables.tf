variable "name_prefix" {
  description = "Resource naming prefix (e.g. clinicalscribe-lab)."
  type        = string
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

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for Cosmos diagnostic settings."
  type        = string
  default     = ""
}
