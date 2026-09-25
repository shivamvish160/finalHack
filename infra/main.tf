/**
 * Root Terraform -- wires all NEW-resource-only modules together.
 * Never declares/imports the existing warehouse's datasets/tables
 * (sre_telemetry, sre_topology, sre_knowledge_base, sre_incident_mart
 * themselves are NOT resources here -- only the write access to 4 of their
 * tables, granted via IAM in the cloud-run module).
 */

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

# Enable every mandatory GCP API before any dependent resource is created --
# a fresh project has none of these on by default, and every module below
# would otherwise fail on first `terraform apply` with a 403.
locals {
  required_apis = [
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "identitytoolkit.googleapis.com", # Firebase Authentication
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com", # build-and-push.sh/.ps1 use Cloud Build, not local docker push
  ]
}

resource "google_project_service" "required" {
  for_each                   = toset(local.required_apis)
  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}

# Cloud Build's default service account needs explicit Artifact Registry
# write access on newer projects (no longer implied by default, per a 2024
# GCP security change) -- without this, `gcloud builds submit` fails to
# push the built image even though the build itself succeeds.
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_iam_member" "cloudbuild_artifact_registry_writer" {
  project    = var.project_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  depends_on = [google_project_service.required]
}

# Artifact Registry Docker repo -- Container Registry (gcr.io) is deprecated
# and unusable on new projects; every service image is pushed/pulled here
# instead (build-and-push.sh/.ps1 and the container_image_* defaults below).
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "sre-incident-platform"
  format        = "DOCKER"
  depends_on    = [google_project_service.required]
}

variable "bq_ml_ops_dataset" {
  type    = string
  default = "sre_ml_ops"
}

variable "bqml_retrain_schedule_cron" {
  type    = string
  default = "*/15 * * * *"
}

variable "predictions_tick_schedule_cron" {
  type    = string
  default = "*/2 * * * *"
}

variable "container_image_alert_replay" {
  type    = string
  default = "us-central1-docker.pkg.dev/qwiklabs-gcp-03-677e28da7024/sre-incident-platform/alert-replay-service:latest"
}

variable "container_image_orchestrator" {
  type    = string
  default = "us-central1-docker.pkg.dev/qwiklabs-gcp-03-677e28da7024/sre-incident-platform/agent-orchestrator:latest"
}

variable "container_image_api_gateway" {
  type    = string
  default = "us-central1-docker.pkg.dev/qwiklabs-gcp-03-677e28da7024/sre-incident-platform/api-gateway:latest"
}

variable "container_image_demo_target" {
  type    = string
  default = "us-central1-docker.pkg.dev/qwiklabs-gcp-03-677e28da7024/sre-incident-platform/demo-target-service:latest"
}

variable "container_image_frontend" {
  type    = string
  default = "us-central1-docker.pkg.dev/qwiklabs-gcp-03-677e28da7024/sre-incident-platform/frontend:latest"
}

locals {
  orchestrator_source_files = concat(
    [for file in fileset("${path.root}/../agents", "**/*.py") : "agents/${file}"],
    [for file in fileset("${path.root}/../services/agent-orchestrator/app", "**/*.py") : "services/agent-orchestrator/app/${file}"],
    ["services/agent-orchestrator/Dockerfile", "requirements.txt"],
  )
  orchestrator_source_hash = substr(sha256(join("", [
    for file in sort(local.orchestrator_source_files) : filesha256("${path.root}/../${file}")
  ])), 0, 16)
  orchestrator_image = "${var.region}-docker.pkg.dev/${var.project_id}/sre-incident-platform/agent-orchestrator:${local.orchestrator_source_hash}"
}

# Build only when orchestrator/agent source changes. The content-addressed
# image tag also guarantees Cloud Run creates a new revision; using :latest
# left old revisions running after successful image pushes.
resource "terraform_data" "build_orchestrator" {
  triggers_replace = [local.orchestrator_source_hash]

  provisioner "local-exec" {
    command = "gcloud builds submit \"${path.root}/..\" --config=\"${path.root}/cloudbuild-agent-orchestrator.yaml\" --substitutions=_IMAGE=${local.orchestrator_image} --project=${var.project_id} --region=${var.region}"
  }

  depends_on = [
    google_artifact_registry_repository.images,
    google_project_iam_member.cloudbuild_artifact_registry_writer,
  ]
}

module "secrets" {
  source     = "./modules/secrets"
  project_id = var.project_id
  depends_on = [google_project_service.required]
}

module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  region     = var.region
  depends_on = [google_project_service.required]
}

module "bqml" {
  source     = "./modules/bqml"
  project_id = var.project_id
  region     = var.region
  depends_on = [google_project_service.required]
}

module "cloud_run" {
  source                       = "./modules/cloud-run"
  project_id                   = var.project_id
  region                       = var.region
  container_image_alert_replay = var.container_image_alert_replay
  container_image_orchestrator = local.orchestrator_image
  container_image_api_gateway  = var.container_image_api_gateway
  container_image_demo_target  = var.container_image_demo_target
  container_image_frontend     = var.container_image_frontend
  depends_on                   = [google_project_service.required, terraform_data.build_orchestrator]
}

module "pubsub" {
  source                                     = "./modules/pubsub"
  project_id                                 = var.project_id
  region                                     = var.region
  orchestrator_alerts_push_endpoint          = module.cloud_run.orchestrator_alerts_url
  orchestrator_incidents_push_endpoint       = module.cloud_run.orchestrator_incidents_url
  orchestrator_predictive_push_endpoint      = module.cloud_run.orchestrator_predictive_url
  orchestrator_invoker_service_account_email = module.cloud_run.orchestrator_service_account_email
}

# Failed historical replay deliveries can keep retrying and saturate every
# fresh Cloud Run revision before a small controlled demo run begins. Reset
# only this replay subscription after orchestrator source changes; durable
# warehouse data and all other event subscriptions are untouched.
resource "terraform_data" "reset_replay_backlog" {
  triggers_replace = [local.orchestrator_source_hash]

  provisioner "local-exec" {
    command = "gcloud pubsub subscriptions seek alerts.replay-sub --time=$(date -u +%Y-%m-%dT%H:%M:%SZ) --project=${var.project_id}"
  }

  depends_on = [module.cloud_run, module.pubsub]
}

module "scheduler" {
  source                          = "./modules/scheduler"
  project_id                      = var.project_id
  region                          = var.region
  predictions_tick_schedule_cron  = var.predictions_tick_schedule_cron
  bqml_retrain_schedule_cron      = var.bqml_retrain_schedule_cron
  orchestrator_push_endpoint      = module.cloud_run.orchestrator_predictive_url
  scheduler_service_account_email = module.cloud_run.orchestrator_service_account_email
}

output "orchestrator_alerts_url" {
  value = module.cloud_run.orchestrator_alerts_url
}

output "orchestrator_incidents_url" {
  value = module.cloud_run.orchestrator_incidents_url
}

output "demo_target_url" {
  value = module.cloud_run.demo_target_url
}

output "api_gateway_url" {
  value = module.cloud_run.api_gateway_url
}

output "frontend_url" {
  value = module.cloud_run.frontend_url
}
