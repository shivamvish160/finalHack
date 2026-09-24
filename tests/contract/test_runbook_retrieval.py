"""T34: contract test for runbook retrieval (VECTOR_SEARCH response shape, belowThreshold case)."""

from agents.runbook_retrieval.agent import build_match_response


def test_match_above_threshold_includes_similarity_and_actions():
    result = build_match_response(
        matches=[{"runbook_id": "rb-1", "title": "Restart checkout pods", "distance": 0.18, "remediation_steps": "kubectl rollout restart"}],
        threshold=0.72,
    )
    assert result["belowThreshold"] is False
    assert result["runbookId"] == "rb-1"
    assert 0.0 <= result["similarityScore"] <= 1.0
    assert result["recommendedActions"]


def test_no_matches_sets_below_threshold():
    result = build_match_response(matches=[], threshold=0.72)
    assert result["belowThreshold"] is True
    assert result["runbookId"] is None


def test_low_similarity_match_sets_below_threshold():
    # distance 0.9 -> similarity 0.1, well under the 0.72 threshold
    result = build_match_response(
        matches=[{"runbook_id": "rb-2", "title": "Unrelated", "distance": 0.9, "remediation_steps": "n/a"}],
        threshold=0.72,
    )
    assert result["belowThreshold"] is True
