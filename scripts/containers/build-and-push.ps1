# Build all 9 service images and push to ACR.
# Usage:
#   .\scripts\containers\build-and-push.ps1 -AcrName <acr> -Tag <tag>
#
# Requires: docker desktop running, az login, AcrPush on the registry.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$AcrName,
    [string]$Tag = "latest",
    [string]$Platform = "linux/amd64"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path "$PSScriptRoot/../.."
$server = "$AcrName.azurecr.io"

Write-Host "Logging into $server ..."
az acr login --name $AcrName | Out-Null

# Map: image repo name -> source folder containing the Dockerfile
$services = @{
    "gateway"           = "services/gateway"
    "orchestrator"      = "services/orchestrator"
    "ingestion-worker"  = "services/ingestion-worker"
    "eval-runner"       = "services/eval-runner"
    "mcp-medical-kb"    = "mcp-servers/medical-kb"
    "mcp-coding"        = "mcp-servers/coding"
    "mcp-ehr"           = "mcp-servers/ehr-mock"
    "mcp-drug"          = "mcp-servers/drug-interaction"
    "web"               = "apps/web"
}

foreach ($svc in $services.Keys) {
    $ctx = Join-Path $repoRoot $services[$svc]
    $image = "${server}/${svc}:${Tag}"
    Write-Host "`n==> Building $image  (context: $ctx)"
    docker build --platform $Platform -t $image $ctx
    Write-Host "==> Pushing $image"
    docker push $image
}

Write-Host "`nAll images pushed to $server with tag '$Tag'."
Write-Host "Next: terraform -chdir=infra/terraform apply -var image_tag=$Tag"
