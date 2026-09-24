#!/usr/bin/env pwsh
# orchestrator-branch.ps1 — Create and checkout a feature branch for the orchestrator.
#
# Usage:
#   ./orchestrator-branch.ps1 -FeatureDescription "Add OAuth2 login"
#   ./orchestrator-branch.ps1 -FeatureDescription "Add OAuth2 login" -ShortName "oauth2-login"
#   ./orchestrator-branch.ps1 -FeatureDescription "Add OAuth2 login" -Number 5
#   ./orchestrator-branch.ps1 -FeatureDescription "Add OAuth2 login" -Timestamp
#
# Always outputs JSON (-Json is implicit).
# Delegates entirely to create-new-feature.ps1.
#
# JSON output:
#   { "ok": true,  "branch": "001-url-shortener", "feature_name": "url-shortener", "number": 1 }
#   { "ok": false, "error": "<message>" }

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$FeatureDescription,

    [string]$ShortName,
    [int]$Number = 0,
    [switch]$Timestamp
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CreateScript = Join-Path $ScriptDir 'create-new-feature.ps1'

if (-not (Test-Path $CreateScript)) {
    ConvertTo-Json @{ ok = $false; error = "create-new-feature.ps1 not found at $CreateScript" } -Compress
    exit 1
}

if ([string]::IsNullOrWhiteSpace($FeatureDescription)) {
    ConvertTo-Json @{ ok = $false; error = 'FeatureDescription is required' } -Compress
    exit 1
}

# Build argument list and delegate to create-new-feature.ps1 with -Json
$args = @('-Json', $FeatureDescription)
if ($ShortName)  { $args += '-ShortName'; $args += $ShortName }
if ($Number -gt 0) { $args += '-Number'; $args += $Number }
if ($Timestamp)  { $args += '-Timestamp' }

& $CreateScript @args
