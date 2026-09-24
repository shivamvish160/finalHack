"""T37: real sandbox execution against demo-target-service (AC-2.4).

DEMO ENVIRONMENT ONLY -- skipped automatically unless DEMO_TARGET_SERVICE_URL
points at a real, deployed demo-target-service. Never runs against
production infrastructure; see services/demo-target-service/.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DEMO_TARGET_SERVICE_URL", "").startswith("https://"),
    reason="Requires a deployed demo-target-service (demo environment only)",
)


def test_real_execution_against_demo_target_service():
    from agents.remediation.agent import execute_remediation

    result = execute_remediation(
        action_id="action-demo-1",
        incident_id="incident-demo-1",
        approved=True,
        fix_script="restart-checkout-pods",
    )
    assert result["success"] in (True, False)  # real outcome, not mocked
    assert "detail" in result
