"""T66: RBAC test matrix -- one test per role x endpoint combination (FR-035)."""

import itertools

import pytest
from fastapi.testclient import TestClient

from tests._pkgload import load_submodule

_main = load_submodule("api_gateway_app", "services/api-gateway/app", "main")
create_app = _main.create_app

ALL_ROLES = ("OnCallEngineer", "IncidentCommander", "Approver", "ExecutiveViewer", "Administrator")

# (method, path, allowed_roles) -- mirrors contracts/rest-api.md's Roles column.
ENDPOINTS = [
    ("GET", "/incidents", None),  # None = any authenticated role
    ("GET", "/approvals?status=pending", ("Approver", "IncidentCommander", "Administrator")),
    ("GET", "/executive/summary", ("ExecutiveViewer", "IncidentCommander", "Administrator")),
    ("GET", "/predictions?activeOnly=true", None),
    ("GET", "/me", None),
]


def _client_as(role: str) -> TestClient:
    auth_module = load_submodule("api_gateway_app", "services/api-gateway/app", "auth")

    async def _fake_user():
        return auth_module.AuthenticatedUser(uid="test-uid", role=role)

    app = create_app()
    app.dependency_overrides[auth_module.get_current_user] = _fake_user
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "method,path,allowed_roles,role",
    [
        (method, path, allowed_roles, role)
        for (method, path, allowed_roles), role in itertools.product(ENDPOINTS, ALL_ROLES)
    ],
)
def test_rbac_matrix(method, path, allowed_roles, role):
    client = _client_as(role)
    response = client.request(method, path)

    if allowed_roles is None or role in allowed_roles:
        assert response.status_code != 403, f"{role} should be allowed on {method} {path}"
    else:
        assert response.status_code == 403, f"{role} should be forbidden on {method} {path}"
