# orchestrator-probe.ps1 — probe artifacts and detect resume point
# Usage: .\orchestrator-probe.ps1 -Feature <feature_name> [-ProjectDir <path>]
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

& audi orchestrator probe $ProjectDir --feature $Feature
