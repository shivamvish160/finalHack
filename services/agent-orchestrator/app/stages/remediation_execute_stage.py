"""Remediation execute orchestrator stage (T43).

Subscribed ONLY to `remediation.approved` -- the sole event capable of
reaching `execute_remediation` (NFR-009). Appends the real outcome to
`remediation_logs`, publishes `remediation.executed`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402
from agents.common.audit_log import log_remediation_execution  # noqa: E402
from agents.remediation.agent import execute_remediation  # noqa: E402


async def handle_remediation_approved(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = payload["incidentId"]
    action_id = payload["payload"]["actionId"]

    firestore_client = FirestoreClient()
    approval = firestore_client.get_approval(action_id)
    if approval is None:
        raise ValueError(f"No approval document found for action_id={action_id}")

    result = execute_remediation(
        action_id=action_id,
        incident_id=incident_id,
        approved=True,  # only reachable because this handler subscribes to remediation.approved
        fix_script=approval.get("fixScript"),
    )

    bq_client = BigQueryClient()
    insert_log_sql = """
        INSERT INTO `sre_incident_mart.remediation_logs` (incident_id, runbook_id, outcome, detail, executed_at)
        VALUES (@incident_id, @runbook_id, @outcome, @detail, CURRENT_TIMESTAMP())
    """
    bq_client.query(
        insert_log_sql,
        [
            param("incident_id", "STRING", incident_id),
            param("runbook_id", "STRING", approval.get("runbookId")),
            param("outcome", "STRING", "Succeeded" if result["success"] else "Failed"),
            param("detail", "STRING", result["detail"]),
        ],
    )
    firestore_client.record_execution_result(action_id, result["success"], result["detail"])
    log_remediation_execution(action_id, incident_id, result["success"], result["detail"])

    return {"incidentId": incident_id, "payload": {"actionId": action_id, **result}}
