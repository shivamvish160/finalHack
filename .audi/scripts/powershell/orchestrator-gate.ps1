# orchestrator-gate.ps1 — apply a gate decision and persist state
# Usage: .\orchestrator-gate.ps1 -Feature <name> -Action <action> -Phase <n> [-RollbackTarget <n>] [-Feedback <text>] [-ProjectDir <path>]
# Output: JSON to stdout

param(
    [Parameter(Mandatory=$true)]
    [string]$Feature,

    [Parameter(Mandatory=$true)]
    [ValidateSet("approve","revise","skip","abort","rollback")]
    [string]$Action,

    [Parameter(Mandatory=$true)]
    [int]$Phase,

    [int]$RollbackTarget = 0,
    [string]$Feedback = "",
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

$args_list = @("orchestrator", "gate", $ProjectDir, "--feature", $Feature, "--action", $Action, "--phase", $Phase)

if ($RollbackTarget -gt 0) {
    $args_list += @("--rollback-target", $RollbackTarget)
}
if ($Feedback) {
    $args_list += @("--feedback", $Feedback)
}

& audi @args_list
