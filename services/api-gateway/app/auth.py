"""Firebase Authentication + RBAC middleware for api-gateway (T16, FR-035).

Verifies the caller's Firebase ID token and enforces role-based access
control from the token's custom `role` claim. GCP IAM (service accounts,
see design.md §7.1) governs service-to-service access to the warehouse
separately -- this module governs only END-USER access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

ROLE_ON_CALL_ENGINEER = "OnCallEngineer"
ROLE_INCIDENT_COMMANDER = "IncidentCommander"
ROLE_APPROVER = "Approver"
ROLE_EXECUTIVE_VIEWER = "ExecutiveViewer"
ROLE_ADMINISTRATOR = "Administrator"

ALL_ROLES = frozenset(
    {ROLE_ON_CALL_ENGINEER, ROLE_INCIDENT_COMMANDER, ROLE_APPROVER, ROLE_EXECUTIVE_VIEWER, ROLE_ADMINISTRATOR}
)


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    role: str
    display_name: str | None = None


def _ensure_firebase_app_initialized() -> None:
    if not firebase_admin._apps:  # noqa: SLF001 - firebase_admin's own documented check
        firebase_admin.initialize_app()


async def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency: verify the bearer ID token, return the caller's identity+role.

    Raises 401 if the token is missing/invalid, per NFR-005 ("no anonymous
    access to incident or business-impact data").
    """
    _ensure_firebase_app_initialized()

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    id_token = auth_header.removeprefix("Bearer ").strip()
    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception as exc:  # noqa: BLE001 - any verification failure is a 401
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    role = decoded.get("role")
    if role not in ALL_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No valid role claim on this account")

    return AuthenticatedUser(uid=decoded["uid"], role=role, display_name=decoded.get("name"))


def require_roles(*allowed_roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """FastAPI dependency factory enforcing a specific set of allowed roles (FR-035)."""

    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to perform this action",
            )
        return user

    return _dependency
