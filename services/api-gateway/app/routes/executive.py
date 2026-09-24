"""Executive summary REST endpoint (T60, User Story 4 -- see tasks.md).

Full computation logic lands with User Story 4's Executive Impact agent.
This module exists now so services/api-gateway/app/main.py can import it;
the read below is already real/functional against Firestore.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from agents.common.firestore_client import FirestoreClient  # noqa: E402

from ..auth import (  # noqa: E402
    ROLE_ADMINISTRATOR,
    ROLE_EXECUTIVE_VIEWER,
    ROLE_INCIDENT_COMMANDER,
    require_roles,
)

router = APIRouter(prefix="/executive", tags=["executive"])


@router.get("/summary")
async def get_executive_summary(
    _user=Depends(require_roles(ROLE_EXECUTIVE_VIEWER, ROLE_INCIDENT_COMMANDER, ROLE_ADMINISTRATOR)),
) -> dict[str, Any]:
    metrics = FirestoreClient().get_executive_metrics()
    return metrics or {}
