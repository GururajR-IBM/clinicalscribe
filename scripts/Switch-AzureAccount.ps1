<#
.SYNOPSIS
    Switch the active Azure CLI account/subscription for ClinicalScribe work.

.DESCRIPTION
    Lists logged-in accounts; lets you pick one (or login fresh); sets the
    subscription; writes the chosen context to `azure-context.local.json`
    (gitignored) so the rest of the toolchain can read it.

.PARAMETER ProfileName
    Friendly profile name (lab | dev | prod). Drives the default region.

.EXAMPLE
    powershell -File ./scripts/Switch-AzureAccount.ps1 -ProfileName lab
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('lab', 'dev', 'prod')]
    [string]$ProfileName,

    [string]$AzCliPath = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin'
)

$ErrorActionPreference = 'Stop'

if (Test-Path $AzCliPath) { $env:PATH = "$AzCliPath;$env:PATH" }

function Get-RepoRoot {
    $here = $PSScriptRoot
    while ($here -and -not (Test-Path (Join-Path $here '.git'))) {
        $here = Split-Path $here -Parent
    }
    if (-not $here) { throw 'Could not find repo root (no .git folder above this script).' }
    return $here
}

$repoRoot = Get-RepoRoot
$contextPath = Join-Path $repoRoot 'azure-context.local.json'

Write-Host '>> Listing Azure accounts you are signed into...' -ForegroundColor Cyan
$rawList = az account list --output json 2>$null | ConvertFrom-Json

if (-not $rawList -or $rawList.Count -eq 0) {
    Write-Host '   (no accounts cached - launching device-code login)' -ForegroundColor Yellow
    az login --use-device-code | Out-Null
    $rawList = az account list --output json | ConvertFrom-Json
}

if ($rawList.Count -eq 1) {
    $chosen = $rawList[0]
    Write-Host (">> Only one subscription: {0}" -f $chosen.name) -ForegroundColor Green
}
else {
    Write-Host ''
    Write-Host '  #   Name                                  Subscription Id                       User'
    Write-Host '  --  ------------------------------------  ------------------------------------  ----'
    for ($i = 0; $i -lt $rawList.Count; $i++) {
        $a = $rawList[$i]
        $star = if ($a.isDefault) { '*' } else { ' ' }
        Write-Host ("  {0,-2}{1} {2,-36}  {3}  {4}" -f $i, $star, $a.name, $a.id, $a.user.name)
    }
    Write-Host ''
    $sel = Read-Host 'Pick a subscription number (or "n" to login fresh)'
    if ($sel -eq 'n') {
        az logout 2>$null | Out-Null
        az account clear 2>$null | Out-Null
        az login --use-device-code | Out-Null
        $rawList = az account list --output json | ConvertFrom-Json
        $chosen = $rawList[0]
    }
    else {
        $chosen = $rawList[[int]$sel]
    }
}

az account set --subscription $chosen.id | Out-Null

$ctx = [pscustomobject]@{
    profile        = $ProfileName
    subscriptionId = $chosen.id
    subscription   = $chosen.name
    tenantId       = $chosen.tenantId
    user           = $chosen.user.name
    setAt          = (Get-Date).ToString('o')
}

$ctx | ConvertTo-Json -Depth 4 | Set-Content -Path $contextPath -Encoding UTF8

Write-Host ''
Write-Host 'OK - Active Azure context:' -ForegroundColor Green
$ctx | Format-List | Out-String | Write-Host
Write-Host ("OK - Wrote {0} (gitignored)" -f $contextPath) -ForegroundColor Green
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Cyan
Write-Host ("  Copy-Item infra/terraform/environments/{0}.tfvars.example infra/terraform/environments/{0}.tfvars" -f $ProfileName)
Write-Host '  terraform -chdir=infra/terraform init'
Write-Host ("  terraform -chdir=infra/terraform plan  -var-file=environments/{0}.tfvars" -f $ProfileName)
