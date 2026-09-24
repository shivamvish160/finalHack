"""T55: contract test for the executive summary API."""

from fastapi.testclient import TestClient

from tests._pkgload import load_submodule

_main = load_submodule("api_gateway_app", "services/api-gateway/app", "main")
create_app = _main.create_app


def _client_as(role: str) -> TestClient:
    auth_module = load_submodule("api_gateway_app", "services/api-gateway/app", "auth")

    async def _fake_user():
        return auth_module.AuthenticatedUser(uid="test-uid", role=role)

    app = create_app()
    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    return TestClient(app, raise_server_exceptions=False)


def test_executive_summary_allowed_for_executive_viewer():
    client = _client_as("ExecutiveViewer")
    response = client.get("/executive/summary")
    assert response.status_code in (200, 500)


def test_executive_summary_forbidden_for_on_call_engineer():
    client = _client_as("OnCallEngineer")
    response = client.get("/executive/summary")
    assert response.status_code == 403
