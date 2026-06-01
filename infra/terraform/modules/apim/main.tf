# ── Azure API Management ───────────────────────────────────────────────────
#
# Acts as the AI Gateway fronting the ClinicalScribe gateway microservice.
# Responsibilities:
#   - Clerk JWT validation (RS256 via JWKS)
#   - Per-subscription rate limiting
#   - Centralized access logging to Log Analytics
#
# SKUs:
#   lab/dev  — Consumption_0 (serverless, no VNet, ~0 cost)
#   prod     — Developer_1 or Premium_1 (VNet injection, HA, custom domain)

resource "azurerm_api_management" "main" {
  name                = "${var.name_prefix}-apim"
  resource_group_name = var.resource_group_name
  location            = var.location
  publisher_name      = var.publisher_name
  publisher_email     = var.publisher_email
  sku_name            = var.sku_name
  tags                = var.tags

  identity {
    type = "SystemAssigned"
  }
}

# ── Backend: gateway microservice ─────────────────────────────────────────

resource "azurerm_api_management_backend" "gateway" {
  name                = "gateway"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = var.gateway_backend_url
}

# ── API: ClinicalScribe Gateway REST API ──────────────────────────────────

resource "azurerm_api_management_api" "clinicalscribe" {
  name                  = "clinicalscribe"
  resource_group_name   = var.resource_group_name
  api_management_name   = azurerm_api_management.main.name
  revision              = "1"
  display_name          = "ClinicalScribe API"
  path                  = "api"
  protocols             = ["https"]
  subscription_required = false # Auth is Clerk JWT, not APIM subscription keys
}

# ── Product: default (groups all APIs) ────────────────────────────────────

resource "azurerm_api_management_product" "default" {
  product_id            = "default"
  resource_group_name   = var.resource_group_name
  api_management_name   = azurerm_api_management.main.name
  display_name          = "Default"
  description           = "Default product for ClinicalScribe APIs"
  subscription_required = false
  published             = true
}

resource "azurerm_api_management_product_api" "default" {
  api_name            = azurerm_api_management_api.clinicalscribe.name
  product_id          = azurerm_api_management_product.default.product_id
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
}

# ── Global policy: JWT validation + rate limit ────────────────────────────
# OWASP A02: validate Clerk JWT on every request before routing to backend.
# Clerk issues RS256 tokens; public keys served via JWKS endpoint.

resource "azurerm_api_management_policy" "global" {
  api_management_id = azurerm_api_management.main.id

  xml_content = <<-XML
    <policies>
      <inbound>
        <!-- Clerk JWT validation (RS256) -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401"
                      failed-validation-error-message="Unauthorized" require-expiration-time="true">
          <openid-config url="${var.clerk_jwks_uri}"/>
          <required-claims>
            <claim name="sub" match="any"/>
          </required-claims>
        </validate-jwt>
        <!-- Rate limit: 120 requests per 60 seconds per IP -->
        <rate-limit-by-key calls="120" renewal-period="60"
                           counter-key="@(context.Request.IpAddress)"
                           increment-condition="@(true)"/>
        <!-- Route to gateway backend -->
        <set-backend-service backend-id="${azurerm_api_management_backend.gateway.name}"/>
        <base/>
      </inbound>
      <backend>
        <base/>
      </backend>
      <outbound>
        <!-- Remove APIM server header -->
        <set-header name="X-Powered-By" exists-action="delete"/>
        <base/>
      </outbound>
      <on-error>
        <base/>
      </on-error>
    </policies>
  XML
}

# ── Diagnostic settings ────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "apim" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-apim-diag"
  target_resource_id         = azurerm_api_management.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
  }

  enabled_log {
    category = "GatewayLogs"
  }
}
