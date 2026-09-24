"""T20: contract test for the alerts.replay Pub/Sub envelope shape (contracts/pubsub-events.md)."""

import uuid
from datetime import datetime, timezone

from tests._pkgload import load_submodule

_replay = load_submodule("alert_replay_app", "services/alert-replay-service/app", "replay")
build_replay_envelope = _replay.build_replay_envelope


def _sample_alert_row() -> dict:
    return {
        "alert_id": "alert-001",
        "node_id": "node-42",
        "service_name": "checkout-api",
        "severity": "critical",
        "alert_type": "latency_spike",
        "message": "p99 latency exceeded threshold",
        "measured_value": 950.2,
        "timestamp": "2026-09-24T10:00:00Z",
    }


def test_envelope_has_fresh_replay_event_id_distinct_from_alert_id():
    envelope = build_replay_envelope(_sample_alert_row())
    assert "replayEventId" in envelope["payload"]
    assert envelope["payload"]["replayEventId"] != envelope["payload"]["sourceAlert"]["alertId"]
    # must be a valid UUID
    uuid.UUID(envelope["payload"]["replayEventId"])


def test_envelope_rewrites_occurred_at_timestamp():
    row = _sample_alert_row()
    envelope = build_replay_envelope(row)
    occurred_at = datetime.fromisoformat(envelope["payload"]["sourceAlert"]["originalTimestamp"].replace("Z", "+00:00"))
    assert occurred_at.tzinfo is not None


def test_envelope_preserves_source_alert_fields():
    row = _sample_alert_row()
    envelope = build_replay_envelope(row)
    source = envelope["payload"]["sourceAlert"]
    assert source["alertId"] == row["alert_id"]
    assert source["nodeId"] == row["node_id"]
    assert source["serviceName"] == row["service_name"]
    assert source["severity"] == row["severity"]


def test_two_replays_of_the_same_row_get_different_replay_event_ids():
    row = _sample_alert_row()
    e1 = build_replay_envelope(row)
    e2 = build_replay_envelope(row)
    assert e1["payload"]["replayEventId"] != e2["payload"]["replayEventId"]
