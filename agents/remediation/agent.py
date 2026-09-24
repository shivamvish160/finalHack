"""Remediation Agent (T40, FR-015 through FR-021, NFR-009).

Two PHYSICALLY SEPARATE tools, per design.md §3.1/§8:
- `propose_remediation`: generates fix/rollback/risk from a matched
  runbook's documented procedure. Never executes anything.
- `execute_remediation`: the ONLY function that can call the real Cloud Run
  Admin API against `demo-target-service`, and it structurally REFUSES to
  run unless `approved=True` -- there is no code path from `propose_*` to
  `execute_*` that bypasses the human approval gate (NFR-009).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402
from agents.common.redaction import redact  # noqa: E402

RISK_LEVELS = ("Low", "Medium", "High")


def propose_remediation(bq_client: BigQueryClient, runbook_id: str) -> dict[str, Any]:
    """Generate fix + rollback + risk from the matched runbook's own
    documented procedure (FR-015) -- never a hardcoded script (NFR-011)."""
    sql = """
        SELECT runbook_id, title, remediation_steps, rollback_commands
        FROM `sre_knowledge_base.runbooks`
        WHERE runbook_id = @runbook_id
    """
    rows = bq_client.query_json_rows(sql, [param("runbook_id", "STRING", runbook_id)])
    if not rows:
        raise ValueError(f"No runbook found for runbook_id={runbook_id}")

    runbook = rows[0]
    fix_script = _validate_commands(runbook.get("remediation_steps") or "")
    rollback_script = _validate_commands(runbook.get("rollback_commands") or "")
    risk_level = _assess_risk(fix_script)

    return {
        "runbookId": runbook_id,
        "fixScript": redact(fix_script),
        "rollbackScript": redact(rollback_script),
        "riskLevel": risk_level,
    }


def _validate_commands(script: str) -> str:
    """Validate the generated commands before they're ever presented for
    approval (FR-015). Rejects obviously destructive, unscoped commands."""
    banned_patterns = ("rm -rf /", "DROP DATABASE", ":(){ :|:& };:")
    for pattern in banned_patterns:
        if pattern in script:
            raise ValueError(f"Generated command failed validation: contains '{pattern}'")
    return script


def _assess_risk(fix_script: str) -> str:
    if any(keyword in fix_script.lower() for keyword in ("delete", "drop", "terminate")):
        return "High"
    if any(keyword in fix_script.lower() for keyword in ("restart", "rollout", "scale")):
        return "Medium"
    return "Low"


def execute_remediation(
    action_id: str,
    incident_id: str,
    approved: bool,
    fix_script: str | None = None,
) -> dict[str, Any]:
    """The ONLY function capable of real execution. Structurally refuses to
    run without `approved=True` -- this is the NFR-009 enforcement point,
    not a prompt instruction (design.md §8)."""
    if not approved:
        raise PermissionError(
            f"execute_remediation refused for action_id={action_id}: "
            "no prior remediation.approved event (NFR-009)"
        )

    import requests  # local import: only needed on the real-execution path

    demo_target_url = os.environ["DEMO_TARGET_SERVICE_URL"]
    response = requests.post(
        f"{demo_target_url}/remediate",
        json={"actionId": action_id, "incidentId": incident_id, "command": fix_script},
        timeout=30,
    )
    return {"success": response.ok, "detail": response.text[:500]}


def build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="remediation_agent",
        model=os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
        instruction=(
            "Propose fix/rollback/risk strictly from the matched runbook's own "
            "documented steps via propose_remediation. You have NO access to "
            "execute_remediation directly -- execution only happens after an "
            "explicit human approval, via the orchestrator's remediation.approved "
            "event handler."
        ),
    )
