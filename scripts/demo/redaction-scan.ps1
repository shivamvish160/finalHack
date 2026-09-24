# T65: pre-demo secret/PII leakage scan (SC-008).
# Runs the redaction-focused pytest subset, then greps built frontend output
# (if present) for obvious leaked-secret patterns as a second, independent pass.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "Running redaction/PII unit tests..."
& "$repoRoot\.venv\Scripts\python.exe" -m pytest "$repoRoot\tests\unit\test_redaction_scan.py" "$repoRoot\tests\unit\test_redaction.py" -v
if ($LASTEXITCODE -ne 0) { throw "Redaction unit tests failed" }

$frontendBuild = Join-Path $repoRoot "frontend\.next"
if (Test-Path $frontendBuild) {
    Write-Host "Scanning built frontend output for leaked secret patterns..."
    $patterns = @('AKIA[0-9A-Z]{16}', 'BEGIN PRIVATE KEY', 'sk-[A-Za-z0-9]{20,}')
    foreach ($pattern in $patterns) {
        $hits = Select-String -Path (Join-Path $frontendBuild "**\*.js") -Pattern $pattern -ErrorAction SilentlyContinue
        if ($hits) {
            Write-Warning "Potential secret leak matching '$pattern':"
            $hits | ForEach-Object { Write-Warning "  $($_.Path):$($_.LineNumber)" }
            exit 1
        }
    }
}

Write-Host "OK: no secret/PII leakage found."
