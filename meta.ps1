#Requires -Version 5.1
<#
.SYNOPSIS
  Neutral meta-framework dispatcher (Windows / PowerShell).
.DESCRIPTION
  Reads 0_phase0_bootstrap/stack_adapter.yaml for the active adapter id, loads
  adapters/<id>/stack_adapter.json, and invokes the declared command for a verb.
  Verb dispatch uses governance_runtime from the manifest (DEC-0005); product_stack
  is informational only. Requires no Python unless the active adapter's commands do.
.EXAMPLE
  .\meta.ps1 health
  .\meta.ps1 validate
  .\meta.ps1 apply-updates --dry-run
#>
param(
  [Parameter(Position = 0)]
  [string]$Verb = "help",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Get-ActiveAdapterId {
  $sel = Join-Path $Root "0_phase0_bootstrap/stack_adapter.yaml"
  if (-not (Test-Path $sel)) { return "generic" }
  foreach ($line in Get-Content $sel) {
    if ($line -match '^\s*adapter:\s*["'']?([a-zA-Z0-9_-]+)') {
      $id = $Matches[1]
      $manifest = Join-Path $Root "adapters/$id/stack_adapter.json"
      if (Test-Path $manifest) { return $id }
      Write-Host "[meta] adapter='$id' missing; falling back to generic"
      return "generic"
    }
  }
  return "generic"
}

function Resolve-Verb([object]$Manifest, [string]$Name) {
  if ($Manifest.commands.PSObject.Properties.Name -contains $Name) {
    return $Name
  }
  if ($Manifest.aliases -and $Manifest.aliases.PSObject.Properties.Name -contains $Name) {
    return [string]$Manifest.aliases.$Name
  }
  return $null
}

if ($Verb -in @("help", "-h", "--help", "")) {
  Write-Host @"
meta.ps1 — stack-agnostic meta-framework dispatcher

Usage:  .\meta.ps1 <verb> [args...]

Required verbs:
  init, generate-context, validate, check-updates, apply-updates,
  submit-feedback, health, crosswalk

Optional: status (fleet backlog + governance gap open-item counts)

Legacy aliases (python adapter): update-template, verify-template, template-status, onboard

Active adapter is read from 0_phase0_bootstrap/stack_adapter.yaml
(missing selection → adapters/generic)
"@
  exit 0
}

$adapterId = Get-ActiveAdapterId
$manifestPath = Join-Path $Root "adapters/$adapterId/stack_adapter.json"
if (-not (Test-Path $manifestPath)) {
  Write-Error "Adapter manifest not found: $manifestPath (adapter=$adapterId)"
  exit 2
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

# DEC-0005: verb dispatch consults governance_runtime only — never product_stack.
$dispatchRuntime = $adapterId
if ($manifest.PSObject.Properties.Name -contains "governance_runtime" -and $manifest.governance_runtime) {
  $dispatchRuntime = [string]$manifest.governance_runtime
}
if ($dispatchRuntime -ne $adapterId) {
  Write-Error "governance_runtime='$dispatchRuntime' does not match selected adapter='$adapterId'"
  exit 2
}

$resolved = Resolve-Verb $manifest $Verb
if (-not $resolved) {
  Write-Error "Unknown verb '$Verb' for adapter '$adapterId' (governance_runtime=$dispatchRuntime)"
  exit 2
}

$binding = $manifest.commands.$resolved
$run = [string]$binding.run
if (-not $run) {
  Write-Error "No run command for verb '$resolved'"
  exit 2
}

# Append remaining args to the declared command
$argStr = if ($Rest -and $Rest.Count -gt 0) { " " + ($Rest -join " ") } else { "" }
$full = "$run$argStr"

Write-Host "[meta] adapter=$adapterId governance_runtime=$dispatchRuntime verb=$resolved"
Write-Host "[meta] exec: $full"

# Use cmd.exe for consistent cross-tool quoting of simple command strings
$p = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $full) -NoNewWindow -Wait -PassThru
exit $p.ExitCode
