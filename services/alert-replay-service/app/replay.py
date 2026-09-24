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

from agents.common.bq_client import BigQueryClient  # noqa: E402
from google.cloud import pubsub_v1  # noqa: E402


def build_replay_envelope(alert_row: dict[str, Any]) -> dict[str, Any]:
    """Wrap one `alert_stream` row into an `alerts.replay` Pub/Sub envelope
    (contracts/pubsub-events.md)."""
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": "alerts.replay",
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "incidentId": None,
        "payload": {
            "replayEventId": str(uuid.uuid4()),
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


def run_replay_loop(target_msgs_per_minute: int = 1000) -> None:
    """Continuously replay `alert_stream` rows to the `alerts.replay` topic,
    looping over the finite row set to sustain the target throughput."""
    project_id = os.environ["GCP_PROJECT_ID"]
    bq_client = BigQueryClient(project_id)
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, os.environ.get("PUBSUB_TOPIC_ALERTS_REPLAY", "alerts.replay"))

    rows = list(fetch_alert_stream_rows(bq_client))
    if not rows:
        raise RuntimeError("sre_telemetry.alert_stream returned zero rows -- nothing to replay")

    interval_seconds = 60.0 / target_msgs_per_minute
    index = 0
    while True:
        row = rows[index % len(rows)]
        envelope = build_replay_envelope(row)
        publisher.publish(topic_path, _to_json_bytes(envelope))
        index += 1
        time.sleep(interval_seconds)


def _to_json_bytes(envelope: dict[str, Any]) -> bytes:
    import json

    return json.dumps(envelope).encode("utf-8")


if __name__ == "__main__":
    run_replay_loop(int(os.environ.get("ALERT_REPLAY_TARGET_MSGS_PER_MINUTE", "1000")))
