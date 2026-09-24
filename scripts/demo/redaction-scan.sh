#!/usr/bin/env bash
# T65: pre-demo secret/PII leakage scan (SC-008).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Running redaction/PII unit tests..."
"${REPO_ROOT}/.venv/bin/python" -m pytest "${REPO_ROOT}/tests/unit/test_redaction_scan.py" "${REPO_ROOT}/tests/unit/test_redaction.py" -v

FRONTEND_BUILD="${REPO_ROOT}/frontend/.next"
if [ -d "$FRONTEND_BUILD" ]; then
  echo "Scanning built frontend output for leaked secret patterns..."
  PATTERNS=('AKIA[0-9A-Z]{16}' 'BEGIN PRIVATE KEY' 'sk-[A-Za-z0-9]{20,}')
  for pattern in "${PATTERNS[@]}"; do
    if grep -rEl "$pattern" "$FRONTEND_BUILD" --include="*.js" 2>/dev/null; then
      echo "WARNING: potential secret leak matching '${pattern}'" >&2
      exit 1
    fi
  done
fi

echo "OK: no secret/PII leakage found."
