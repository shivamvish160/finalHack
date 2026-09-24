"""T36: the execution tool must be unreachable without a prior remediation.approved event (NFR-009)."""

import pytest

from agents.remediation.agent import execute_remediation


def test_execute_without_approval_raises():
    with pytest.raises(PermissionError):
        execute_remediation(action_id="action-1", incident_id="incident-1", approved=False)


def test_execute_with_approval_flag_false_still_raises_even_if_other_fields_look_valid():
    with pytest.raises(PermissionError):
        execute_remediation(
            action_id="action-1",
            incident_id="incident-1",
            approved=False,
            fix_script="echo ok",
        )
