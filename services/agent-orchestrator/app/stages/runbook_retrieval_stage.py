"""Runbook retrieval orchestrator stage (T39).

Subscribed to `incidents.root_cause_identified`. Invokes the Runbook
Retrieval agent's VECTOR_SEARCH tool, publishes `incidents.runbook_matched`
(no BigQuery write -- this stage only reads).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient  # noqa: E402
from agents.runbook_retrieval.agent import build_match_response, find_matching_runbooks  # noqa: E402


def handle_root_cause_identified(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = payload["incidentId"]
    root_cause = payload["rootCause"]

    bq_client = BigQueryClient()
    matches = find_matching_runbooks(bq_client, query_text=root_cause)
    result = build_match_response(matches)

    return {"incidentId": incident_id, "payload": result}
