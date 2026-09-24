"""T64: ADK agent-eval smoke test against a held-out warehouse subset.

Confirms the deterministic clustering/mapping/matching functions (which
every agent's LlmAgent wraps as tools) are demonstrably data-derived: their
output changes when fed DIFFERENT held-out fixture data, rather than
returning a fixed answer regardless of input -- evidence against
memorization/hardcoding (NFR-011).

A full ADK `Runner`-based agent-eval (actually invoking Gemini against a
held-out `alert_stream`/`runbooks` slice) requires live Vertex AI
credentials and is run manually per quickstart.md; this smoke test is the
CI-safe proxy that runs everywhere.
"""

from agents.alert_correlation.agent import decide_cluster, resolve_topology_mapping
from agents.runbook_retrieval.agent import build_match_response


def test_clustering_output_changes_with_different_held_out_input():
    """If the agent's tool were hardcoded, both fixture sets would produce
    the same incident_count regardless of their actual node/service
    overlap -- they must not."""
    fixture_a = [
        {"replayEventId": "r1", "alertId": "a1", "nodeId": "node-A", "serviceName": "svc-A"},
        {"replayEventId": "r2", "alertId": "a2", "nodeId": "node-A", "serviceName": "svc-A"},
    ]
    fixture_b = [
        {"replayEventId": "r3", "alertId": "a3", "nodeId": "node-B", "serviceName": "svc-B"},
        {"replayEventId": "r4", "alertId": "a4", "nodeId": "node-C", "serviceName": "svc-C"},
    ]

    result_a = decide_cluster(fixture_a, existing_clusters=[])
    result_b = decide_cluster(fixture_b, existing_clusters=[])

    assert result_a.incident_count == 1  # fixture_a's alerts share node/service -> 1 cluster
    assert result_b.incident_count == 2  # fixture_b's alerts share neither -> 2 clusters


def test_topology_mapping_reflects_held_out_lookup_table_not_a_fixed_answer():
    held_out_nodes = {"node-held-out-1": {"node_id": "node-held-out-1", "node_name": "held-out-svc"}}
    mapped = resolve_topology_mapping("node-held-out-1", held_out_nodes)
    unmapped = resolve_topology_mapping("node-never-seen", held_out_nodes)
    assert mapped["mapped"] is True
    assert unmapped["mapped"] is False


def test_runbook_match_response_reflects_held_out_distance_not_a_fixed_score():
    close_match = build_match_response([{"runbook_id": "held-out-rb", "distance": 0.05, "remediation_steps": "x"}])
    far_match = build_match_response([{"runbook_id": "held-out-rb", "distance": 0.95, "remediation_steps": "x"}])
    assert close_match["similarityScore"] != far_match["similarityScore"]
    assert close_match["belowThreshold"] != far_match["belowThreshold"]
