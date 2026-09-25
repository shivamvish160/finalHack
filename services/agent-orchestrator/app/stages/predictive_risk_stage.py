"""Predictive risk orchestrator stage (T52).

Subscribed to `predictions.tick` (Cloud Scheduler -- independent of alert
traffic, AC-4.1). Invokes the Predictive Risk agent's forecast/anomaly/
explain tools, writes ONLY to Firestore `predictions/*` (no BigQuery write,
per the Agent-to-Warehouse Query Patterns table), publishes
`risk.forecast.created`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient  # noqa: E402
from agents.common.firestore_client import FirestoreClient  # noqa: E402
from agents.predictive_risk.agent import (  # noqa: E402
    build_anomaly_only_entries,
    build_predictions,
    detect_anomalies,
    explain_forecast,
    forecast_service_trends,
)


def handle_predictions_tick(_payload: dict[str, Any]) -> dict[str, Any]:
    bq_client = BigQueryClient()
    firestore_client = FirestoreClient()

    forecasts = forecast_service_trends(bq_client)
    explanations = explain_forecast(bq_client)
    anomalies = detect_anomalies(bq_client)

    predictions = build_predictions(forecasts, explanations)
    anomaly_entries = build_anomaly_only_entries(anomalies)

    for prediction in predictions:
        firestore_client.write_prediction(
            prediction["serviceName"], alert_type="predicted_failure", data=prediction
        )
    for anomaly in anomaly_entries:
        firestore_client.write_prediction(
            anomaly["serviceName"], alert_type="anomaly_only", data=anomaly
        )

    return {"payload": {"predictionCount": len(predictions), "anomalyCount": len(anomaly_entries)}}
