"""Shared Firestore client wrapper (T14).

Owns the 4 live/ephemeral collections this platform ever writes to --
`approvals/`, `predictions/`, `executive_metrics/`, `pending_alerts/`
(design.md §3.4) -- and nothing else. Firestore is never the system of
record: every field written here is a projection of, or derived from, the
four FR-039 BigQuery tables (correlated_alerts, incidents,
remediation_logs, incident_postmortems), never a substitute for them.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore


class FirestoreClient:
    """Thin wrapper scoping access to this platform's 4 Firestore collections."""

    APPROVALS = "approvals"
    PREDICTIONS = "predictions"
    EXECUTIVE_METRICS = "executive_metrics"
    PENDING_ALERTS = "pending_alerts"

    def __init__(self, project_id: str | None = None) -> None:
        self._project_id = project_id or os.environ["GCP_PROJECT_ID"]
        self._client = firestore.Client(project=self._project_id)

    # ── Approvals (Remediation Action + Approval Decision, design.md §3.4) ──

    def create_approval(self, action_id: str, data: dict[str, Any]) -> None:
        doc = {**data, "status": data.get("status", "Proposed"), "createdAt": _now()}
        self._client.collection(self.APPROVALS).document(action_id).set(doc)

    def get_approval(self, action_id: str) -> dict[str, Any] | None:
        snap = self._client.collection(self.APPROVALS).document(action_id).get()
        return snap.to_dict() if snap.exists else None

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        query = self._client.collection(self.APPROVALS).where("status", "==", "Proposed")
        return [{"actionId": d.id, **d.to_dict()} for d in query.stream()]

    def decide_approval(
        self, action_id: str, decision: str, approver_uid: str, comments: str = ""
    ) -> datetime:
        decided_at = _now()
        self._client.collection(self.APPROVALS).document(action_id).update(
            {
                "status": "Approved" if decision == "approve" else "Rejected",
                "approverUid": approver_uid,
                "decision": decision,
                "comments": comments,
                "decidedAt": decided_at,
            }
        )
        return decided_at

    def record_execution_result(self, action_id: str, success: bool, detail: str) -> None:
        self._client.collection(self.APPROVALS).document(action_id).update(
            {
                "executionResult": {"success": success, "detail": detail, "executedAt": _now()},
                "status": "Executed" if success else "ExecutionFailed",
            }
        )

    # ── Predictions (design.md §3.2 row 4 -- Firestore-only, no BQ write) ──

    def write_prediction(self, service_name: str, alert_type: str, data: dict[str, Any]) -> None:
        doc_id = f"{service_name}__{alert_type}"
        self._client.collection(self.PREDICTIONS).document(doc_id).set(
            {**data, "updatedAt": _now()}
        )

    def list_active_predictions(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._client.collection(self.PREDICTIONS).stream()]

    # ── Executive metrics snapshot ──

    def write_executive_metrics(self, data: dict[str, Any]) -> None:
        self._client.collection(self.EXECUTIVE_METRICS).document("latest").set(
            {**data, "updatedAt": _now()}
        )

    def get_executive_metrics(self) -> dict[str, Any] | None:
        snap = self._client.collection(self.EXECUTIVE_METRICS).document("latest").get()
        return snap.to_dict() if snap.exists else None

    # ── Pending alerts clustering window (short-TTL, Agent 1 only) ──

    def add_pending_alert(self, cluster_key: str, replay_event_id: str, alert: dict[str, Any]) -> None:
        ref = self._client.collection(self.PENDING_ALERTS).document(cluster_key)
        ref.set(
            {"alerts": firestore.ArrayUnion([{"replayEventId": replay_event_id, **alert}])},
            merge=True,
        )

    def get_pending_cluster(self, cluster_key: str) -> dict[str, Any] | None:
        snap = self._client.collection(self.PENDING_ALERTS).document(cluster_key).get()
        return snap.to_dict() if snap.exists else None

    def clear_pending_cluster(self, cluster_key: str) -> None:
        self._client.collection(self.PENDING_ALERTS).document(cluster_key).delete()


def _now() -> datetime:
    return datetime.now(timezone.utc)
