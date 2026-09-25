"""Remediation propose orchestrator stage (T41).

Subscribed to `incidents.runbook_matched`. Invokes the Remediation agent's
`propose_remediation` tool ONLY (never `execute_remediation`), writes the
Firestore `approvals/{actionId}` document as Proposed, publishes
`remediation.proposed`.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402
from agents.remediation.agent import propose_remediation  # noqa: E402


async def handle_runbook_matched(payload: dict[str, Any]) -> dict[str, Any] | None:
    incident_id = payload["incidentId"]

    if payload.get("belowThreshold"):
        # No confident runbook match -- nothing to propose (AC-2.5); the
        # incident stays actionable for manual investigation.
        return None

    bq_client = BigQueryClient()
    proposal = propose_remediation(bq_client, runbook_id=payload["runbookId"])

    action_id = str(uuid.uuid4())
    FirestoreClient().create_approval(
        action_id,
        {
            "incidentId": incident_id,
            "runbookId": proposal["runbookId"],
            "fixScript": proposal["fixScript"],
            "rollbackScript": proposal["rollbackScript"],
            "riskLevel": proposal["riskLevel"],
        },
    )

    return {"incidentId": incident_id, "payload": {"actionId": action_id, **proposal}}
