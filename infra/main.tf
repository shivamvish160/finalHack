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
  default = "gcr.io/PROJECT/alert-replay-service:latest"
}

variable "container_image_orchestrator" {
  type    = string
  default = "gcr.io/PROJECT/agent-orchestrator:latest"
}

variable "container_image_api_gateway" {
  type    = string
  default = "gcr.io/PROJECT/api-gateway:latest"
}

variable "container_image_demo_target" {
  type    = string
  default = "gcr.io/PROJECT/demo-target-service:latest"
}

module "secrets" {
  source     = "./modules/secrets"
  project_id = var.project_id
}

module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  region     = var.region
}

module "bqml" {
  source     = "./modules/bqml"
  project_id = var.project_id
  region     = var.region
}

module "cloud_run" {
  source                       = "./modules/cloud-run"
  project_id                   = var.project_id
  region                       = var.region
  container_image_alert_replay = var.container_image_alert_replay
  container_image_orchestrator = var.container_image_orchestrator
  container_image_api_gateway  = var.container_image_api_gateway
  container_image_demo_target  = var.container_image_demo_target
}

module "pubsub" {
  source                                      = "./modules/pubsub"
  project_id                                  = var.project_id
  region                                      = var.region
  orchestrator_alerts_push_endpoint           = module.cloud_run.orchestrator_alerts_url
  orchestrator_incidents_push_endpoint        = module.cloud_run.orchestrator_incidents_url
  orchestrator_predictive_push_endpoint       = module.cloud_run.orchestrator_predictive_url
  orchestrator_invoker_service_account_email  = module.cloud_run.orchestrator_service_account_email
}

module "scheduler" {
  source                         = "./modules/scheduler"
  project_id                     = var.project_id
  region                         = var.region
  predictions_tick_schedule_cron = var.predictions_tick_schedule_cron
  bqml_retrain_schedule_cron     = var.bqml_retrain_schedule_cron
  orchestrator_push_endpoint     = module.cloud_run.orchestrator_predictive_url
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
