"""TD-4 (review finding): unit tests for the Predictive Risk agent's
forecast/anomaly logic (AC-3.1, AC-3.2, FR-022, FR-023) -- previously
zero coverage."""

from agents.predictive_risk.agent import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    build_anomaly_only_entries,
    build_predictions,
)


def _forecast_row(service_name: str, confidence: float) -> dict:
    return {
        "service_name": service_name,
        "forecast_timestamp": "2026-09-24T12:00:00Z",
        "forecast_value": 950.0,
        "confidence_level": confidence,
    }


def test_confident_forecast_becomes_a_prediction():
    forecasts = [_forecast_row("checkout-api", DEFAULT_CONFIDENCE_THRESHOLD + 0.1)]
    explanations = [{"service_name": "checkout-api", "explanation": "Degrading trend over past 6 hours."}]

    predictions = build_predictions(forecasts, explanations)

    assert len(predictions) == 1
    assert predictions[0]["serviceName"] == "checkout-api"
    assert predictions[0]["confidence"] > DEFAULT_CONFIDENCE_THRESHOLD
    assert "trend" in predictions[0]["rationale"]  # NFR-010: rationale present


def test_low_confidence_forecast_is_filtered_out():
    forecasts = [_forecast_row("billing-service", DEFAULT_CONFIDENCE_THRESHOLD - 0.2)]
    predictions = build_predictions(forecasts, explanations=[])
    assert predictions == []


def test_missing_explanation_falls_back_to_default_rationale():
    forecasts = [_forecast_row("checkout-api", DEFAULT_CONFIDENCE_THRESHOLD + 0.1)]
    predictions = build_predictions(forecasts, explanations=[])
    assert predictions[0]["rationale"]  # never empty, per NFR-010


def test_anomaly_entries_are_distinguished_from_predictions():
    anomalies = [
        {"service_name": "checkout-api", "timestamp": "2026-09-24T11:00:00Z", "measured_value": 12.3, "anomaly_probability": 0.91}
    ]
    entries = build_anomaly_only_entries(anomalies)
    assert entries[0]["isAnomalyOnly"] is True
    assert entries[0]["anomalyProbability"] == 0.91
