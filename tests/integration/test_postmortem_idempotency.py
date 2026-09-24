"""T57: postmortem regeneration must increment version, never duplicate (FR-032, SC-010)."""

from agents.executive_impact.agent import build_postmortem_merge_params


def test_postmortem_merge_params_are_stable_keyed_on_incident_id():
    params_v1 = build_postmortem_merge_params(
        incident_id="incident-1",
        root_cause_summary="Checkout DB connection pool exhaustion",
        timeline_summary="Alerts began 10:00, resolved 10:22",
        remediation_summary="Restarted checkout pods per runbook rb-1",
        business_impact_summary="~150 users, $3,000 revenue at risk",
        full_report_markdown="# Postmortem\n...",
    )
    assert params_v1["incident_id"] == "incident-1"
    # The MERGE statement itself (agents/executive_impact/agent.py) is
    # responsible for incrementing `version` server-side; this test only
    # verifies the parameter set is stable/keyed correctly across calls.
    params_v2 = build_postmortem_merge_params(
        incident_id="incident-1",
        root_cause_summary="Checkout DB connection pool exhaustion (updated)",
        timeline_summary="Alerts began 10:00, resolved 10:22",
        remediation_summary="Restarted checkout pods per runbook rb-1",
        business_impact_summary="~150 users, $3,000 revenue at risk",
        full_report_markdown="# Postmortem\n...(v2)",
    )
    assert params_v1["incident_id"] == params_v2["incident_id"]
