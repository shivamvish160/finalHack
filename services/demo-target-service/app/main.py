"""Demo target sandbox service (T45).

Isolated Cloud Run app that is the literal target of real remediation
execution -- contains blast radius to a purpose-built, disposable service,
never production infrastructure (design.md §3.1). Invocable only by the
agent-orchestrator's service account (infra/modules/cloud-run IAM binding).

Exposes a controllable failure/recovery endpoint: `/fail` flips it into a
failing state, `/remediate` "fixes" it (simulating what a real remediation
script would target, e.g. a rollout restart), so the demo can show a real,
observable before/after state change.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="demo-target-service", version="0.1.0")

_state = {"healthy": True}


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"healthy": _state["healthy"]}


@app.post("/fail")
async def induce_failure() -> dict[str, str]:
    _state["healthy"] = False
    return {"status": "failing"}


@app.post("/remediate")
async def remediate(payload: dict) -> dict[str, str]:  # noqa: ANN001
    """The real action Agent 5's execute_remediation calls (FR-019/FR-020)."""
    _state["healthy"] = True
    return {"status": "healthy", "actionId": payload.get("actionId", ""), "command": payload.get("command", "")}


@app.post("/rollback")
async def rollback(payload: dict) -> dict[str, str]:  # noqa: ANN001
    _state["healthy"] = False
    return {"status": "rolled_back", "actionId": payload.get("actionId", "")}
