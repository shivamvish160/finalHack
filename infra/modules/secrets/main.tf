/**
 * T12: Secret Manager entries (design.md §7.2). Only real secrets live
 * here -- the public Firebase Web client config is intentionally excluded.
 */

variable "project_id" {
  type = string
}

resource "google_secret_manager_secret" "firebase_admin_credentials" {
  project   = var.project_id
  secret_id = "firebase-admin-sdk-credentials"

  replication {
    auto {}
  }
}

# The secret VALUE is populated out-of-band (e.g. `gcloud secrets versions
# add`) by the deployer, never committed to source control or set via
# Terraform variables.
