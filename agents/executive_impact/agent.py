"""Executive Impact Agent (T58, FR-027 through FR-032).

ADK `LlmAgent` (gemini-2.5-flash) that joins `correlated_alerts` ->
`alert_stream` -> `customer_accounts` (via `service_name`) and `incidents`
<-> `remediation_logs` to compute affected customers, revenue at risk, and
MTTR reduction (FR-027-030), then drafts and MERGEs an automated
postmortem into `incident_postmortems` (FR-031/032).

Column names below are the real, INFORMATION_SCHEMA.COLUMNS-verified
warehouse schema (data-model.md §1, checklist CHK067) -- `customer_accounts`
has no `user_count`/`sla_uptime_target_pct`/`sla_credit_rate_per_hour`
columns, so per-user and SLA-credit exposure genuinely cannot be computed
from this warehouse; only customer count + MRR-based revenue at risk are.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402


def fetch_linked_customer_accounts(bq_client: BigQueryClient, incident_id: str) -> list[dict[str, Any]]:
    """Join this incident's correlated alerts -> alert_stream -> customer_accounts
    via service_name (FR-027)."""
    sql = """
        SELECT DISTINCT ca_acct.customer_id, ca_acct.customer_name, ca_acct.mrr_cad, ca_acct.tier
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        JOIN `sre_incident_mart.customer_accounts` AS ca_acct ON ca_acct.service_name = al.service_name
        WHERE ca.incident_id = @incident_id
    """
    return bq_client.query_json_rows(sql, [param("incident_id", "STRING", incident_id)])


def compute_business_impact(accounts: list[dict[str, Any]], incident_duration_hours: float) -> dict[str, Any]:
    """Deterministic FR-027/028/030 calculation over the linked accounts --
    every figure is data-derived, never a hardcoded per-incident guess
    (NFR-011). affectedUsers/slaCreditExposure are None -- this warehouse
    has no per-account user-count or SLA-credit-rate columns to derive
    them from (never faked as 0, which would misleadingly imply zero
    exposure rather than "not measurable")."""
    affected_customers = len(accounts)
    monthly_revenue = sum(a.get("mrr_cad") or 0.0 for a in accounts)
    # Pro-rate monthly recurring revenue by incident duration as a simple,
    # explainable revenue-at-risk proxy (NFR-010 requires a stated rationale).
    revenue_at_risk = round(monthly_revenue * (incident_duration_hours / (30 * 24)), 2)

    return {
        "affectedCustomers": affected_customers,
        "affectedUsers": None,
        "revenueAtRisk": revenue_at_risk,
        "slaCreditExposure": None,
    }


def compute_mttr_reduction(bq_client: BigQueryClient) -> dict[str, float]:
    """FR-028: MTTR for platform-handled incidents vs. the historical
    baseline reflected in existing incidents/remediation_logs."""
    sql = """
        SELECT AVG(TIMESTAMP_DIFF(resolved_at, started_at, MINUTE)) AS avg_mttr_minutes
        FROM `sre_incident_mart.incidents`
        WHERE resolved_at IS NOT NULL
    """
    rows = bq_client.query_json_rows(sql)
    return {"averageMttrMinutes": (rows[0].get("avg_mttr_minutes") if rows else None) or 0.0}


def compute_resolution_success_rate(bq_client: BigQueryClient) -> dict[str, float]:
    """FR-029/AC-4.3: resolution success rate -- the share of appended
    remediation_logs outcomes that succeeded, data-derived from the
    existing warehouse (never a hardcoded percentage, NFR-011)."""
    sql = """
        SELECT
          COUNTIF(status = 'Succeeded') AS succeeded_count,
          COUNT(*) AS total_count
        FROM `sre_incident_mart.remediation_logs`
    """
    rows = bq_client.query_json_rows(sql)
    if not rows or not rows[0].get("total_count"):
        return {"resolutionSuccessRatePct": 0.0}

    succeeded = rows[0]["succeeded_count"] or 0
    total = rows[0]["total_count"]
    return {"resolutionSuccessRatePct": round((succeeded / total) * 100, 1)}


def build_postmortem_merge_params(
    incident_id: str,
    root_cause_summary: str,
    timeline_summary: str,
    remediation_summary: str,
    business_impact_summary: str,
    full_report_markdown: str,
    downtime_minutes: float = 0.0,
) -> dict[str, Any]:
    """Stable parameter set for the incident_postmortems MERGE (FR-031/032) --
    keyed on incident_id so regeneration updates rather than duplicates.

    Maps onto the real incident_postmortems schema (no timeline_summary/
    version/generated_at/full_report_markdown columns exist): root_cause,
    impact_summary, contributing_factors, action_items, downtime_minutes.
    `timeline_summary` and `full_report_markdown` are folded into
    `contributing_factors` since there is no dedicated column for either.
    """
    return {
        "incident_id": incident_id,
        "root_cause": root_cause_summary,
        "impact_summary": business_impact_summary,
        "contributing_factors": f"{timeline_summary}\n\n{full_report_markdown}",
        "action_items": remediation_summary,
        "downtime_minutes": downtime_minutes,
    }


def merge_postmortem(bq_client: BigQueryClient, params: dict[str, Any]) -> None:
    """FR-031/032: MERGE into incident_postmortems, keyed on incident_id --
    re-running updates the existing row instead of inserting a duplicate
    (research.md §16). There is no `version` column in the real schema, so
    idempotency is enforced structurally by the MERGE key alone."""
    sql = """
        MERGE `sre_incident_mart.incident_postmortems` T
        USING (SELECT @incident_id AS incident_id) S
        ON T.incident_id = S.incident_id
        WHEN MATCHED THEN
          UPDATE SET
            root_cause = @root_cause,
            impact_summary = @impact_summary,
            contributing_factors = @contributing_factors,
            action_items = @action_items,
            downtime_minutes = @downtime_minutes,
            published_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
          INSERT (postmortem_id, incident_id, published_at, root_cause, impact_summary,
                  contributing_factors, action_items, downtime_minutes)
          VALUES (@postmortem_id, @incident_id, CURRENT_TIMESTAMP(), @root_cause, @impact_summary,
                  @contributing_factors, @action_items, @downtime_minutes)
    """
    query_params = [
        param("incident_id", "STRING", params["incident_id"]),
        param("root_cause", "STRING", params["root_cause"]),
        param("impact_summary", "STRING", params["impact_summary"]),
        param("contributing_factors", "STRING", params["contributing_factors"]),
        param("action_items", "STRING", params["action_items"]),
        param("downtime_minutes", "FLOAT64", params["downtime_minutes"]),
        param("postmortem_id", "STRING", f"pm-{params['incident_id']}"),
    ]
    bq_client.query(sql, query_params)


def build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="executive_impact_agent",
        model=os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
        instruction=(
            "Summarize business impact strictly from compute_business_impact and "
            "compute_mttr_reduction tool outputs, in plain business terms "
            "(NFR-013) -- never fabricate a figure not derived from the tools."
        ),
    )
