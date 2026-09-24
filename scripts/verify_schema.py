"""T5: Verify the LIVE BigQuery schema for warehouse tables this platform reads/writes.

Run once before implementing any agent that queries `customer_accounts`,
`incidents`, or `remediation_logs` -- their column lists in data-model.md §1
are documented as illustrative placeholders pending this exact verification
(see checklists/architecture.md CHK067). This script never modifies the
warehouse; it only reads INFORMATION_SCHEMA.COLUMNS.

Usage:
    python scripts/verify_schema.py --project <GCP_PROJECT_ID>
"""

from __future__ import annotations

import argparse
import json
import sys

from google.cloud import bigquery

TABLES_TO_VERIFY = [
    ("sre_incident_mart", "customer_accounts"),
    ("sre_incident_mart", "incidents"),
    ("sre_incident_mart", "remediation_logs"),
]


def verify_schema(project_id: str) -> dict[str, list[dict[str, str]]]:
    """Return {dataset.table: [{name, data_type}, ...]} for every table above."""
    client = bigquery.Client(project=project_id)
    results: dict[str, list[dict[str, str]]] = {}

    for dataset, table in TABLES_TO_VERIFY:
        query = f"""
            SELECT column_name, data_type
            FROM `{project_id}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = @table_name
            ORDER BY ordinal_position
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("table_name", "STRING", table)]
        )
        rows = client.query(query, job_config=job_config).result()
        results[f"{dataset}.{table}"] = [
            {"name": row.column_name, "data_type": row.data_type} for row in rows
        ]

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="GCP_PROJECT_ID hosting the existing warehouse")
    args = parser.parse_args()

    schema = verify_schema(args.project)
    print(json.dumps(schema, indent=2))

    for table, columns in schema.items():
        if not columns:
            print(f"WARNING: no columns found for {table} -- does it exist in this project?", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
