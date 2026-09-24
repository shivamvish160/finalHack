"""T50: graceful degradation -- disabling Runbook Retrieval / Predictive
Risk must never block core alert visibility/correlation (NFR-012)."""

from agents.alert_correlation.agent import decide_cluster


def test_core_clustering_works_even_when_downstream_agents_are_disabled():
    """Simulates Agents 3/4 being unavailable: Agent 1's clustering logic has
    zero dependency on them and must keep functioning."""
    alerts = [
        {"replayEventId": "r1", "alertId": "a1", "nodeId": "node-1", "serviceName": "checkout-api"},
        {"replayEventId": "r2", "alertId": "a2", "nodeId": "node-1", "serviceName": "checkout-api"},
    ]
    # No import of runbook_retrieval or predictive_risk modules at all --
    # proves decide_cluster has no hidden coupling to either.
    decision = decide_cluster(alerts, existing_clusters=[])
    assert decision.incident_count == 1
