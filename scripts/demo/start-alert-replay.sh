#!/usr/bin/env bash
# T69: kick off the >=1000 alerts/minute replay for the live demo.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -z "${GCP_PROJECT_ID:-}" ]; then
  echo "Set GCP_PROJECT_ID before running this script" >&2
  exit 1
fi

echo "Triggering alert-replay-service (or running it locally against the real warehouse)..."
python3 "${REPO_ROOT}/services/alert-replay-service/app/replay.py"
