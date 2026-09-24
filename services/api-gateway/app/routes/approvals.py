"""Approval workflow REST endpoints (T42, FR-017/FR-018, NFR-009).

`POST /approvals/{actionId}/decision` is the ONLY code path that can lead
to real execution (research.md §12) -- it never executes anything
synchronously itself; it updates Firestore, writes the FR-037 audit entry,
then publishes `remediation.approved`/`remediation.rejected` for the
orchestrator's execute/rejected stages to react to.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from agents.common.audit_log import log_approval_decision  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402

from ..auth import (  # noqa: E402
    AuthenticatedUser,
    ROLE_ADMINISTRATOR,
    ROLE_APPROVER,
    ROLE_INCIDENT_COMMANDER,
    require_roles,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])

_ALLOWED_ROLES = (ROLE_APPROVER, ROLE_INCIDENT_COMMANDER, ROLE_ADMINISTRATOR)


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comments: str = ""


def _publish(topic: str, payload: dict[str, Any]) -> None:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(os.environ["GCP_PROJECT_ID"], topic)
    import json

    publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))


@router.get("")
async def list_pending_approvals(
    status: str = "pending", _user: AuthenticatedUser = Depends(require_roles(*_ALLOWED_ROLES))
) -> list[dict[str, Any]]:
    if status != "pending":
        return []
    return FirestoreClient().list_pending_approvals()


@router.post("/{action_id}/decision")
async def decide_approval(
    action_id: str,
    body: DecisionRequest,
    user: AuthenticatedUser = Depends(require_roles(*_ALLOWED_ROLES)),
) -> dict[str, Any]:
    firestore_client = FirestoreClient()
    approval = firestore_client.get_approval(action_id)
    if approval is None:
        raise HTTPException(404, detail="Approval action not found")

    firestore_client.decide_approval(action_id, body.decision, user.uid, body.comments)
    log_approval_decision(user.uid, action_id, approval["incidentId"], body.decision, body.comments)

    topic = "remediation.approved" if body.decision == "approve" else "remediation.rejected"
    _publish(topic, {"incidentId": approval["incidentId"], "payload": {"actionId": action_id}})

    return {"actionId": action_id, "decision": body.decision, "decidedAt": None}
