"""api-gateway FastAPI application entrypoint.

Backend-for-Frontend for all 8 UI pages (design.md §3.1): Firebase auth +
RBAC (auth.py), REST contract (contracts/rest-api.md), sole publisher of
approval decisions, and audit logging (audit_log.py, FR-037).
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthenticatedUser, get_current_user
from .routes import approvals, executive, incidents, predictions


def create_app() -> FastAPI:
    app = FastAPI(title="SRE Incident Platform API Gateway", version="0.1.0")

    # Frontend runs as a separate Cloud Run service (different origin), so
    # every browser fetch() needs CORS headers or it's silently blocked.
    # Auth is a Bearer token (not cookies), so credentials aren't needed --
    # and browsers reject Access-Control-Allow-Origin: * combined with
    # allow_credentials=True anyway. Cloud Run exposes EVERY service under
    # both a *.a.run.app and a *.<region>.run.app hostname for the same
    # revision -- matching only one exact FRONTEND_ORIGIN string breaks
    # CORS the moment someone opens the other valid URL, so this also
    # accepts any origin matching either Cloud Run hostname pattern for a
    # service starting with "frontend-".
    allowed_origins = [o for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_origin_regex=r"https://frontend-[a-z0-9-]+\.(?:[a-z0-9-]+\.)?run\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(incidents.router)
    app.include_router(approvals.router)
    app.include_router(executive.router)
    app.include_router(predictions.router)

    @app.get("/me")
    async def me(user: AuthenticatedUser = Depends(get_current_user)):
        return {"uid": user.uid, "role": user.role, "displayName": user.display_name}

    return app


app = create_app()
