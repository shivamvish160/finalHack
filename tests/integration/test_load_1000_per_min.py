"""T49: integration test validating the >=1000 alerts/minute target is
achievable given the quantified autoscaling config (research.md §17).

DEMO/STAGING ENVIRONMENT ONLY -- requires a real deployed Pub/Sub topic +
subscriptions; skipped otherwise. Asserts the publish-side rate itself
(the receive-side DLQ-count assertion requires live Cloud Monitoring
access and is exercised manually per quickstart.md, not in CI).
"""

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_LOAD_TEST"),
    reason="Requires a deployed alerts.replay topic; set RUN_LIVE_LOAD_TEST=1 to run",
)


def test_publish_rate_sustains_1000_per_minute():
    from scripts.demo.load_test_alerts import publish_synthetic_burst

    start = time.monotonic()
    count = publish_synthetic_burst(
        project_id=os.environ["GCP_PROJECT_ID"],
        topic_name=os.environ.get("PUBSUB_TOPIC_ALERTS_REPLAY", "alerts.replay"),
        target_msgs_per_minute=1000,
        duration_seconds=60,
    )
    elapsed = time.monotonic() - start
    achieved_rate = count / (elapsed / 60.0)
    assert achieved_rate >= 950  # allow small scheduling jitter under the 1000 target
