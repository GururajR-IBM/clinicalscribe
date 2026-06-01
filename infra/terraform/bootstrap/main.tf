terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

variable "environment" {
  type = string
}

variable "owner" {
  type = string
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "project" {
  type    = string
  default = "clinicalscribe"
}

locals {
  tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform-bootstrap"
    purpose     = "tfstate"
  }
}

resource "random_string" "suffix" {
  length  = 8
  upper   = false
  special = false
  numeric = true
}

resource "azurerm_resource_group" "tfstate" {
  name     = "${var.project}-tfstate-rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "tfstate" {
  name                            = "csbtfstate${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.tfstate.name
  location                        = azurerm_resource_group.tfstate.location
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }
  tags = local.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}

output "resource_group_name" {
  value = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  value = azurerm_storage_account.tfstate.name
}

output "container_name" {
  value = azurerm_storage_container.tfstate.name
}
