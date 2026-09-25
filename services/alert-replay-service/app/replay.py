"""Alert replay service (T24, FR-004).

The ONLY reader of `sre_telemetry.alert_stream` at the raw-row level; never
mutates it (FR-039). Loops over the existing ~3,000 rows (ordered by
timestamp) at a controlled rate to sustain >=1,000 msgs/min (NFR-001),
wrapping each occurrence in an envelope carrying a freshly generated
`replayEventId` and a rewritten `occurredAt` timestamp -- distinct from the
row's natural `alert_id` -- per spec.md Clarification #2, so looping over
the finite row set never gets mistaken for repeats of the same original
alert (FR-004).
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root, for `agents.common.*`

from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from google.cloud import pubsub_v1  # noqa: E402


def build_replay_envelope(alert_row: dict[str, Any], replay_session_id: str | None = None) -> dict[str, Any]:
    """Wrap one `alert_stream` row into an `alerts.replay` Pub/Sub envelope
    (contracts/pubsub-events.md)."""
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": "alerts.replay",
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "incidentId": None,
        "payload": {
            "replayEventId": str(uuid.uuid4()),
            "replaySessionId": replay_session_id or str(uuid.uuid4()),
            "sourceAlert": {
                "alertId": alert_row["alert_id"],
                "nodeId": alert_row["node_id"],
                "serviceName": alert_row["service_name"],
                "severity": alert_row["severity"],
                "alertType": alert_row["alert_type"],
                "message": alert_row.get("message", ""),
                "measuredValue": alert_row.get("measured_value"),
                "originalTimestamp": str(alert_row["timestamp"]),
            },
        },
    }


def fetch_alert_stream_rows(client: BigQueryClient) -> Iterator[dict[str, Any]]:
    """Read-only SELECT over the existing `sre_telemetry.alert_stream` table,
    ordered by timestamp (FR-004). Never writes back."""
    sql = """
        SELECT alert_id, node_id, service_name, severity, alert_type,
               message, measured_value, timestamp
        FROM `sre_telemetry.alert_stream`
        ORDER BY timestamp
    """
    yield from client.query_json_rows(sql)


def run_replay_loop(
    target_msgs_per_minute: int = 1000,
    duration_seconds: float | None = None,
    wait_for_incidents_seconds: float = 0,
) -> None:
    """Continuously replay `alert_stream` rows to the `alerts.replay` topic,
    looping over the finite row set to sustain the target throughput.

    `duration_seconds=None` runs forever (matches the always-on deployed
    Cloud Run service); pass a value to auto-stop after that many seconds
    (useful for local/manual test runs)."""
    project_id = os.environ["GCP_PROJECT_ID"]
    bq_client = BigQueryClient(project_id)
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, os.environ.get("PUBSUB_TOPIC_ALERTS_REPLAY", "alerts.replay"))

    rows = list(fetch_alert_stream_rows(bq_client))
    if not rows:
        raise RuntimeError("sre_telemetry.alert_stream returned zero rows -- nothing to replay")

    interval_seconds = 60.0 / target_msgs_per_minute
    replay_session_id = str(uuid.uuid4())
    print(f"Replay session: {replay_session_id}", flush=True)
    replay_started_at = datetime.now(timezone.utc)
    start_time = time.monotonic()
    index = 0
    publish_futures = []
    while duration_seconds is None or (time.monotonic() - start_time) < duration_seconds:
        row = rows[index % len(rows)]
        envelope = build_replay_envelope(row, replay_session_id)
        publish_futures.append(publisher.publish(topic_path, _to_json_bytes(envelope)))
        if len(publish_futures) % 50 == 0:
            print(f"Queued {len(publish_futures)} alerts so far...", flush=True)
        index += 1
        time.sleep(interval_seconds)

    message_ids = [future.result(timeout=60) for future in publish_futures]
    publisher.stop()
    print(f"Done: Pub/Sub acknowledged {len(message_ids)} alerts on {topic_path}.", flush=True)

    if wait_for_incidents_seconds:
        deadline = time.monotonic() + wait_for_incidents_seconds
        while time.monotonic() < deadline:
            incidents = bq_client.query_json_rows(
                """
                SELECT incident_id, title, status, started_at
                FROM `sre_incident_mart.incidents`
                WHERE started_at >= @replay_started_at
                ORDER BY started_at DESC
                """,
                [param("replay_started_at", "TIMESTAMP", replay_started_at)],
            )
            if incidents:
                print(f"Created {len(incidents)} incident(s):", flush=True)
                for incident in incidents:
                    print(
                        f"  {incident['incident_id']} | {incident.get('status')} | {incident.get('title')}",
                        flush=True,
                    )
                return
            time.sleep(2)
        raise RuntimeError(
            f"Pub/Sub accepted {len(message_ids)} alerts, but no new BigQuery incident appeared "
            f"within {wait_for_incidents_seconds:g}s. Check agent-orchestrator-alerts logs."
        )


def _to_json_bytes(envelope: dict[str, Any]) -> bytes:
    import json

    return json.dumps(envelope).encode("utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Replay sre_telemetry.alert_stream to the alerts.replay Pub/Sub topic.")
    parser.add_argument("--rate", type=int, default=int(os.environ.get("ALERT_REPLAY_TARGET_MSGS_PER_MINUTE", "1000")),
                         help="Target messages per minute (default: 1000, or ALERT_REPLAY_TARGET_MSGS_PER_MINUTE env var).")
    parser.add_argument("--duration-seconds", type=float, default=None,
                         help="Stop after this many seconds. Omit to run forever (matches the deployed service).")
    parser.add_argument("--duration-minutes", type=float, default=None,
                         help="Stop after this many minutes (alternative to --duration-seconds).")
    parser.add_argument("--wait-for-incidents-seconds", type=float, default=60,
                         help="After a bounded run, wait this long for a new BigQuery incident (default: 60).")
    args = parser.parse_args()

    duration = args.duration_seconds
    if duration is None and args.duration_minutes is not None:
        duration = args.duration_minutes * 60

    run_replay_loop(args.rate, duration, args.wait_for_incidents_seconds if duration is not None else 0)
