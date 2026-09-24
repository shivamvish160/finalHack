# T67: build + push all 4 Cloud Run service container images.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not $env:GCP_PROJECT_ID) { throw "Set GCP_PROJECT_ID before running this script" }

$services = @(
    @{ Name = "alert-replay-service"; Path = "services/alert-replay-service" },
    @{ Name = "agent-orchestrator";   Path = "services/agent-orchestrator" },
    @{ Name = "api-gateway";          Path = "services/api-gateway" },
    @{ Name = "demo-target-service";  Path = "services/demo-target-service" }
)

foreach ($svc in $services) {
    $image = "gcr.io/$($env:GCP_PROJECT_ID)/$($svc.Name):latest"
    $dockerfile = Join-Path $repoRoot "$($svc.Path)/Dockerfile"
    Write-Host "Building $image (context: repo root, file: $dockerfile) ..."
    # Build context is the REPO ROOT, not the service subfolder -- every
    # service's Dockerfile COPYs the shared agents/ package, which only
    # exists outside services/<name>/ (TD-1 fix).
    docker build -f $dockerfile -t $image $repoRoot
    Write-Host "Pushing $image ..."
    docker push $image
}

Write-Host "All 4 service images built and pushed."
