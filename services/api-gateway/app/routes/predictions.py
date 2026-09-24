"""Predictive risk REST endpoints (T54 support, contracts/rest-api.md).

Reads are Firestore-only (`predictions/*`) -- the Predictive Risk Agent
never writes to BigQuery (design.md's Agent-to-Warehouse table).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from agents.common.firestore_client import FirestoreClient  # noqa: E402

from ..auth import AuthenticatedUser, get_current_user  # noqa: E402

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
async def list_predictions(
    activeOnly: bool = True, _user: AuthenticatedUser = Depends(get_current_user)  # noqa: N803
) -> list[dict[str, Any]]:
    predictions = FirestoreClient().list_active_predictions()
    return [p for p in predictions if p.get("isAnomalyOnly") is not True]


@router.get("/anomalies")
async def list_anomalies(_user: AuthenticatedUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    predictions = FirestoreClient().list_active_predictions()
    return [p for p in predictions if p.get("isAnomalyOnly") is True]
