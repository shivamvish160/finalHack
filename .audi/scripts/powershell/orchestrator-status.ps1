# orchestrator-status.ps1 — read current workflow state
# Usage: .\orchestrator-status.ps1 -Feature <feature_name> [-ProjectDir <path>]
# Output: JSON to stdout

param(
    [Parameter(Mandatory=$true)]
    [string]$Feature,

    [string]$ProjectDir = ""
)

if (-not $ProjectDir) {
    try {
        $ProjectDir = & git rev-parse --show-toplevel 2>$null
    } catch {}
    if (-not $ProjectDir) {
        $ProjectDir = (Get-Location).Path
    }
}

& audi orchestrator status $ProjectDir --feature $Feature
