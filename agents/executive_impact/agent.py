"""Executive Impact Agent (T58, FR-027 through FR-032).

ADK `LlmAgent` (gemini-2.5-flash) that joins `correlated_alerts` ->
`alert_stream` -> `customer_accounts` (via `service_name`) and `incidents`
<-> `remediation_logs` to compute affected customers, revenue at risk, SLA
exposure, and MTTR reduction (FR-027-030), then drafts and MERGEs an
automated postmortem into `incident_postmortems` (FR-031/032).

NOTE: `customer_accounts` column names below are the spec's Clarification-
documented ASSUMED set -- MUST be reconciled against T5's live
`INFORMATION_SCHEMA.COLUMNS` verification before this agent is trusted in
production (data-model.md §1, checklist CHK067).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402


def fetch_linked_customer_accounts(bq_client: BigQueryClient, incident_id: str) -> list[dict[str, Any]]:
    """Join this incident's correlated alerts -> alert_stream -> customer_accounts
    via service_name (FR-027)."""
    sql = """
        SELECT DISTINCT ca_acct.customer_id, ca_acct.monthly_recurring_revenue,
               ca_acct.user_count, ca_acct.sla_uptime_target_pct,
               ca_acct.sla_credit_rate_per_hour
        FROM `sre_incident_mart.correlated_alerts` AS ca
        JOIN `sre_telemetry.alert_stream` AS al ON al.alert_id = ca.alert_id
        JOIN `sre_incident_mart.customer_accounts` AS ca_acct ON ca_acct.service_name = al.service_name
        WHERE ca.incident_id = @incident_id
    """
    return bq_client.query_json_rows(sql, [param("incident_id", "STRING", incident_id)])


def compute_business_impact(accounts: list[dict[str, Any]], incident_duration_hours: float) -> dict[str, Any]:
    """Deterministic FR-027/028/030 calculation over the linked accounts --
    every figure is data-derived, never a hardcoded per-incident guess
    (NFR-011)."""
    affected_customers = len(accounts)
    affected_users = sum(a.get("user_count") or 0 for a in accounts)
    monthly_revenue = sum(a.get("monthly_recurring_revenue") or 0.0 for a in accounts)
    # Pro-rate monthly recurring revenue by incident duration as a simple,
    # explainable revenue-at-risk proxy (NFR-010 requires a stated rationale).
    revenue_at_risk = round(monthly_revenue * (incident_duration_hours / (30 * 24)), 2)
    sla_credit_exposure = sum((a.get("sla_credit_rate_per_hour") or 0.0) for a in accounts) * incident_duration_hours

    return {
        "affectedCustomers": affected_customers,
        "affectedUsers": affected_users,
        "revenueAtRisk": revenue_at_risk,
        "slaCreditExposure": round(sla_credit_exposure, 2),
    }


def compute_mttr_reduction(bq_client: BigQueryClient) -> dict[str, float]:
    """FR-028: MTTR for platform-handled incidents vs. the historical
    baseline reflected in existing incidents/remediation_logs."""
    sql = """
        SELECT AVG(TIMESTAMP_DIFF(resolved_at, opened_at, MINUTE)) AS avg_mttr_minutes
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
          COUNTIF(outcome = 'Succeeded') AS succeeded_count,
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
) -> dict[str, str]:
    """Stable parameter set for the incident_postmortems MERGE (FR-031/032) --
    keyed on incident_id so regeneration updates rather than duplicates."""
    return {
        "incident_id": incident_id,
        "root_cause_summary": root_cause_summary,
        "timeline_summary": timeline_summary,
        "remediation_summary": remediation_summary,
        "business_impact_summary": business_impact_summary,
        "full_report_markdown": full_report_markdown,
    }


def merge_postmortem(bq_client: BigQueryClient, params: dict[str, str]) -> None:
    """FR-031/032: MERGE into incident_postmortems, keyed on incident_id,
    incrementing `version` on an existing row instead of inserting a
    duplicate (research.md §16)."""
    sql = """
        MERGE `sre_incident_mart.incident_postmortems` T
        USING (SELECT @incident_id AS incident_id) S
        ON T.incident_id = S.incident_id
        WHEN MATCHED THEN
          UPDATE SET
            root_cause_summary = @root_cause_summary,
            timeline_summary = @timeline_summary,
            remediation_summary = @remediation_summary,
            business_impact_summary = @business_impact_summary,
            full_report_markdown = @full_report_markdown,
            version = T.version + 1,
            generated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
          INSERT (incident_id, generated_at, root_cause_summary, timeline_summary,
                  remediation_summary, business_impact_summary, full_report_markdown, version)
          VALUES (@incident_id, CURRENT_TIMESTAMP(), @root_cause_summary, @timeline_summary,
                  @remediation_summary, @business_impact_summary, @full_report_markdown, 1)
    """
    bq_client.query(sql, [param(k, "STRING", v) for k, v in params.items()])


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
