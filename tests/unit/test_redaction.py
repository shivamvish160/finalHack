"""T19: verify redaction.py catches known secret/PII canaries (SC-008, NFR-006/007, AC-3.4)."""

from agents.common.redaction import redact


def test_redacts_email():
    assert "REDACTED" in redact("Contact ops-oncall@example.com for details")
    assert "ops-oncall@example.com" not in redact("Contact ops-oncall@example.com for details")


def test_redacts_aws_access_key():
    text = "Found leaked key AKIAABCDEFGHIJKLMNOP in log line"
    assert "AKIAABCDEFGHIJKLMNOP" not in redact(text)


def test_redacts_bearer_token():
    text = "Authorization: Bearer abc123.def456-ghi789"
    assert "abc123.def456-ghi789" not in redact(text)


def test_redacts_ssn():
    assert "123-45-6789" not in redact("Customer SSN on file: 123-45-6789")


def test_preserves_surrounding_context():
    result = redact("alert message: node-42 flapping, contact a@b.com now")
    assert "node-42 flapping" in result
    assert "a@b.com" not in result


def test_passthrough_for_clean_text():
    clean = "CPU utilization on node-7 exceeded 95% for 3 consecutive minutes"
    assert redact(clean) == clean


def test_none_and_empty_are_passthrough():
    assert redact(None) is None
    assert redact("") == ""
