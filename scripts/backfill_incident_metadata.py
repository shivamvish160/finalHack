"""One-off backfill for incidents created before the field-population fix
(commit 737fab4) -- those rows only ever got incident_id/status/started_at
written, leaving title/severity/affected_region/customer_tier_impacted
NULL forever (the INSERT-only MERGE never revisits existing rows).

Safe to re-run: only touches rows where title IS NULL, and is a no-op if
none exist. Never touches the pre-existing inc-50XX warehouse seed rows
(those already have real values).

Usage:
    export GCP_PROJECT_ID=<project>
    python3 scripts/backfill_incident_metadata.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root

from agents.common.bq_client import BigQueryClient, array_param, param  # noqa: E402

_SEVERITY_RANK = {"P1": 0, "CRITICAL": 0, "P2": 1, "WARNING": 1, "MAJOR": 1, "P3": 2, "INFO": 2, "MINOR": 2}
_TIER_RANK = {"GOLD": 0, "SILVER": 1, "BRONZE": 2}


def _worst_severity(severities: list[str]) -> str | None:
    values = [s for s in severities if s]
    if not values:
        return None
    return min(values, key=lambda s: _SEVERITY_RANK.get(s.upper(), 0))


def _fetch_customer_tier(bq: BigQueryClient, service_names: list[str]) -> str | None:
    if not service_names:
        return None
    rows = bq.query_json_rows(
        "SELECT tier FROM `sre_incident_mart.customer_accounts` WHERE service_name IN UNNEST(@service_names)",
        [array_param("service_names", "STRING", service_names)],
    )
    tiers = [r["tier"] for r in rows if r.get("tier")]
    return min(tiers, key=lambda t: _TIER_RANK.get((t or "").upper(), 0)) if tiers else None


def backfill(bq: BigQueryClient) -> None:
    incomplete = bq.query_json_rows(
        "SELECT incident_id FROM `sre_incident_mart.incidents` WHERE title IS NULL"
    )
    if not incomplete:
        print("Nothing to backfill.")
        return

    for row in incomplete:
        incident_id = row["incident_id"]
        alerts = bq.query_json_rows(
            """
            SELECT al.alert_id, al.node_id, al.service_name, al.severity, al.alert_type
            FROM `sre_incident_mart.correlated_alerts` AS ca
            JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
            WHERE ca.incident_id = @incident_id
            """,
            [param("incident_id", "STRING", incident_id)],
        )
        if not alerts:
            print(f"{incident_id}: no correlated_alerts rows found, skipping")
            continue

        affected_services = sorted({a["service_name"] for a in alerts})
        first = alerts[0]
        node_rows = bq.query_json_rows(
            "SELECT node_id, region FROM `sre_topology.network_nodes` WHERE node_id = @node_id",
            [param("node_id", "STRING", first["node_id"])],
        )
        affected_region = node_rows[0]["region"] if node_rows else None

        title = f"{first['alert_type']} on {', '.join(affected_services)}"
        severity = _worst_severity([a["severity"] for a in alerts])
        customer_tier_impacted = _fetch_customer_tier(bq, affected_services)

        bq.query(
            """
            UPDATE `sre_incident_mart.incidents`
            SET title = @title, severity = @severity, affected_region = @affected_region,
                customer_tier_impacted = @customer_tier_impacted
            WHERE incident_id = @incident_id
            """,
            [
                param("title", "STRING", title),
                param("severity", "STRING", severity),
                param("affected_region", "STRING", affected_region),
                param("customer_tier_impacted", "STRING", customer_tier_impacted),
                param("incident_id", "STRING", incident_id),
            ],
        )
        print(f"{incident_id}: backfilled title={title!r} severity={severity} region={affected_region} tier={customer_tier_impacted}")


if __name__ == "__main__":
    project_id = os.environ["GCP_PROJECT_ID"]
    backfill(BigQueryClient(project_id))
