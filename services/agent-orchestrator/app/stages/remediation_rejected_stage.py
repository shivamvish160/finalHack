"""Remediation rejected orchestrator stage (T44).

Subscribed to `remediation.rejected`. Returns the incident to
`Investigating` in Firestore/BigQuery with NO BigQuery remediation write --
a rejection must leave the incident actionable, never stuck (FR-021).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402


def handle_remediation_rejected(payload: dict[str, Any]) -> None:
    incident_id = payload["incidentId"]
    bq_client = BigQueryClient()

    update_sql = """
        UPDATE `sre_incident_mart.incidents`
        SET status = @status
        WHERE incident_id = @incident_id
    """
    bq_client.query(
        update_sql,
        [param("status", "STRING", "Investigating"), param("incident_id", "STRING", incident_id)],
    )
