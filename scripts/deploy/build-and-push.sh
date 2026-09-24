#!/usr/bin/env bash
# T67: build + push all 4 Cloud Run service container images.
# Uses Cloud Build (gcloud builds submit) rather than local `docker build`/
# `docker push` -- Cloud Build runs entirely inside Google's network, so it
# sidesteps Cloud Shell's local Docker daemon / outbound-network flakiness
# entirely (a local `docker push` to *.pkg.dev can fail with
# "connection refused" in some Cloud Shell sessions even when gcloud/auth
# are correctly configured). Also uses Artifact Registry, NOT Container
# Registry (gcr.io) -- gcr.io is deprecated and unusable on new projects.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -z "${GCP_PROJECT_ID:-}" ]; then
  echo "Set GCP_PROJECT_ID before running this script" >&2
  exit 1
fi
GCP_REGION="${GCP_REGION:-us-central1}"
AR_REPO="sre-incident-platform"
AR_HOST="${GCP_REGION}-docker.pkg.dev"

echo "Ensuring Artifact Registry repo ${AR_REPO} exists in ${GCP_REGION}..."
gcloud artifacts repositories describe "$AR_REPO" \
  --location="$GCP_REGION" --project="$GCP_PROJECT_ID" >/dev/null 2>&1 || \
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker --location="$GCP_REGION" --project="$GCP_PROJECT_ID"

declare -A SERVICES=(
  ["alert-replay-service"]="services/alert-replay-service"
  ["agent-orchestrator"]="services/agent-orchestrator"
  ["api-gateway"]="services/api-gateway"
  ["demo-target-service"]="services/demo-target-service"
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

for name in "${!SERVICES[@]}"; do
  path="${SERVICES[$name]}"
  image="${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}/${name}:latest"
  dockerfile_rel="${path}/Dockerfile"  # relative to REPO_ROOT, the uploaded build context
  cloudbuild_yaml="${TMP_DIR}/cloudbuild-${name}.yaml"

  cat > "$cloudbuild_yaml" <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-f', '${dockerfile_rel}', '-t', '${image}', '.']
images:
- '${image}'
EOF

  echo "Building + pushing ${image} via Cloud Build (Dockerfile: ${dockerfile_rel}) ..."
  gcloud builds submit "$REPO_ROOT" \
    --config="$cloudbuild_yaml" \
    --project="$GCP_PROJECT_ID" \
    --region="$GCP_REGION"
done

echo "All 4 service images built and pushed to ${AR_HOST}/${GCP_PROJECT_ID}/${AR_REPO}."
