# ── Virtual Network ────────────────────────────────────────────────────────
#
# Hub topology (single VNet for portfolio project; hub-spoke in enterprise).
# Subnets:
#   aks               — AKS system + user node pools
#   postgres          — delegated to Microsoft.DBforPostgreSQL/flexibleServers
#   private_endpoints — Blob, Key Vault, Cosmos, AI Search private endpoints
#
# NSGs restrict inbound/outbound per subnet. Outbound internet egress via
# the AKS subnet's managed outbound rules (not this module).

resource "azurerm_virtual_network" "main" {
  name                = "${var.name_prefix}-vnet"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.vnet_address_space
  tags                = var.tags
}

# ── Subnets ────────────────────────────────────────────────────────────────

resource "azurerm_subnet" "aks" {
  name                 = "aks"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_aks_cidr]
}

resource "azurerm_subnet" "postgres" {
  name                 = "postgres"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_postgres_cidr]

  delegation {
    name = "postgres-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "private-endpoints"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_private_endpoints_cidr]

  private_endpoint_network_policies = "Disabled"
}

# ── NSG: AKS subnet ────────────────────────────────────────────────────────

resource "azurerm_network_security_group" "aks" {
  name                = "${var.name_prefix}-nsg-aks"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  security_rule {
    name                       = "DenyInternetInbound"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

# ── NSG: private endpoints subnet ─────────────────────────────────────────

resource "azurerm_network_security_group" "private_endpoints" {
  name                = "${var.name_prefix}-nsg-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_subnet_network_security_group_association" "private_endpoints" {
  subnet_id                 = azurerm_subnet.private_endpoints.id
  network_security_group_id = azurerm_network_security_group.private_endpoints.id
}

# ── Private DNS zones ──────────────────────────────────────────────────────

resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "keyvault" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "search" {
  name                = "privatelink.search.windows.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Link all DNS zones to the VNet so services resolve private IPs

locals {
  dns_zones = {
    blob     = azurerm_private_dns_zone.blob.id
    keyvault = azurerm_private_dns_zone.keyvault.id
    cosmos   = azurerm_private_dns_zone.cosmos.id
    search   = azurerm_private_dns_zone.search.id
    postgres = azurerm_private_dns_zone.postgres.id
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "links" {
  for_each = local.dns_zones

  name                  = "${var.name_prefix}-dnslink-${each.key}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = split("/", each.value)[length(split("/", each.value)) - 1]
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
  tags                  = var.tags
}

# ── Private endpoints — created only when resource IDs are provided ────────

resource "azurerm_private_endpoint" "storage" {
  count               = var.storage_account_id != "" ? 1 : 0
  name                = "${var.name_prefix}-pe-storage"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = var.tags

  private_service_connection {
    name                           = "storage"
    private_connection_resource_id = var.storage_account_id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "blob"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }
}

resource "azurerm_private_endpoint" "keyvault" {
  count               = var.keyvault_id != "" ? 1 : 0
  name                = "${var.name_prefix}-pe-kv"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = var.tags

  private_service_connection {
    name                           = "keyvault"
    private_connection_resource_id = var.keyvault_id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "keyvault"
    private_dns_zone_ids = [azurerm_private_dns_zone.keyvault.id]
  }
}

resource "azurerm_private_endpoint" "cosmos" {
  count               = var.cosmos_id != "" ? 1 : 0
  name                = "${var.name_prefix}-pe-cosmos"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = var.tags

  private_service_connection {
    name                           = "cosmos"
    private_connection_resource_id = var.cosmos_id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "cosmos"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }
}

resource "azurerm_private_endpoint" "search" {
  count               = var.search_id != "" ? 1 : 0
  name                = "${var.name_prefix}-pe-search"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = var.tags

  private_service_connection {
    name                           = "search"
    private_connection_resource_id = var.search_id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "search"
    private_dns_zone_ids = [azurerm_private_dns_zone.search.id]
  }
}

# ── VNet diagnostic settings ───────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "vnet" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-vnet-diag"
  target_resource_id         = azurerm_virtual_network.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
  }
}
