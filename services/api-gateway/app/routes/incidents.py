"""Incident REST endpoints (T29, contracts/rest-api.md).

Implements GET /incidents, /incidents/{id}, /incidents/{id}/alerts,
/incidents/{id}/timeline, /incidents/{id}/dependency-graph. Every read
here is redacted (agents/common/redaction.py) and audited (FR-037,
closing the Analyze-phase C1 gap: incident ACCESS is now explicitly
logged here, not just approval decisions).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from agents.common.audit_log import log_incident_access  # noqa: E402
from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from agents.common.redaction import redact  # noqa: E402
from agents.runbook_retrieval.agent import build_match_response, find_matching_runbooks  # noqa: E402

from ..auth import AuthenticatedUser, get_current_user  # noqa: E402

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _bq() -> BigQueryClient:
    return BigQueryClient()


@router.get("")
async def list_incidents(
    status: str = "all", user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict[str, Any]]:
    where_clause = "" if status == "all" else "WHERE status = @status"
    sql = f"""
        SELECT incident_id, status, opened_at, root_cause, root_cause_confidence AS confidence
        FROM `sre_incident_mart.incidents`
        {where_clause}
        ORDER BY opened_at DESC
        LIMIT 200
    """
    params = [] if status == "all" else [param("status", "STRING", status)]
    rows = _bq().query_json_rows(sql, params)
    log_incident_access(user.uid, incident_id="*list*", action="list")
    return rows


@router.get("/{incident_id}")
async def get_incident(incident_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    sql = """
        SELECT incident_id, status, opened_at, resolved_at, root_cause,
               root_cause_confidence AS confidence, root_cause_reasoning AS reasoning
        FROM `sre_incident_mart.incidents`
        WHERE incident_id = @incident_id
    """
    rows = _bq().query_json_rows(sql, [param("incident_id", "STRING", incident_id)])
    log_incident_access(user.uid, incident_id, action="view")
    if not rows:
        return {"error": {"code": "not_found", "message": "Incident not found"}}
    incident = rows[0]
    incident["reasoning"] = redact(incident.get("reasoning"))
    return incident


@router.get("/{incident_id}/runbook-matches")
async def get_runbook_matches(
    incident_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> dict[str, Any]:
    incident = await get_incident(incident_id, user)
    root_cause = incident.get("root_cause") or ""
    matches = find_matching_runbooks(_bq(), query_text=root_cause) if root_cause else []
    log_incident_access(user.uid, incident_id, action="view_runbook_matches")
    return build_match_response(matches)


@router.get("/{incident_id}/alerts")
async def get_incident_alerts(
    incident_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict[str, Any]]:
    sql = """
        SELECT al.alert_id, al.node_id, al.service_name, al.severity, al.alert_type,
               al.message, al.timestamp,
               n.node_id IS NOT NULL AS mapped
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        LEFT JOIN `sre_topology.network_nodes` AS n ON n.node_id = al.node_id
        WHERE ca.incident_id = @incident_id
        ORDER BY al.timestamp
    """
    rows = _bq().query_json_rows(sql, [param("incident_id", "STRING", incident_id)])
    log_incident_access(user.uid, incident_id, action="view_alerts")
    for row in rows:
        row["message"] = redact(row.get("message"))
        row["topologyMappingStatus"] = "Mapped" if row.pop("mapped", False) else "Unmapped"
    return rows


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict[str, Any]]:
    sql = """
        SELECT al.timestamp AS event_time, 'alert' AS event_type, al.alert_id AS reference
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        WHERE ca.incident_id = @incident_id
        ORDER BY al.timestamp
    """
    rows = _bq().query_json_rows(sql, [param("incident_id", "STRING", incident_id)])
    log_incident_access(user.uid, incident_id, action="view_timeline")
    return rows


@router.get("/{incident_id}/dependency-graph")
async def get_dependency_graph(
    incident_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> dict[str, Any]:
    sql = """
        SELECT DISTINCT n.node_id, n.node_name, n.node_type, n.region, n.status,
               al.node_id IS NOT NULL AS mapped
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        LEFT JOIN `sre_topology.network_nodes` AS n ON n.node_id = al.node_id
        WHERE ca.incident_id = @incident_id
    """
    rows = _bq().query_json_rows(sql, [param("incident_id", "STRING", incident_id)])
    log_incident_access(user.uid, incident_id, action="view_dependency_graph")

    nodes = [{**r, "mapped": bool(r.pop("mapped", False) or r.get("node_id"))} for r in rows]
    # Data-driven edges: same-region/type co-occurrence within this incident
    # (design.md §6) -- never a stored, hand-authored edge table.
    edges = [
        {"from": a["node_id"], "to": b["node_id"], "basis": "same_region_type"}
        for a in nodes
        for b in nodes
        if a["node_id"] != b.get("node_id") and a.get("region") == b.get("region") and a.get("node_type") == b.get("node_type")
    ]
    return {"nodes": nodes, "edges": edges}
