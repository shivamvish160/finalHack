"""T56: verify executive-impact figures match the documented formulas
(data-model.md §7) given a fixture incident linked to customer_accounts."""

from agents.executive_impact.agent import compute_business_impact, compute_resolution_success_rate


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


class _FakeBQClient:
    """Fixture BQ client returning a fixed succeeded/total split so
    compute_resolution_success_rate's percentage math can be verified
    without live BigQuery credentials (TD-5 review finding)."""

    def __init__(self, succeeded: int, total: int) -> None:
        self._succeeded = succeeded
        self._total = total

    def query_json_rows(self, sql, params=()):  # noqa: ANN001, ARG002
        return [{"succeeded_count": self._succeeded, "total_count": self._total}]


def test_resolution_success_rate_computes_percentage():
    result = compute_resolution_success_rate(_FakeBQClient(succeeded=3, total=4))
    assert result["resolutionSuccessRatePct"] == 75.0


def test_resolution_success_rate_zero_remediations_is_zero_not_an_error():
    result = compute_resolution_success_rate(_FakeBQClient(succeeded=0, total=0))
    assert result["resolutionSuccessRatePct"] == 0.0

