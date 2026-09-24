"""Shared BigQuery client wrapper (T13).

Enforces named `@param` query parameters ONLY -- never string-concatenated
SQL -- per research.md §18 and NFR-011/checklist CHK018. Every agent that
queries the existing warehouse (sre_telemetry, sre_topology,
sre_knowledge_base, sre_incident_mart) or the new sre_ml_ops dataset MUST
go through this wrapper rather than instantiating `bigquery.Client`
directly, so the anti-SQL-injection guarantee is structural, not a
convention agents can accidentally skip.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable

from google.cloud import bigquery

# Real parameterized queries compare columns against named `@param`
# placeholders, never inline quoted literals -- so a comparison `=`
# immediately followed by a quoted literal (`= 'value'`, `= "value"`) is a
# reliable smell that a value was embedded directly into the SQL text
# instead of passed via `query_parameters`. The negative lookahead on `=>`
# specifically excludes BigQuery's named-argument call syntax (e.g.
# `distance_type => 'COSINE'` in VECTOR_SEARCH/ML.* calls), which is a
# legitimate, safe literal (a fixed enum option name, not user data) and
# not a SQL comparison at all. Also flags leftover unresolved
# `%s`/`.format()`-style placeholders as a second, independent signal.
_SUSPICIOUS_CONCAT_RE = re.compile(r"=(?!>)\s*['\"][^'\"]*['\"]|%s\b|\{[^}]*\}")


class UnsafeQueryError(ValueError):
    """Raised when a query looks like it embeds a value via string building
    instead of a named `@param` placeholder."""


class BigQueryClient:
    """Thin, safety-enforcing wrapper around `google.cloud.bigquery.Client`."""

    def __init__(self, project_id: str | None = None) -> None:
        self._project_id = project_id or os.environ["GCP_PROJECT_ID"]
        self._client = bigquery.Client(project=self._project_id)

    @property
    def project_id(self) -> str:
        return self._project_id

    def query(
        self,
        sql: str,
        params: Iterable[bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter] = (),
    ) -> "bigquery.table.RowIterator":
        """Run a parameterized query and return the result row iterator.

        Raises `UnsafeQueryError` if the query text looks like it was built
        via string interpolation/concatenation rather than named `@param`s.
        """
        self._assert_safe(sql)
        job_config = bigquery.QueryJobConfig(query_parameters=list(params))
        return self._client.query(sql, job_config=job_config).result()

    def query_json_rows(
        self,
        sql: str,
        params: Iterable[bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter] = (),
    ) -> list[dict[str, Any]]:
        """Convenience wrapper returning rows as plain dicts."""
        return [dict(row.items()) for row in self.query(sql, params)]

    @staticmethod
    def _assert_safe(sql: str) -> None:
        if _SUSPICIOUS_CONCAT_RE.search(sql):
            raise UnsafeQueryError(
                "Query text appears to embed a value via string "
                "concatenation/interpolation instead of a named @param "
                "placeholder (NFR-011 / research.md §18). Rewrite using "
                "bigquery.ScalarQueryParameter/ArrayQueryParameter."
            )


def param(name: str, type_: str, value: Any) -> bigquery.ScalarQueryParameter:
    """Shorthand for a named scalar query parameter."""
    return bigquery.ScalarQueryParameter(name, type_, value)


def array_param(name: str, type_: str, values: list[Any]) -> bigquery.ArrayQueryParameter:
    """Shorthand for a named array query parameter (e.g. `IN UNNEST(@ids)`)."""
    return bigquery.ArrayQueryParameter(name, type_, values)
