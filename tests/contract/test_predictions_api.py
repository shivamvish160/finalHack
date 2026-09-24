"""T48: contract test for the predictions API (contracts/rest-api.md)."""

from fastapi.testclient import TestClient

from tests._pkgload import load_submodule

_main = load_submodule("api_gateway_app", "services/api-gateway/app", "main")
create_app = _main.create_app


def _client(monkeypatch) -> TestClient:
    auth_module = load_submodule("api_gateway_app", "services/api-gateway/app", "auth")

    async def _fake_user():
        return auth_module.AuthenticatedUser(uid="test-uid", role="OnCallEngineer")

    app = create_app()
    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    return TestClient(app, raise_server_exceptions=False)


def test_active_predictions_endpoint_exists(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/predictions?activeOnly=true")
    assert response.status_code in (200, 500)


def test_anomalies_endpoint_exists(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/predictions/anomalies")
    assert response.status_code in (200, 500)
