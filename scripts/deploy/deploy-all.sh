#!/usr/bin/env bash
# T67: apply the new-resource-only Terraform (never the existing warehouse).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -z "${GCP_PROJECT_ID:-}" ]; then
  echo "Set GCP_PROJECT_ID before running this script (must match build-and-push.sh's image tags)" >&2
  exit 1
fi
GCP_REGION="${GCP_REGION:-us-central1}"
AR_HOST="${GCP_REGION}-docker.pkg.dev"
AR_REPO="sre-incident-platform"

cd "${REPO_ROOT}/infra"
terraform init
terraform plan \
  -var-file="environments/demo/terraform.tfvars" \
  -var="container_image_alert_replay=${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/alert-replay-service:latest" \
  -var="container_image_orchestrator=${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/agent-orchestrator:latest" \
  -var="container_image_api_gateway=${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/api-gateway:latest" \
  -var="container_image_demo_target=${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/demo-target-service:latest" \
  -out=tfplan
echo "Review the plan above -- it must show ZERO changes to sre_telemetry/sre_topology/sre_knowledge_base/sre_incident_mart datasets themselves (FR-001)."
terraform apply tfplan
