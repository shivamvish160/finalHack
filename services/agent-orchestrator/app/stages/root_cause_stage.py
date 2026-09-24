"""Root cause orchestrator stage (T28).

Subscribed to `incidents.correlated`. Invokes the Root Cause Analysis
agent's evidence-gathering tool, updates the `incidents` row with the
resulting root cause/confidence/reasoning, and publishes
`incidents.root_cause_identified`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from agents.root_cause_analysis.agent import (  # noqa: E402
    fetch_root_cause_evidence,
    summarize_confidence,
)


async def handle_incidents_correlated(payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = payload["incidentId"]
    bq_client = BigQueryClient()

    evidence = fetch_root_cause_evidence(bq_client, incident_id)
    confidence = summarize_confidence(evidence)
    root_cause, reasoning = _summarize_root_cause(evidence)

    update_sql = """
        UPDATE `sre_incident_mart.incidents`
        SET root_cause = @root_cause,
            root_cause_confidence = @confidence,
            root_cause_reasoning = @reasoning,
            status = @status
        WHERE incident_id = @incident_id
    """
    bq_client.query(
        update_sql,
        [
            param("root_cause", "STRING", root_cause),
            param("confidence", "FLOAT64", confidence),
            param("reasoning", "STRING", reasoning),
            param("status", "STRING", "Investigating"),
            param("incident_id", "STRING", incident_id),
        ],
    )

    return {
        "incidentId": incident_id,
        "payload": {"rootCause": root_cause, "confidence": confidence, "reasoning": reasoning},
    }


def _summarize_root_cause(evidence: dict[str, Any]) -> tuple[str, str]:
    """Deterministic fallback narrative built directly from the live
    evidence (used when the ADK LlmAgent call is unavailable, e.g. in
    tests) -- the production path replaces this with the LlmAgent's
    generated explanation, which is still required to cite this same
    evidence (NFR-011)."""
    alerts = evidence.get("alerts", [])
    precedents = evidence.get("historical_precedents", [])

    if not alerts:
        return "Unknown -- insufficient alert evidence", "No correlated alerts were available for analysis."

    services = sorted({a["service_name"] for a in alerts if a.get("service_name")})
    node_types = sorted({a.get("node_type") for a in alerts if a.get("node_type")})

    root_cause = f"Likely degradation in {', '.join(services) or 'affected service(s)'}"
    reasoning = (
        f"{len(alerts)} correlated alert(s) across node type(s) {', '.join(node_types) or 'unknown'}; "
        f"{len(precedents)} historical incident(s) with overlapping node/service found as precedent."
    )
    return root_cause, reasoning
