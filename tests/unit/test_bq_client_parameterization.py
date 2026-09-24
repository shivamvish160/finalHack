"""T18: guard NFR-011/CHK018 -- bq_client must reject non-parameterized SQL."""

import pytest
from google.cloud import bigquery

from agents.common.bq_client import BigQueryClient, UnsafeQueryError, param


class _FakeBQClient:
    """Stand-in for google.cloud.bigquery.Client so this test needs no live GCP creds."""

    def query(self, sql, job_config=None):  # noqa: ANN001, ANN201 - test double
        class _Job:
            def result(self_inner):  # noqa: ANN001
                return []

        return _Job()


@pytest.fixture(autouse=True)
def _patch_bigquery_client(monkeypatch):
    monkeypatch.setattr(bigquery, "Client", lambda project=None: _FakeBQClient())
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")


def test_parameterized_query_is_allowed():
    client = BigQueryClient()
    client.query(
        "SELECT * FROM `sre_telemetry.alert_stream` WHERE node_id = @node_id",
        [param("node_id", "STRING", "node-123")],
    )


@pytest.mark.parametrize(
    "unsafe_sql",
    [
        "SELECT * FROM alert_stream WHERE node_id = '" + "node-123" + "'",
        "SELECT * FROM alert_stream WHERE node_id = %s" + "",
        "SELECT * FROM alert_stream WHERE node_id = {node_id}",
    ],
)
def test_string_built_query_is_rejected(unsafe_sql):
    client = BigQueryClient()
    with pytest.raises(UnsafeQueryError):
        client.query(unsafe_sql)
