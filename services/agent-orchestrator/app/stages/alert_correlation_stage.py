"""Alert correlation orchestrator stage (T26).

Subscribed to `alerts.replay`. Maintains the short-TTL Firestore
`pending_alerts` clustering window, invokes the Alert Correlation agent's
deterministic clustering + topology-mapping tools, writes
`correlated_alerts`/`incidents` (the only two FR-039 tables this stage
touches), then publishes `incidents.correlated` -- BigQuery write happens
BEFORE the Firestore projection update and BEFORE publishing, per
design.md §3.2/§8's ordering rule.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.alert_correlation.agent import (  # noqa: E402
    decide_cluster,
    fetch_known_nodes,
    fetch_precedent_incidents,
)
from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402

# Clustering window: alerts sharing a node/service within this many seconds
# of each other are considered part of the same storm (NFR-003 target).
CLUSTER_WINDOW_SECONDS = 300


def cluster_key_for(alert_payload: dict[str, Any]) -> str:
    """Coarse clustering bucket key -- refined by decide_cluster's actual
    node/service overlap check, this just scopes the Firestore lookup."""
    source = alert_payload["sourceAlert"]
    return f"{source['serviceName']}"


async def handle_alerts_replay(payload: dict[str, Any]) -> None:
    bq_client = BigQueryClient()
    firestore_client = FirestoreClient()

    source = payload["sourceAlert"]
    replay_event_id = payload["replayEventId"]
    alert = {
        "replayEventId": replay_event_id,
        "alertId": source["alertId"],
        "nodeId": source["nodeId"],
        "serviceName": source["serviceName"],
        "severity": source["severity"],
        "alertType": source["alertType"],
    }

    cluster_key = cluster_key_for(payload)
    pending = firestore_client.get_pending_cluster(cluster_key)
    window_alerts = (pending or {}).get("alerts", []) + [alert]

    decision = decide_cluster(window_alerts, existing_clusters=[])
    node_ids = [a["nodeId"] for cluster in decision.clusters for a in cluster]
    known_nodes = fetch_known_nodes(bq_client, node_ids)

    for cluster in decision.clusters:
        incident_id = _incident_id_for_cluster(bq_client, cluster) or str(uuid.uuid4())
        _write_incident_and_correlations(bq_client, incident_id, cluster, known_nodes)

    firestore_client.add_pending_alert(cluster_key, replay_event_id, alert)


def _incident_id_for_cluster(bq_client: BigQueryClient, cluster: list[dict[str, Any]]) -> str | None:
    node_ids = list({a["nodeId"] for a in cluster})
    service_names = list({a["serviceName"] for a in cluster})
    precedents = fetch_precedent_incidents(bq_client, node_ids, service_names)
    open_precedents = [p for p in precedents if p.get("status") not in ("Resolved", "Closed")]
    return open_precedents[0]["incident_id"] if open_precedents else None


def _write_incident_and_correlations(
    bq_client: BigQueryClient,
    incident_id: str,
    cluster: list[dict[str, Any]],
    known_nodes: dict[str, Any],
) -> None:
    affected_services = sorted({a["serviceName"] for a in cluster})

    merge_incident_sql = """
        MERGE `sre_incident_mart.incidents` T
        USING (SELECT @incident_id AS incident_id) S
        ON T.incident_id = S.incident_id
        WHEN NOT MATCHED THEN
          INSERT (incident_id, status, started_at)
          VALUES (@incident_id, @initial_status, CURRENT_TIMESTAMP())
    """
    bq_client.query(
        merge_incident_sql,
        [
            param("incident_id", "STRING", incident_id),
            param("initial_status", "STRING", "Open"),
        ],
    )

    for alert in cluster:
        insert_link_sql = """
            MERGE `sre_incident_mart.correlated_alerts` T
            USING (SELECT @incident_id AS incident_id, @alert_id AS alert_id) S
            ON T.incident_id = S.incident_id AND T.alert_id = S.alert_id
            WHEN NOT MATCHED THEN
              INSERT (incident_id, alert_id) VALUES (@incident_id, @alert_id)
        """
        bq_client.query(
            insert_link_sql,
            [
                param("incident_id", "STRING", incident_id),
                param("alert_id", "STRING", alert["alertId"]),
            ],
        )
