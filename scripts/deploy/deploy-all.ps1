# T67: apply the new-resource-only Terraform (never the existing warehouse).
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Push-Location (Join-Path $repoRoot "infra")
try {
    terraform init
    terraform plan -var-file="environments/demo/terraform.tfvars" -out=tfplan
    Write-Host "Review the plan above -- it must show ZERO changes to sre_telemetry/sre_topology/sre_knowledge_base/sre_incident_mart datasets themselves (FR-001)."
    terraform apply tfplan
} finally {
    Pop-Location
}
