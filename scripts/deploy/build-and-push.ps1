# T67: build + push all 5 Cloud Run service container images.
# Uses Cloud Build (gcloud builds submit) rather than local `docker build`/
# `docker push` -- sidesteps local Docker daemon / outbound-network
# flakiness entirely, and uses Artifact Registry, NOT Container Registry
# (gcr.io) -- gcr.io is deprecated and unusable on new GCP projects.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not $env:GCP_PROJECT_ID) { throw "Set GCP_PROJECT_ID before running this script" }
$gcpRegion = if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }
$arRepo = "sre-incident-platform"
$arHost = "$gcpRegion-docker.pkg.dev"

Write-Host "Ensuring Artifact Registry repo $arRepo exists in $gcpRegion..."
$null = gcloud artifacts repositories describe $arRepo --location=$gcpRegion --project=$env:GCP_PROJECT_ID 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $arRepo --repository-format=docker --location=$gcpRegion --project=$env:GCP_PROJECT_ID
}

$services = @(
    @{ Name = "alert-replay-service"; Path = "services/alert-replay-service" },
    @{ Name = "agent-orchestrator";   Path = "services/agent-orchestrator" },
    @{ Name = "api-gateway";          Path = "services/api-gateway" },
    @{ Name = "demo-target-service";  Path = "services/demo-target-service" }
)

$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid())
New-Item -ItemType Directory -Path $tmpDir | Out-Null
try {
    foreach ($svc in $services) {
        $image = "$arHost/$($env:GCP_PROJECT_ID)/$arRepo/$($svc.Name):latest"
        $dockerfileRel = "$($svc.Path)/Dockerfile"  # relative to repoRoot, the uploaded build context
        $cloudbuildYaml = Join-Path $tmpDir "cloudbuild-$($svc.Name).yaml"

        @"
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', '$dockerfileRel', '-t', '$image', '.']
images:
- '$image'
"@ | Set-Content -Path $cloudbuildYaml -Encoding utf8

        Write-Host "Building + pushing $image via Cloud Build (Dockerfile: $dockerfileRel) ..."
        gcloud builds submit $repoRoot --config=$cloudbuildYaml --project=$env:GCP_PROJECT_ID --region=$gcpRegion
    }

    # Frontend: NEXT_PUBLIC_* vars are baked into the JS bundle at build time,
    # not runtime env vars -- set these before running this script, typically
    # to the api-gateway URL from a prior `terraform apply`. Its build context
    # is frontend/ itself (not repoRoot), since it has no dependency on agents/.
    $frontendImage = "$arHost/$($env:GCP_PROJECT_ID)/$arRepo/frontend:latest"
    $frontendCloudbuildYaml = Join-Path $tmpDir "cloudbuild-frontend.yaml"
    $apiGatewayUrl = if ($env:NEXT_PUBLIC_API_GATEWAY_URL) { $env:NEXT_PUBLIC_API_GATEWAY_URL } else { "" }
    $firebaseApiKey = if ($env:NEXT_PUBLIC_FIREBASE_API_KEY) { $env:NEXT_PUBLIC_FIREBASE_API_KEY } else { "" }
    $firebaseProjectId = if ($env:NEXT_PUBLIC_FIREBASE_PROJECT_ID) { $env:NEXT_PUBLIC_FIREBASE_PROJECT_ID } else { "" }

    @"
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '-f'
    - 'Dockerfile'
    - '--build-arg'
    - 'NEXT_PUBLIC_API_GATEWAY_URL=$apiGatewayUrl'
    - '--build-arg'
    - 'NEXT_PUBLIC_FIREBASE_API_KEY=$firebaseApiKey'
    - '--build-arg'
    - 'NEXT_PUBLIC_FIREBASE_PROJECT_ID=$firebaseProjectId'
    - '-t'
    - '$frontendImage'
    - '.'
images:
- '$frontendImage'
"@ | Set-Content -Path $frontendCloudbuildYaml -Encoding utf8

    Write-Host "Building + pushing $frontendImage via Cloud Build ..."
    gcloud builds submit "$repoRoot/frontend" --config=$frontendCloudbuildYaml --project=$env:GCP_PROJECT_ID --region=$gcpRegion
} finally {
    Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}

Write-Host "All 5 service images built and pushed to $arHost/$($env:GCP_PROJECT_ID)/$arRepo."
