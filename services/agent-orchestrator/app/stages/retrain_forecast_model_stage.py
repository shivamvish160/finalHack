"""Retrain-forecast-model orchestrator stage.

Subscribed to the Cloud Scheduler-driven retrain trigger
(infra/modules/scheduler `bqml_retrain_schedule_cron`, T6). Re-runs the
`CREATE OR REPLACE MODEL` DDL from infra/modules/bqml/forecast_model.sql
against the existing (read-only) `sre_telemetry.alert_stream` so the
Predictive Risk agent's model stays current with new replayed data.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.common.bq_client import BigQueryClient  # noqa: E402

_FORECAST_MODEL_SQL_PATH = Path(__file__).resolve().parents[5] / "infra" / "modules" / "bqml" / "forecast_model.sql"


def handle_retrain_tick(_payload: dict[str, Any]) -> None:
    bq_client = BigQueryClient()
    ddl = _FORECAST_MODEL_SQL_PATH.read_text(encoding="utf-8")
    bq_client.query(ddl)
