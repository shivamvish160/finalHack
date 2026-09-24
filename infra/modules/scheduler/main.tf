/**
 * T11: Cloud Scheduler jobs -- predictions.tick (alert-independent forecast
 * cadence, AC-4.1) and the BQML retrain job, using the cadence fixed in T6
 * (infra/environments/demo/terraform.tfvars).
 */

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "predictions_tick_schedule_cron" {
  type = string
}

variable "bqml_retrain_schedule_cron" {
  type = string
}

variable "orchestrator_push_endpoint" {
  type = string
}

variable "scheduler_service_account_email" {
  type = string
}

resource "google_cloud_scheduler_job" "predictions_tick" {
  project   = var.project_id
  region    = var.region
  name      = "predictions-tick"
  schedule  = var.predictions_tick_schedule_cron
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${var.orchestrator_push_endpoint}/stages/predictive-risk"
    oidc_token {
      service_account_email = var.scheduler_service_account_email
    }
  }
}

resource "google_cloud_scheduler_job" "bqml_retrain" {
  project   = var.project_id
  region    = var.region
  name      = "bqml-retrain-alert-trend-forecast"
  schedule  = var.bqml_retrain_schedule_cron
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${var.orchestrator_push_endpoint}/stages/retrain-forecast-model"
    oidc_token {
      service_account_email = var.scheduler_service_account_email
    }
  }
}

resource "google_service_account" "scheduler" {
  project      = var.project_id
  account_id   = "sa-scheduler"
  display_name = "Cloud Scheduler jobs (predictions.tick, BQML retrain)"
}
