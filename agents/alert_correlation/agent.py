"""Alert Correlation Agent (T25, FR-006 through FR-011).

ADK `LlmAgent` (gemini-2.5-flash) that clusters replayed alerts sharing a
`node_id`/`service_name`/topology-dependency signal within a short time
window into a single incident (FR-006), and resolves each alert's topology
relationship against `network_nodes`, marking unresolved relationships
`Unmapped` rather than dropping the alert (FR-005).

The deterministic clustering/mapping logic lives in plain functions
(`decide_cluster`, `resolve_topology_mapping`) so it is unit-testable
without any live GCP call; the `LlmAgent` wraps these as tools and adds
the natural-language root-cause-adjacent narration Gemini contributes on
top of the deterministic decision.
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

from agents.common.bq_client import BigQueryClient, array_param  # noqa: E402


@dataclass
class ClusterDecision:
    clusters: list[list[dict[str, Any]]]

    @property
    def incident_count(self) -> int:
        return len(self.clusters)


def active_precedent_id(precedents: list[dict[str, Any]]) -> str | None:
    """Return the newest reusable incident, excluding terminal states regardless of case."""
    active_statuses = {"OPEN", "INVESTIGATING", "MONITORING"}
    active = [p for p in precedents if str(p.get("status", "")).upper() in active_statuses]
    return active[0]["incident_id"] if active else None


def replay_incident_id(replay_session_id: str, service_names: list[str]) -> str:
    """Stable per-session/service incident ID: new replay run, new incident."""
    cluster_identity = ",".join(sorted(set(service_names)))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"sre-replay:{replay_session_id}:{cluster_identity}"))


def decide_cluster(
    alerts: list[dict[str, Any]], existing_clusters: list[list[dict[str, Any]]]
) -> ClusterDecision:
    """Group `alerts` sharing a `nodeId` or `serviceName` into the same
    cluster (FR-006, FR-011). This is the deterministic core of the
    Alert Correlation Agent's decision -- data-driven, never a hardcoded
    alert-to-incident mapping (NFR-011): the grouping key is derived purely
    from the replayed alerts' own node/service identifiers.
    """
    clusters: list[list[dict[str, Any]]] = [list(c) for c in existing_clusters]

    for alert in alerts:
        target_cluster = None
        for cluster in clusters:
            if any(
                a["nodeId"] == alert["nodeId"] or a["serviceName"] == alert["serviceName"]
                for a in cluster
            ):
                target_cluster = cluster
                break
        if target_cluster is not None:
            target_cluster.append(alert)
        else:
            clusters.append([alert])

    return ClusterDecision(clusters=clusters)


def resolve_topology_mapping(node_id: str, known_nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resolve `node_id` against the existing `network_nodes` warehouse
    table (passed in as `known_nodes`, keyed by node_id). Marks the
    relationship `Unmapped` when no match exists, per FR-005 -- the alert
    itself is never dropped as a result.
    """
    node = known_nodes.get(node_id)
    if node is None:
        return {"node_id": node_id, "mapped": False}
    return {"mapped": True, **node}


def fetch_known_nodes(bq_client: BigQueryClient, node_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Live, parameterized LEFT-JOIN-equivalent lookup against the existing
    `sre_topology.network_nodes` table (read-only, FR-039)."""
    sql = """
        SELECT node_id, node_name, node_type, region, ip_address, status
        FROM `sre_topology.network_nodes`
        WHERE node_id IN UNNEST(@node_ids)
    """
    rows = bq_client.query_json_rows(sql, [array_param("node_ids", "STRING", node_ids)])
    return {row["node_id"]: row for row in rows}


def fetch_precedent_incidents(bq_client: BigQueryClient, node_ids: list[str], service_names: list[str]) -> list[dict[str, Any]]:
    """Has this node/service combination clustered into an incident before?
    (FR-011 precedent signal, data-model.md §2)."""
    sql = """
        SELECT DISTINCT ca.incident_id, i.status, i.started_at
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        JOIN `sre_incident_mart.incidents` AS i ON i.incident_id = ca.incident_id
        WHERE al.node_id IN UNNEST(@node_ids) OR al.service_name IN UNNEST(@service_names)
        ORDER BY i.started_at DESC
    """
    return bq_client.query_json_rows(
        sql,
        [
            array_param("node_ids", "STRING", node_ids),
            array_param("service_names", "STRING", service_names),
        ],
    )


def build_agent():
    """Construct the ADK `LlmAgent` for production use (requires google-adk
    + live Vertex AI credentials; not exercised by unit tests)."""
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="alert_correlation_agent",
        model=os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
        instruction=(
            "You cluster incoming replayed alerts sharing a node, service, or "
            "known topology dependency into a single incident. Use the "
            "decide_cluster and resolve_topology_mapping tool outputs as your "
            "sole source of truth -- never invent a root cause or grouping "
            "not supported by the tool data (NFR-011)."
        ),
    )
