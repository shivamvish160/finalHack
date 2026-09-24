# Demo environment variables -- populate before `terraform apply`.
# project_id/region MUST match the project that already hosts the existing
# BigQuery warehouse; this Terraform root never creates that warehouse.
project_id = "your-gcp-project-id"
region     = "us-central1"

bq_telemetry_dataset      = "sre_telemetry"
bq_topology_dataset       = "sre_topology"
bq_knowledge_base_dataset = "sre_knowledge_base"
bq_incident_mart_dataset  = "sre_incident_mart"
bq_ml_ops_dataset         = "sre_ml_ops"

# Fixed per T6 / research.md §4 -- retrain the ARIMA_PLUS forecast model
# every 15 minutes, comfortably inside the demo's replay window so a
# prediction can fire before its corresponding alert (AC-4.1).
bqml_retrain_schedule_cron = "*/15 * * * *"
predictions_tick_schedule_cron = "*/2 * * * *"

alert_replay_target_msgs_per_minute = 1000
