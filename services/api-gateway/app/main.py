"""api-gateway FastAPI application entrypoint.

Backend-for-Frontend for all 8 UI pages (design.md §3.1): Firebase auth +
RBAC (auth.py), REST contract (contracts/rest-api.md), sole publisher of
approval decisions, and audit logging (audit_log.py, FR-037).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from .auth import AuthenticatedUser, get_current_user
from .routes import approvals, executive, incidents, predictions


def create_app() -> FastAPI:
    app = FastAPI(title="SRE Incident Platform API Gateway", version="0.1.0")
    app.include_router(incidents.router)
    app.include_router(approvals.router)
    app.include_router(executive.router)
    app.include_router(predictions.router)

    @app.get("/me")
    async def me(user: AuthenticatedUser = Depends(get_current_user)):
        return {"uid": user.uid, "role": user.role, "displayName": user.display_name}

    return app


app = create_app()
