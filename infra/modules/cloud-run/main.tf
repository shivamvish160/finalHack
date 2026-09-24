/**
 * T8: Cloud Run services + least-privilege service accounts + IAM
 * (design.md §7.1). Provisions the 4 NEW Cloud Run services only.
 */

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "container_image_alert_replay" {
  type = string
}

variable "container_image_orchestrator" {
  type = string
}

variable "container_image_api_gateway" {
  type = string
}

variable "container_image_demo_target" {
  type = string
}

# ── Service accounts (design.md §7.1) ──

resource "google_service_account" "alert_replay" {
  project      = var.project_id
  account_id   = "sa-alert-replay"
  display_name = "alert-replay-service"
}

resource "google_service_account" "orchestrator" {
  project      = var.project_id
  account_id   = "sa-agent-orchestrator"
  display_name = "agent-orchestrator"
}

resource "google_service_account" "api_gateway" {
  project      = var.project_id
  account_id   = "sa-api-gateway"
  display_name = "api-gateway"
}

resource "google_service_account" "demo_target" {
  project      = var.project_id
  account_id   = "sa-demo-target"
  display_name = "demo-target-service"
}

# ── IAM: alert-replay-service (read-only sre_telemetry, publish alerts.replay) ──

resource "google_project_iam_member" "alert_replay_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.alert_replay.email}"
}

resource "google_project_iam_member" "alert_replay_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.alert_replay.email}"
}

# ── IAM: agent-orchestrator (broadest, but every grant is dataset/resource-scoped) ──

resource "google_project_iam_member" "orchestrator_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

# Scoped to sre_incident_mart only -- the sole dataset this platform writes to.
resource "google_bigquery_dataset_iam_member" "orchestrator_incident_mart_editor" {
  project    = var.project_id
  dataset_id = "sre_incident_mart"
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_pubsub_pubsub" {
  for_each = toset(["roles/pubsub.subscriber", "roles/pubsub.publisher"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

# Scoped ONLY to demo-target-service -- never project-wide run.developer.
resource "google_cloud_run_v2_service_iam_member" "orchestrator_can_invoke_demo_target" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.demo_target.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.orchestrator.email}"
}

# ── IAM: api-gateway ──

resource "google_project_iam_member" "api_gateway_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

# ── Cloud Run services ──

resource "google_cloud_run_v2_service" "alert_replay" {
  project  = var.project_id
  location = var.region
  name     = "alert-replay-service"

  template {
    service_account = google_service_account.alert_replay.email
    scaling {
      min_instance_count = 1
      max_instance_count = 3
    }
    containers {
      image = var.container_image_alert_replay
    }
  }
}

# T53: per-stage autoscaling, quantified in research.md §17. Cloud Run v2
# scaling/concurrency is a SERVICE-level setting, so each stage family with
# a materially different load profile gets its OWN service (same container
# image, different scaling) rather than one blended "agent-orchestrator"
# service -- this is the only way to actually realize the research.md §17
# table's distinct concurrency/min/max values per stage, not just document
# them as an aspiration.

# Agent 1 (Alert Correlation): highest volume, >=1,000 msgs/min raw alerts.
resource "google_cloud_run_v2_service" "orchestrator_alerts" {
  project  = var.project_id
  location = var.region
  name     = "agent-orchestrator-alerts"

  template {
    service_account = google_service_account.orchestrator.email
    max_instance_request_concurrency = 20
    scaling {
      min_instance_count = 2
      max_instance_count = 50
    }
    containers {
      image = var.container_image_orchestrator
      args  = ["--stage-family=alerts"]
    }
  }
}

# Agents 2/3/5/6 (Root Cause, Runbook, Remediation, Executive): incident-
# granularity, LLM-call-bound -- lower concurrency protects per-instance
# memory/LLM connections.
resource "google_cloud_run_v2_service" "orchestrator_incidents" {
  project  = var.project_id
  location = var.region
  name     = "agent-orchestrator-incidents"

  template {
    service_account = google_service_account.orchestrator.email
    max_instance_request_concurrency = 4
    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }
    containers {
      image = var.container_image_orchestrator
      args  = ["--stage-family=incidents"]
    }
  }
}

# Agent 4 (Predictive Risk): Scheduler-triggered only, not alert-driven.
resource "google_cloud_run_v2_service" "orchestrator_predictive" {
  project  = var.project_id
  location = var.region
  name     = "agent-orchestrator-predictive"

  template {
    service_account = google_service_account.orchestrator.email
    max_instance_request_concurrency = 4
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
    containers {
      image = var.container_image_orchestrator
      args  = ["--stage-family=predictive"]
    }
  }
}

resource "google_cloud_run_v2_service" "api_gateway" {
  project  = var.project_id
  location = var.region
  name     = "api-gateway"

  template {
    service_account = google_service_account.api_gateway.email
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.container_image_api_gateway
    }
  }
}

resource "google_cloud_run_v2_service" "demo_target" {
  project  = var.project_id
  location = var.region
  name     = "demo-target-service"

  template {
    service_account = google_service_account.demo_target.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = var.container_image_demo_target
    }
  }
}

output "orchestrator_alerts_url" {
  value = google_cloud_run_v2_service.orchestrator_alerts.uri
}

output "orchestrator_incidents_url" {
  value = google_cloud_run_v2_service.orchestrator_incidents.uri
}

output "orchestrator_predictive_url" {
  value = google_cloud_run_v2_service.orchestrator_predictive.uri
}

output "orchestrator_service_account_email" {
  value = google_service_account.orchestrator.email
}

output "demo_target_url" {
  value = google_cloud_run_v2_service.demo_target.uri
}
