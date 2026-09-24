"""T56: verify executive-impact figures match the documented formulas
(data-model.md §7) given a fixture incident linked to customer_accounts."""

from agents.executive_impact.agent import compute_business_impact


def test_revenue_and_customer_count_scale_with_linked_accounts():
    accounts = [
        {"customer_id": "c1", "monthly_recurring_revenue": 1000.0, "user_count": 50, "sla_uptime_target_pct": 99.9, "sla_credit_rate_per_hour": 10.0},
        {"customer_id": "c2", "monthly_recurring_revenue": 2000.0, "user_count": 100, "sla_uptime_target_pct": 99.9, "sla_credit_rate_per_hour": 20.0},
    ]
    impact = compute_business_impact(accounts, incident_duration_hours=2.0)

    assert impact["affectedCustomers"] == 2
    assert impact["affectedUsers"] == 150
    assert impact["revenueAtRisk"] > 0
    assert impact["slaCreditExposure"] == (10.0 + 20.0) * 2.0


def test_zero_accounts_yields_zero_impact_not_an_error():
    impact = compute_business_impact([], incident_duration_hours=1.0)
    assert impact["affectedCustomers"] == 0
    assert impact["revenueAtRisk"] == 0
    assert impact["slaCreditExposure"] == 0
