"""T49: load test driver publishing >=1000 alerts.replay messages/minute.

Standalone script (not itself a pytest test) -- see
tests/integration/test_load_1000_per_min.py for the pytest wrapper that
invokes this against a real deployed alert-replay-service/Pub/Sub setup.
"""

from __future__ import annotations

import argparse
import os
import time

from google.cloud import pubsub_v1


def publish_synthetic_burst(project_id: str, topic_name: str, target_msgs_per_minute: int, duration_seconds: int) -> int:
    """Publish synthetic alerts.replay-shaped messages at the target rate for
    `duration_seconds`, returning the total count published."""
    import json
    import uuid
    from datetime import datetime, timezone

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    interval = 60.0 / target_msgs_per_minute

    count = 0
    deadline = time.monotonic() + duration_seconds
    while time.monotonic() < deadline:
        envelope = {
            "eventId": str(uuid.uuid4()),
            "eventType": "alerts.replay",
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "incidentId": None,
            "payload": {
                "replayEventId": str(uuid.uuid4()),
                "sourceAlert": {
                    "alertId": f"load-test-{count}",
                    "nodeId": "node-load-test",
                    "serviceName": "load-test-service",
                    "severity": "warning",
                    "alertType": "synthetic_load",
                    "message": "synthetic load-test alert",
                    "measuredValue": 1.0,
                    "originalTimestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        }
        publisher.publish(topic_path, json.dumps(envelope).encode("utf-8"))
        count += 1
        time.sleep(interval)

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT_ID"))
    parser.add_argument("--topic", default=os.environ.get("PUBSUB_TOPIC_ALERTS_REPLAY", "alerts.replay"))
    parser.add_argument("--rate", type=int, default=1000, help="target msgs/minute")
    parser.add_argument("--duration", type=int, default=300, help="seconds to run")
    args = parser.parse_args()

    total = publish_synthetic_burst(args.project, args.topic, args.rate, args.duration)
    print(f"Published {total} messages over {args.duration}s (target {args.rate}/min)")
