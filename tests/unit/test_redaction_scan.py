"""T65: scan for plaintext secrets/PII in generated remediation scripts
(SC-008). Invoked by scripts/demo/redaction-scan.ps1 for the pre-demo scan,
and runs as part of the normal test suite."""

from agents.common.redaction import redact
from agents.remediation.agent import propose_remediation


class _FakeBQClient:
    """Fixture BQ client returning a runbook whose procedure text
    deliberately contains a secret/PII canary, to prove propose_remediation
    redacts it before returning (defense-in-depth per design.md §7.3)."""

    def query_json_rows(self, sql, params=()):  # noqa: ANN001, ARG002
        return [
            {
                "runbook_id": "rb-canary",
                "title": "Rotate DB credentials",
                "remediation_steps": "kubectl set env deployment/checkout DB_PASSWORD=hunter2secret; restart pods",
                "rollback_commands": "contact ops-oncall@example.com if this fails",
            }
        ]


def test_propose_remediation_redacts_secret_in_fix_script():
    proposal = propose_remediation(_FakeBQClient(), runbook_id="rb-canary")
    assert "hunter2secret" not in proposal["fixScript"]


def test_propose_remediation_redacts_email_in_rollback_script():
    proposal = propose_remediation(_FakeBQClient(), runbook_id="rb-canary")
    assert "ops-oncall@example.com" not in proposal["rollbackScript"]


def test_redaction_helper_is_idempotent():
    text = "token=abcdef1234567890abcdef"
    once = redact(text)
    twice = redact(once)
    assert once == twice
