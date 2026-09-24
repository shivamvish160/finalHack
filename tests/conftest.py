"""Session-wide test fixtures: provide a fake GCP_PROJECT_ID so modules that
read it eagerly (BigQueryClient, FirestoreClient, etc.) don't KeyError in
this sandboxed test environment, which has no live GCP credentials."""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _fake_gcp_project_id():
    os.environ.setdefault("GCP_PROJECT_ID", "test-project")
    yield
