"""Structured Cloud Logging audit trail (FR-037).

FR-037 requires auditing THREE action categories -- incident access,
approval decision, and remediation execution -- as a single, consistent
log-based trail (not a BigQuery table; see design.md §7.4 item 1). Shared
under agents/common/ (rather than living inside one service) so both
api-gateway (incident access, approval decisions) and agent-orchestrator
(remediation execution) call into the exact same audit trail.
"""

from __future__ import annotations

import os

import google.cloud.logging as cloud_logging

_LOGGER_NAME = "sre-incident-platform-audit"


def _get_logger():
    client = cloud_logging.Client(project=os.environ["GCP_PROJECT_ID"])
    return client.logger(_LOGGER_NAME)


def log_incident_access(actor_uid: str, incident_id: str, action: str = "view") -> None:
    """FR-037 category 1: incident access."""
    _get_logger().log_struct(
        {"category": "incident_access", "actor": actor_uid, "incidentId": incident_id, "action": action}
    )


def log_approval_decision(
    actor_uid: str, action_id: str, incident_id: str, decision: str, comments: str = ""
) -> None:
    """FR-037 category 2: approval decision."""
    _get_logger().log_struct(
        {
            "category": "approval_decision",
            "actor": actor_uid,
            "actionId": action_id,
            "incidentId": incident_id,
            "decision": decision,
            "comments": comments,
        }
    )


def log_remediation_execution(action_id: str, incident_id: str, success: bool, detail: str) -> None:
    """FR-037 category 3: remediation execution. Actor here is the platform
    itself (the orchestrator), since execution is system-triggered by a
    prior human approval, not a direct end-user action -- the approval
    decision's actor (above) is the accountable human for this outcome."""
    _get_logger().log_struct(
        {
            "category": "remediation_execution",
            "actor": "agent-orchestrator",
            "actionId": action_id,
            "incidentId": incident_id,
            "success": success,
            "detail": detail,
        }
    )
