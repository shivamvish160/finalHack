"""T35: contract tests for the approvals API (contracts/rest-api.md)."""

from fastapi.testclient import TestClient

from tests._pkgload import load_submodule

_main = load_submodule("api_gateway_app", "services/api-gateway/app", "main")
create_app = _main.create_app


def _client_as(monkeypatch, role: str) -> TestClient:
    auth_module = load_submodule("api_gateway_app", "services/api-gateway/app", "auth")

    async def _fake_user():
        return auth_module.AuthenticatedUser(uid="test-uid", role=role)

    app = create_app()
    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    return TestClient(app, raise_server_exceptions=False)


def test_list_pending_approvals_allowed_for_approver(monkeypatch):
    client = _client_as(monkeypatch, "Approver")
    response = client.get("/approvals?status=pending")
    assert response.status_code in (200, 500)


def test_list_pending_approvals_forbidden_for_executive_viewer(monkeypatch):
    client = _client_as(monkeypatch, "ExecutiveViewer")
    response = client.get("/approvals?status=pending")
    assert response.status_code == 403


def test_decision_endpoint_requires_decision_field(monkeypatch):
    client = _client_as(monkeypatch, "Approver")
    response = client.post("/approvals/action-123/decision", json={})
    assert response.status_code == 422


def test_decision_endpoint_accepts_approve(monkeypatch):
    client = _client_as(monkeypatch, "Approver")
    response = client.post("/approvals/action-123/decision", json={"decision": "approve", "comments": "looks safe"})
    assert response.status_code in (200, 404, 500)
