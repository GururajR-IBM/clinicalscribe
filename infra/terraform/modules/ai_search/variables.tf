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

variable "sku" {
  description = "AI Search SKU. Use 'basic' for dev/lab, 'standard' for prod (semantic + vector)."
  type        = string
  default     = "basic"
  validation {
    condition     = contains(["free", "basic", "standard", "standard2", "standard3"], var.sku)
    error_message = "sku must be one of: free, basic, standard, standard2, standard3."
  }
}

variable "replica_count" {
  description = "Number of replicas (1 for dev, 2+ for prod HA)."
  type        = number
  default     = 1
}

variable "partition_count" {
  description = "Number of partitions (storage shards). 1 for basic/dev."
  type        = number
  default     = 1
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings."
  type        = string
  default     = ""
}

variable "aoai_endpoint" {
  description = "Azure OpenAI endpoint for the vectorizer. Optional — supports BYO (external AOAI account)."
  type        = string
  default     = ""
}

variable "aoai_embedding_deployment" {
  description = "Deployment name for the embedding model used by the AI Search vectorizer."
  type        = string
  default     = "text-embedding-3-large"
}
