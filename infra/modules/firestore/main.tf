/**
 * T9: Firestore (native mode) + security rules for the 4 live/ephemeral
 * collections this platform owns (design.md §3.4).
 */

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}
