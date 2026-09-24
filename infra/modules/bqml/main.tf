/**
 * T10: new, platform-owned sre_ml_ops dataset + ARIMA_PLUS forecast model
 * (data-model.md §5). Never touches the existing warehouse's 4 datasets.
 */

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

resource "google_bigquery_dataset" "ml_ops" {
  project    = var.project_id
  dataset_id = "sre_ml_ops"
  location   = var.region
  description = "Platform-owned dataset for the Predictive Risk Agent's BQML model only -- never the existing warehouse."
}

# The model itself is created via `CREATE OR REPLACE MODEL` DDL (data-model.md §5),
# run by scripts/deploy or a one-off migration job, not by Terraform, since
# BQML model training is a data operation rather than infrastructure state.
resource "google_bigquery_table" "forecast_model_placeholder_note" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.ml_ops.dataset_id
  table_id   = "_deployment_notes"
  deletion_protection = false
  schema = jsonencode([
    { name = "note", type = "STRING", mode = "NULLABLE" }
  ])
}
