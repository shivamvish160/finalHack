# T67: apply the new-resource-only Terraform (never the existing warehouse).
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not $env:GCP_PROJECT_ID) { throw "Set GCP_PROJECT_ID before running this script (must match build-and-push.ps1's image tags)" }
$project = $env:GCP_PROJECT_ID
$gcpRegion = if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }
$arHost = "$gcpRegion-docker.pkg.dev"
$arRepo = "sre-incident-platform"

Push-Location (Join-Path $repoRoot "infra")
try {
    terraform init
    terraform plan `
        -var-file="environments/demo/terraform.tfvars" `
        -var="container_image_alert_replay=$arHost/$project/$arRepo/alert-replay-service:latest" `
        -var="container_image_orchestrator=$arHost/$project/$arRepo/agent-orchestrator:latest" `
        -var="container_image_api_gateway=$arHost/$project/$arRepo/api-gateway:latest" `
        -var="container_image_demo_target=$arHost/$project/$arRepo/demo-target-service:latest" `
        -out=tfplan
    Write-Host "Review the plan above -- it must show ZERO changes to sre_telemetry/sre_topology/sre_knowledge_base/sre_incident_mart datasets themselves (FR-001)."
    terraform apply tfplan
} finally {
    Pop-Location
}
