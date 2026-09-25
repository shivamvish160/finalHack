/**
 * T7: Pub/Sub topics + DLQs + push subscriptions (contracts/pubsub-events.md).
 * Provisions NEW messaging infrastructure only -- never touches the
 * existing BigQuery warehouse.
 */

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "orchestrator_alerts_push_endpoint" {
  description = "URL of the agent-orchestrator-alerts Cloud Run service (Agent 1, research.md §17)."
  type        = string
}

variable "orchestrator_incidents_push_endpoint" {
  description = "URL of the agent-orchestrator-incidents Cloud Run service (Agents 2/3/5/6)."
  type        = string
}

variable "orchestrator_predictive_push_endpoint" {
  description = "URL of the agent-orchestrator-predictive Cloud Run service (Agent 4)."
  type        = string
}

variable "orchestrator_invoker_service_account_email" {
  type = string
}

locals {
  topics = [
    "alerts.replay",
    "incidents.correlated",
    "incidents.root_cause_identified",
    "incidents.runbook_matched",
    "remediation.proposed",
    "remediation.approved",
    "remediation.rejected",
    "remediation.executed",
    "predictions.tick",
    "risk.forecast.created",
    "executive.metrics.updated",
  ]

  # (push endpoint base, route path) for each topic, matching
  # services/agent-orchestrator/app/stages/* and the T53 per-family split.
  topic_routes = {
    "alerts.replay"                   = { endpoint = var.orchestrator_alerts_push_endpoint, path = "/stages/alert-correlation" }
    "incidents.correlated"            = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/root-cause" }
    "incidents.root_cause_identified" = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/runbook-retrieval" }
    "incidents.runbook_matched"       = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/remediation-propose" }
    "remediation.approved"            = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/remediation-execute" }
    "remediation.rejected"            = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/remediation-rejected" }
    "remediation.executed"            = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/executive-impact-remediation" }
    "predictions.tick"                = { endpoint = var.orchestrator_predictive_push_endpoint, path = "/stages/predictive-risk" }
    "risk.forecast.created"           = { endpoint = var.orchestrator_incidents_push_endpoint, path = "/stages/executive-impact-forecast" }
  }
}

resource "google_pubsub_topic" "topic" {
  for_each = toset(local.topics)
  project  = var.project_id
  name     = each.value
}

resource "google_pubsub_topic" "dlq" {
  for_each = toset(local.topics)
  project  = var.project_id
  name     = "${each.value}-dlq"
}

resource "google_pubsub_subscription" "push" {
  for_each = local.topic_routes
  project  = var.project_id
  name     = "${each.key}-sub"
  topic    = google_pubsub_topic.topic[each.key].id

  push_config {
    push_endpoint = "${each.value.endpoint}${each.value.path}"
    oidc_token {
      service_account_email = var.orchestrator_invoker_service_account_email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq[each.key].id
    max_delivery_attempts = 5
  }

  ack_deadline_seconds = 60
}

output "topic_ids" {
  value = { for k, v in google_pubsub_topic.topic : k => v.id }
}
