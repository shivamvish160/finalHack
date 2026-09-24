"""Root Cause Analysis Agent (T27, FR-009).

ADK `LlmAgent` (gemini-2.5-pro -- higher-reasoning model than the other 5
agents, per design.md §3.2 rationale) that joins the incident's correlated
alerts against topology and historical incident/remediation data to
produce a root cause, a confidence score, and a plain-language
explanation (NFR-010) -- entirely derived from the live query results
below, never a hardcoded alert-to-root-cause table (NFR-011).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient, array_param  # noqa: E402


def fetch_root_cause_evidence(bq_client: BigQueryClient, incident_id: str) -> dict[str, Any]:
    """Gather the live evidence set the RCA agent reasons over: this
    incident's correlated alerts joined to topology, plus historical
    incidents/remediation_logs sharing the same node/service (FR-009).
    """
    alerts_sql = """
        SELECT al.alert_id, al.node_id, al.service_name, al.severity,
               al.alert_type, al.measured_value, al.timestamp,
               n.node_name, n.node_type, n.region, n.status AS node_status
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        LEFT JOIN `sre_topology.network_nodes` AS n ON n.node_id = al.node_id
        WHERE ca.incident_id = @incident_id
    """
    alerts = bq_client.query_json_rows(alerts_sql, [_param("incident_id", incident_id)])

    node_ids = list({a["node_id"] for a in alerts if a.get("node_id")})
    service_names = list({a["service_name"] for a in alerts if a.get("service_name")})

    precedent_sql = """
        SELECT i.incident_id, i.status, r.runbook_id, r.incident_id AS remediation_incident_id
        FROM `sre_incident_mart.incidents` AS i
        LEFT JOIN `sre_incident_mart.remediation_logs` AS r ON r.incident_id = i.incident_id
        JOIN `sre_incident_mart.correlated_alerts` AS ca ON ca.incident_id = i.incident_id
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        WHERE (al.node_id IN UNNEST(@node_ids) OR al.service_name IN UNNEST(@service_names))
          AND i.incident_id != @incident_id
        ORDER BY i.incident_id DESC
        LIMIT 20
    """
    precedents = bq_client.query_json_rows(
        precedent_sql,
        [
            array_param("node_ids", "STRING", node_ids or [""]),
            array_param("service_names", "STRING", service_names or [""]),
            _param("incident_id", incident_id),
        ],
    )

    return {"alerts": alerts, "historical_precedents": precedents}


def summarize_confidence(evidence: dict[str, Any]) -> float:
    """Deterministic confidence baseline before Gemini's narrative pass:
    more corroborating alerts + more historical precedent -> higher
    confidence, capped at 0.95 (never claim absolute certainty, NFR-010).
    """
    alert_count = len(evidence.get("alerts", []))
    precedent_count = len(evidence.get("historical_precedents", []))
    raw = 0.3 + min(alert_count, 10) * 0.03 + min(precedent_count, 10) * 0.04
    return round(min(raw, 0.95), 2)


def _param(name: str, value: str):
    from google.cloud import bigquery

    return bigquery.ScalarQueryParameter(name, "STRING", value)


def build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="root_cause_analysis_agent",
        model=os.environ.get("GEMINI_MODEL_RCA", "gemini-2.5-pro"),
        instruction=(
            "Given the correlated alerts, topology, and historical incident/"
            "remediation evidence returned by fetch_root_cause_evidence, "
            "identify the single most probable root cause, cite the specific "
            "evidence supporting it, and never state a root cause not "
            "traceable to that evidence (NFR-011)."
        ),
    )
