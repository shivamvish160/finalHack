"""Runbook Retrieval Agent (T38, FR-012 through FR-014).

ADK `LlmAgent` (gemini-2.5-flash) that embeds the root-cause query text via
`AI.GENERATE_EMBEDDING` (reusing the EXISTING `sre_knowledge_base.
embedding_model` -- never re-embedding the runbooks corpus itself, FR-003)
and runs `VECTOR_SEARCH` over the existing `runbooks.embedding` column.
Never falls back to keyword/`LIKE` matching (FR-012).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.common.bq_client import BigQueryClient, param  # noqa: E402

DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("RUNBOOK_SIMILARITY_THRESHOLD", "0.72"))


def find_matching_runbooks(bq_client: BigQueryClient, query_text: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Live VECTOR_SEARCH over the existing runbooks.embedding column.

    Query text is embedded at RETRIEVAL time only (research.md §2/§4) --
    the runbooks corpus itself is never re-embedded by this platform.
    """
    sql = """
        SELECT base.runbook_id, base.title, base.recommended_actions, distance
        FROM VECTOR_SEARCH(
            (SELECT runbook_id, title, recommended_actions, embedding FROM `sre_knowledge_base.runbooks`),
            'embedding',
            (
                SELECT ml_generate_embedding_result AS embedding
                FROM ML.GENERATE_EMBEDDING(
                    MODEL `sre_knowledge_base.embedding_model`,
                    (SELECT @query_text AS content)
                )
            ),
            top_k => @top_k,
            distance_type => 'COSINE'
        )
    """
    return bq_client.query_json_rows(
        sql,
        [param("query_text", "STRING", query_text), param("top_k", "INT64", top_k)],
    )


def build_match_response(matches: list[dict[str, Any]], threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> dict[str, Any]:
    """Convert raw VECTOR_SEARCH rows (cosine `distance`) into the
    FR-012/FR-014 response shape, applying the below-threshold rule."""
    if not matches:
        return {"runbookId": None, "similarityScore": 0.0, "recommendedActions": None, "belowThreshold": True}

    best = min(matches, key=lambda m: m["distance"])
    similarity = round(1.0 - best["distance"], 4)
    return {
        "runbookId": best["runbook_id"],
        "similarityScore": similarity,
        "recommendedActions": best.get("recommended_actions"),
        "belowThreshold": similarity < threshold,
    }


def build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="runbook_retrieval_agent",
        model=os.environ.get("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
        instruction=(
            "Use find_matching_runbooks (BigQuery VECTOR_SEARCH) exclusively -- "
            "never keyword or LIKE matching. Present the matched runbook's own "
            "documented actions verbatim; never invent remediation steps not "
            "present in the matched runbook (NFR-011)."
        ),
    )
