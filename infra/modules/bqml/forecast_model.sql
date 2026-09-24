-- BQML ARIMA_PLUS forecast model DDL (data-model.md §5, research.md §6).
-- Run once at deploy time (scripts/deploy) and re-run on the Cloud Scheduler
-- retrain cadence fixed in T6 (*/15 * * * *). Trains directly against the
-- EXISTING sre_telemetry.alert_stream -- reads only, never writes there.
CREATE OR REPLACE MODEL `sre_ml_ops.alert_trend_forecast_model`
OPTIONS (
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'timestamp',
  time_series_data_col = 'measured_value',
  time_series_id_col = 'service_name',
  auto_arima = TRUE,
  data_frequency = 'AUTO_FREQUENCY',
  decompose_time_series = TRUE
) AS
SELECT
  timestamp,
  service_name,
  measured_value
FROM `sre_telemetry.alert_stream`
WHERE measured_value IS NOT NULL;
