"""T22: integration test for alert clustering correctness (AC-1.1, AC-1.4).

Uses fake BigQuery/Firestore clients (no live GCP credentials required) to
exercise the Alert Correlation agent's clustering decision logic in
isolation from real GCP services.
"""

from agents.alert_correlation.agent import decide_cluster


def _alert(alert_id: str, node_id: str, service_name: str) -> dict:
    return {
        "replayEventId": f"replay-{alert_id}",
        "alertId": alert_id,
        "nodeId": node_id,
        "serviceName": service_name,
        "severity": "critical",
        "alertType": "latency_spike",
    }


def test_related_alerts_cluster_into_one_incident():
    related_alerts = [_alert(f"a{i}", "node-42", "checkout-api") for i in range(1, 6)]
    decision = decide_cluster(related_alerts, existing_clusters=[])
    assert decision.incident_count == 1
    assert len(decision.clusters[0]) == 5


def test_unrelated_alerts_form_separate_incidents():
    alerts = [
        _alert("a1", "node-1", "checkout-api"),
        _alert("a2", "node-1", "checkout-api"),
        _alert("b1", "node-99", "billing-service"),
        _alert("b2", "node-99", "billing-service"),
    ]
    decision = decide_cluster(alerts, existing_clusters=[])
    assert decision.incident_count == 2


def test_single_alert_still_forms_an_incident():
    decision = decide_cluster([_alert("a1", "node-1", "checkout-api")], existing_clusters=[])
    assert decision.incident_count == 1
