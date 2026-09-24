"""Predictive Risk Agent (T51, FR-022/FR-023).

ADK `LlmAgent` (gemini-2.5-flash) calling `ML.FORECAST`, `ML.DETECT_
ANOMALIES`, and `ML.EXPLAIN_FORECAST` against the platform-owned
`sre_ml_ops.alert_trend_forecast_model` (ARIMA_PLUS, trained on the
EXISTING `sre_telemetry.alert_stream`, data-model.md §5). Triggered by
Cloud Scheduler's `predictions.tick`, independent of alert arrival, so a
forecast can precede its corresponding alert (AC-4.1).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient  # noqa: E402

DEFAULT_CONFIDENCE_THRESHOLD = float(os.environ.get("PREDICTION_CONFIDENCE_THRESHOLD", "0.65"))


def forecast_service_trends(bq_client: BigQueryClient, horizon_minutes: int = 60) -> list[dict[str, Any]]:
    """`ML.FORECAST` over the trained model -- predicted value + confidence
    interval per `service_name` time series (FR-022)."""
    sql = f"""
        SELECT service_name, forecast_timestamp, forecast_value,
               confidence_level, prediction_interval_lower_bound,
               prediction_interval_upper_bound
        FROM ML.FORECAST(
            MODEL `sre_ml_ops.alert_trend_forecast_model`,
            STRUCT({horizon_minutes} AS horizon, 0.95 AS confidence_level)
        )
    """
    return bq_client.query_json_rows(sql)


def detect_anomalies(bq_client: BigQueryClient) -> list[dict[str, Any]]:
    """`ML.DETECT_ANOMALIES` -- surfaces deviations from historical norms
    independent of whether a full outage prediction is triggered (FR-023)."""
    sql = """
        SELECT service_name, timestamp, measured_value, is_anomaly, anomaly_probability
        FROM ML.DETECT_ANOMALIES(
            MODEL `sre_ml_ops.alert_trend_forecast_model`,
            STRUCT(0.95 AS anomaly_prob_threshold)
        )
        WHERE is_anomaly = TRUE
    """
    return bq_client.query_json_rows(sql)


def explain_forecast(bq_client: BigQueryClient, horizon_minutes: int = 60) -> list[dict[str, Any]]:
    """`ML.EXPLAIN_FORECAST` -- the WHY behind each prediction (NFR-010)."""
    sql = f"""
        SELECT * FROM ML.EXPLAIN_FORECAST(
            MODEL `sre_ml_ops.alert_trend_forecast_model`,
            STRUCT({horizon_minutes} AS horizon, 0.95 AS confidence_level)
        )
    """
    return bq_client.query_json_rows(sql)


def build_predictions(
    forecasts: list[dict[str, Any]],
    explanations: list[dict[str, Any]],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Combine forecast + explanation rows into FR-022's response shape,
    filtering to only confident predictions (>= threshold)."""
    explanation_by_service = {e.get("service_name"): e for e in explanations}
    predictions = []
    for forecast in forecasts:
        confidence = forecast.get("confidence_level", 0.0)
        if confidence < threshold:
            continue
        explanation = explanation_by_service.get(forecast["service_name"], {})
        predictions.append(
            {
                "serviceName": forecast["service_name"],
                "predictedFailureWindow": str(forecast.get("forecast_timestamp")),
                "confidence": confidence,
                "affectedServices": [forecast["service_name"]],
                "rationale": explanation.get("explanation", "Derived from ARIMA_PLUS trend decomposition."),
            }
        )
    return predictions


def build_anomaly_only_entries(anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """FR-023: anomaly-only entries, distinguished from a full prediction."""
    return [
        {
            "serviceName": a["service_name"],
            "timestamp": str(a["timestamp"]),
            "measuredValue": a["measured_value"],
            "anomalyProbability": a["anomaly_probability"],
            "isAnomalyOnly": True,
        }
        for a in anomalies
    ]


def build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="predictive_risk_agent",
        model=os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
        instruction=(
            "Report only forecasts derived from ML.FORECAST/ML.DETECT_ANOMALIES/"
            "ML.EXPLAIN_FORECAST tool outputs -- never invent a prediction not "
            "backed by the trained model's output (NFR-011)."
        ),
    )
