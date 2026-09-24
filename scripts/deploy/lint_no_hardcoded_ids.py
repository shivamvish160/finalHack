"""T63: CI check blocking literal alert/runbook/service identifiers in
agent/service source outside test fixtures (NFR-011, checklist CHK016).

Usage: python scripts/deploy/lint_no_hardcoded_ids.py
Exits non-zero (and prints offending lines) if a hardcoded warehouse ID
pattern is found in agents/ or services/ source (excluding tests/).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [REPO_ROOT / "agents", REPO_ROOT / "services"]

# Literal warehouse-row-shaped identifiers that must never appear hardcoded
# in agent/service reasoning or query logic (they should always be
# resolved live from a query result, never baked into source).
_HARDCODED_ID_RE = re.compile(
    r"""["'](alert-\d+|incident-[a-f0-9-]{6,}|rb-\d+|node-\d+)["']"""
)

_ALLOWED_FILE_SUFFIXES = {".py"}


def scan() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for scan_dir in SCAN_DIRS:
        for path in scan_dir.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if _HARDCODED_ID_RE.search(line):
                    violations.append((path, lineno, line.strip()))
    return violations


if __name__ == "__main__":
    violations = scan()
    if violations:
        print("NFR-011 violation: hardcoded warehouse-row identifiers found outside tests:")
        for path, lineno, line in violations:
            print(f"  {path.relative_to(REPO_ROOT)}:{lineno}: {line}")
        sys.exit(1)
    print("OK: no hardcoded alert/incident/runbook/node identifiers found in agents/ or services/.")
