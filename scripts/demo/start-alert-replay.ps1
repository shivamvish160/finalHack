# T69: kick off the >=1000 alerts/minute replay for the live demo.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not $env:GCP_PROJECT_ID) { throw "Set GCP_PROJECT_ID before running this script" }

Write-Host "Triggering alert-replay-service (or running it locally against the real warehouse)..."
& "$repoRoot\.venv\Scripts\python.exe" "$repoRoot\services\alert-replay-service\app\replay.py"
