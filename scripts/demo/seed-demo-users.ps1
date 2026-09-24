# T68: provision the 5 Firebase demo user accounts with role custom claims.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$demoUsers = @(
    @{ Email = "oncall-demo@example.com";    Role = "OnCallEngineer" },
    @{ Email = "commander-demo@example.com"; Role = "IncidentCommander" },
    @{ Email = "approver-demo@example.com";  Role = "Approver" },
    @{ Email = "exec-demo@example.com";      Role = "ExecutiveViewer" },
    @{ Email = "admin-demo@example.com";     Role = "Administrator" }
)

foreach ($user in $demoUsers) {
    Write-Host "Seeding $($user.Email) with role=$($user.Role)..."
    & "$repoRoot\.venv\Scripts\python.exe" -c @"
import firebase_admin
from firebase_admin import auth, credentials
firebase_admin.initialize_app()
try:
    u = auth.get_user_by_email('$($user.Email)')
except auth.UserNotFoundError:
    u = auth.create_user(email='$($user.Email)', password='DemoPassw0rd!')
auth.set_custom_user_claims(u.uid, {'role': '$($user.Role)'})
print(f'Seeded {u.uid} with role $($user.Role)')
"@
}

Write-Host "All 5 demo users seeded."
