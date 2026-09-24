#!/usr/bin/env bash
# T68: provision the 5 Firebase demo user accounts with role custom claims.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

declare -A DEMO_USERS=(
  ["oncall-demo@example.com"]="OnCallEngineer"
  ["commander-demo@example.com"]="IncidentCommander"
  ["approver-demo@example.com"]="Approver"
  ["exec-demo@example.com"]="ExecutiveViewer"
  ["admin-demo@example.com"]="Administrator"
)

for email in "${!DEMO_USERS[@]}"; do
  role="${DEMO_USERS[$email]}"
  echo "Seeding ${email} with role=${role}..."
  python3 - "$email" "$role" <<'PYEOF'
import sys
import firebase_admin
from firebase_admin import auth
email, role = sys.argv[1], sys.argv[2]
firebase_admin.initialize_app()
try:
    u = auth.get_user_by_email(email)
except auth.UserNotFoundError:
    u = auth.create_user(email=email, password="DemoPassw0rd!")
auth.set_custom_user_claims(u.uid, {"role": role})
print(f"Seeded {u.uid} with role {role}")
PYEOF
done

echo "All 5 demo users seeded."
