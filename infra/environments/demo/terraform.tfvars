# Demo environment variables -- populate before `terraform apply`.
# project_id/region MUST match the project that already hosts the existing
# BigQuery warehouse; this Terraform root never creates that warehouse.
project_id = "qwiklabs-gcp-03-677e28da7024"
region     = "us-central1"

# Fixed per T6 / research.md §4 -- retrain the ARIMA_PLUS forecast model
# every 15 minutes, comfortably inside the demo's replay window so a
# prediction can fire before its corresponding alert (AC-4.1).
bqml_retrain_schedule_cron     = "*/15 * * * *"
predictions_tick_schedule_cron = "*/2 * * * *"

# Note: sre_telemetry/sre_topology/sre_knowledge_base/sre_incident_mart are
# the EXISTING warehouse dataset names, hardcoded directly in agent SQL
# (agents/*/agent.py) -- not Terraform variables, since this root never
# creates or renames them. The alert-replay target rate is an app-level env
# var (ALERT_REPLAY_TARGET_MSGS_PER_MINUTE in .env), not a Terraform var.
