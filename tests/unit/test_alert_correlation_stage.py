from agents.alert_correlation.agent import active_precedent_id


def test_resolved_precedents_are_not_reused_regardless_of_case():
    precedents = [
        {"incident_id": "inc-resolved-upper", "status": "RESOLVED"},
        {"incident_id": "inc-resolved-title", "status": "Resolved"},
        {"incident_id": "inc-closed", "status": "CLOSED"},
    ]

    assert active_precedent_id(precedents) is None


def test_most_recent_active_precedent_is_reused():
    precedents = [
        {"incident_id": "inc-monitoring", "status": "MONITORING"},
        {"incident_id": "inc-open", "status": "Open"},
    ]

    assert active_precedent_id(precedents) == "inc-monitoring"
