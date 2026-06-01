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

variable "gpt4o_mini_capacity" {
  description = "TPM capacity (thousands) for gpt-4o-mini deployment."
  type        = number
  default     = 10
}

variable "gpt4o_capacity" {
  description = "TPM capacity (thousands) for gpt-4o deployment."
  type        = number
  default     = 10
}

variable "embedding_capacity" {
  description = "TPM capacity (thousands) for text-embedding-3-large deployment."
  type        = number
  default     = 10
}
