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
    active_precedent_id,
    decide_cluster,
    fetch_known_nodes,
    fetch_precedent_incidents,
    replay_incident_id,
)
from agents.common.bq_client import BigQueryClient, array_param, param  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402

# Clustering window: alerts sharing a node/service within this many seconds
# of each other are considered part of the same storm (NFR-003 target).
CLUSTER_WINDOW_SECONDS = 300


def cluster_key_for(alert_payload: dict[str, Any]) -> str:
    """Coarse clustering bucket key -- refined by decide_cluster's actual
    node/service overlap check, this just scopes the Firestore lookup."""
    source = alert_payload["sourceAlert"]
    replay_session_id = alert_payload.get("replaySessionId")
    if replay_session_id:
        return replay_incident_id(replay_session_id)
    return source["serviceName"]


def handle_alerts_replay(payload: dict[str, Any]) -> list[dict[str, Any]]:
    bq_client = BigQueryClient()
    firestore_client = FirestoreClient()

    source = payload["sourceAlert"]
    replay_event_id = payload["replayEventId"]
    replay_session_id = payload.get("replaySessionId")
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

    results = []
    session_incident_id = replay_incident_id(replay_session_id) if replay_session_id else None
    for cluster in decision.clusters:
        incident_id = session_incident_id or _incident_id_for_cluster(bq_client, cluster) or str(uuid.uuid4())
        _write_incident_and_correlations(bq_client, incident_id, cluster, known_nodes)
        if not replay_session_id:
            results.append(
                {
                    "incidentId": incident_id,
                    "payload": {
                        "correlatedAlertIds": [a["alertId"] for a in cluster],
                        "affectedServices": sorted({a["serviceName"] for a in cluster}),
                    },
                }
            )

    if session_incident_id:
        results = [
            {
                "incidentId": session_incident_id,
                "payload": {
                    "correlatedAlertIds": [a["alertId"] for cluster in decision.clusters for a in cluster],
                    "affectedServices": sorted(
                        {a["serviceName"] for cluster in decision.clusters for a in cluster}
                    ),
                },
            }
        ]

    firestore_client.add_pending_alert(cluster_key, replay_event_id, alert)
    return results


def _incident_id_for_cluster(bq_client: BigQueryClient, cluster: list[dict[str, Any]]) -> str | None:
    node_ids = list({a["nodeId"] for a in cluster})
    service_names = list({a["serviceName"] for a in cluster})
    precedents = fetch_precedent_incidents(bq_client, node_ids, service_names)
    return active_precedent_id(precedents)


def _write_incident_and_correlations(
    bq_client: BigQueryClient,
    incident_id: str,
    cluster: list[dict[str, Any]],
    known_nodes: dict[str, Any],
) -> None:
    affected_services = sorted({a["serviceName"] for a in cluster})
    first_alert = cluster[0]
    node = known_nodes.get(first_alert["nodeId"], {})

    title = f"{first_alert['alertType']} on {', '.join(affected_services)}"
    severity = _worst_severity(a["severity"] for a in cluster)
    affected_region = node.get("region")
    customer_tier_impacted = _fetch_customer_tier(bq_client, affected_services)

    merge_incident_sql = """
        MERGE `sre_incident_mart.incidents` T
        USING (SELECT @incident_id AS incident_id) S
        ON T.incident_id = S.incident_id
        WHEN NOT MATCHED THEN
          INSERT (incident_id, status, started_at, title, severity, affected_region, customer_tier_impacted)
          VALUES (@incident_id, @initial_status, CURRENT_TIMESTAMP(), @title, @severity, @affected_region, @customer_tier_impacted)
    """
    bq_client.query(
        merge_incident_sql,
        [
            param("incident_id", "STRING", incident_id),
            param("initial_status", "STRING", "Open"),
            param("title", "STRING", title),
            param("severity", "STRING", severity),
            param("affected_region", "STRING", affected_region),
            param("customer_tier_impacted", "STRING", customer_tier_impacted),
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


# Highest-priority-first ranking covering both alert_stream's raw severity
# values and the incidents table's own P1/P2/P3 scheme -- unrecognized
# values still sort deterministically (worst-case, rank 0) rather than
# crashing on an unexpected label.
_SEVERITY_RANK = {"P1": 0, "CRITICAL": 0, "P2": 1, "WARNING": 1, "MAJOR": 1, "P3": 2, "INFO": 2, "MINOR": 2}


def _worst_severity(severities: Any) -> str | None:
    values = list(severities)
    if not values:
        return None
    return min(values, key=lambda s: _SEVERITY_RANK.get((s or "").upper(), 0))


def _fetch_customer_tier(bq_client: BigQueryClient, service_names: list[str]) -> str | None:
    """Highest customer tier (GOLD > SILVER > BRONZE) among accounts linked
    to any of this incident's affected services (FR-027-adjacent -- same
    join key used by the Executive Impact agent)."""
    sql = """
        SELECT tier
        FROM `sre_incident_mart.customer_accounts`
        WHERE service_name IN UNNEST(@service_names)
    """
    rows = bq_client.query_json_rows(sql, [array_param("service_names", "STRING", service_names)])
    tiers = [r["tier"] for r in rows if r.get("tier")]
    if not tiers:
        return None
    tier_rank = {"GOLD": 0, "SILVER": 1, "BRONZE": 2}
    return min(tiers, key=lambda t: tier_rank.get((t or "").upper(), 0))
