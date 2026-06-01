<#
.SYNOPSIS
    Back up the current Azure context: Terraform state + resource exports.

.DESCRIPTION
    Snapshots everything needed to "remember" what was deployed before you
    switch / lose access to an Azure subscription:
      1. All local *.tfstate files under infra/terraform -> backups/<stamp>/state/
      2. JSON dump of resource groups and resources visible in the active sub.
      3. The current azure-context.local.json.
      4. The current az account info.

    Output goes into `backups/<utc-timestamp>/` (gitignored).

.EXAMPLE
    powershell -File ./scripts/Backup-AzureContext.ps1
#>
[CmdletBinding()]
param(
    [string]$AzCliPath = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin'
)

$ErrorActionPreference = 'Stop'

if (Test-Path $AzCliPath) { $env:PATH = "$AzCliPath;$env:PATH" }

function Get-RepoRoot {
    $here = $PSScriptRoot
    while ($here -and -not (Test-Path (Join-Path $here '.git'))) {
        $here = Split-Path $here -Parent
    }
    if (-not $here) { throw 'Could not find repo root.' }
    return $here
}

$repoRoot = Get-RepoRoot
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$dest = Join-Path $repoRoot "backups/$stamp"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path "$dest/state" | Out-Null
New-Item -ItemType Directory -Force -Path "$dest/azure" | Out-Null

Write-Host (">> Backup destination: {0}" -f $dest) -ForegroundColor Cyan

# 1. Terraform state
$tfDir = Join-Path $repoRoot 'infra/terraform'
$stateFiles = Get-ChildItem -Path $tfDir -Recurse -Include 'terraform.tfstate', 'terraform.tfstate.backup' -ErrorAction SilentlyContinue
foreach ($s in $stateFiles) {
    $rel = $s.FullName.Substring($tfDir.Length + 1) -replace '[\\/]', '_'
    Copy-Item $s.FullName -Destination (Join-Path "$dest/state" $rel) -Force
    Write-Host ("   OK {0}" -f $s.FullName)
}
if (-not $stateFiles) {
    Write-Host '   (no local tfstate files yet - nothing to back up)' -ForegroundColor Yellow
}

# 2. Azure context
$ctxPath = Join-Path $repoRoot 'azure-context.local.json'
if (Test-Path $ctxPath) {
    Copy-Item $ctxPath -Destination "$dest/azure-context.local.json" -Force
}

az account show --output json 2>$null | Set-Content -Path "$dest/azure/account-show.json" -Encoding UTF8

# 3. Resource inventory
Write-Host '>> Dumping resource group + resource inventory...' -ForegroundColor Cyan
$rgsJson = az group list --output json 2>$null
$rgsJson | Set-Content -Path "$dest/azure/resource-groups.json" -Encoding UTF8

$resourcesJson = az resource list --output json 2>$null
$resourcesJson | Set-Content -Path "$dest/azure/resources.json" -Encoding UTF8

# 4. Quick human-readable summary
$summary = @()
$summary += 'ClinicalScribe Azure context backup'
$summary += '==================================='
$summary += ('Timestamp (UTC): ' + $stamp)
$summary += ''
if (Test-Path $ctxPath) {
    $summary += 'Profile context:'
    $summary += (Get-Content $ctxPath -Raw)
    $summary += ''
}
$rgs = $rgsJson | ConvertFrom-Json
if ($rgs) {
    $summary += ('Resource groups ({0}):' -f $rgs.Count)
    foreach ($g in $rgs) { $summary += ('  - {0}  [{1}]' -f $g.name, $g.location) }
}
$resources = $resourcesJson | ConvertFrom-Json
if ($resources) {
    $summary += ''
    $summary += ('Resources ({0}):' -f $resources.Count)
    foreach ($r in $resources) { $summary += ('  - {0}  {1}' -f $r.type, $r.name) }
}
$summary -join "`r`n" | Set-Content -Path "$dest/SUMMARY.md" -Encoding UTF8

Write-Host ''
Write-Host ('OK - Backup complete: {0}' -f $dest) -ForegroundColor Green
Write-Host ('     See {0}/SUMMARY.md for a quick view.' -f $dest) -ForegroundColor Green
