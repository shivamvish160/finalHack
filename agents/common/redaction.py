"""Shared PII/secret redaction utility (T15).

Applied at READ/OUTPUT time (design.md §7.3) on every free-text warehouse
field before it reaches a Gemini prompt, a dashboard, a generated
remediation/rollback script, or a log line -- defense-in-depth even though
the source data pre-exists this platform (AC-3.4, NFR-006, NFR-007,
SC-008).

This is intentionally a fast, deterministic regex-based pass (not an LLM
call) so it can run on every field of every response without adding
material latency, per NFR-004's "feels immediate" target.
"""

from __future__ import annotations

import re

_REDACTED = "[REDACTED]"

# Each pattern is deliberately narrow (favor false negatives over breaking
# legitimate diagnostic text) but covers the canary classes exercised by
# T19's unit test and SC-008's audit: API keys/tokens, emails, and
# US-style SSNs. Extend here as new canary classes are identified.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic_api_key", re.compile(r"\b(?:api[_-]?key|token|secret)[\"'=:\s]+[A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # No leading \b before the keyword: real secrets routinely appear as
    # env-var-style names with a prefix (e.g. `DB_PASSWORD=...`), where a
    # strict word-boundary would miss "password" embedded after the "_".
    ("password_assignment", re.compile(r"[A-Za-z_]*(?:password|passwd|pwd)[A-Za-z_]*[\"'=:\s]+\S{6,}", re.IGNORECASE)),
]


def redact(text: str | None) -> str | None:
    """Return `text` with every recognized secret/PII pattern replaced.

    Preserves surrounding context (NFR-007) by only replacing the matched
    span, never the whole field.
    """
    if not text:
        return text

    redacted = text
    for _name, pattern in _PATTERNS:
        redacted = pattern.sub(_REDACTED, redacted)
    return redacted


def redact_dict(data: dict, fields: list[str]) -> dict:
    """Return a shallow copy of `data` with the given free-text `fields` redacted."""
    out = dict(data)
    for field in fields:
        if field in out and isinstance(out[field], str):
            out[field] = redact(out[field])
    return out
