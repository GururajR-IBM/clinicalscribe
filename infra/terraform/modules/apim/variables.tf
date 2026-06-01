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

variable "publisher_name" {
  type    = string
  default = "ClinicalScribe"
}

variable "publisher_email" {
  type    = string
  default = "admin@clinicalscribe.local"
}

# Consumption tier for lab/dev; Developer or Premium for prod
variable "sku_name" {
  type    = string
  default = "Consumption_0"   # "Consumption_0" or "Developer_1"
}

# Clerk JWKS endpoint for JWT validation policy
variable "clerk_jwks_uri" {
  type    = string
  default = "https://clerk.your-domain.com/.well-known/jwks.json"
}

# URL of the gateway microservice AKS ingress
variable "gateway_backend_url" {
  type    = string
  default = "http://localhost:8000"
}

variable "log_analytics_workspace_id" {
  type    = string
  default = ""
}
