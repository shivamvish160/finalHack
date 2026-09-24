"""T23: integration test for referential-gap handling (FR-005) -- an alert
whose node_id/service_name has no matching warehouse row must be clustered
and marked Unmapped, never dropped."""

from agents.alert_correlation.agent import resolve_topology_mapping


def test_orphaned_node_id_is_marked_unmapped_not_dropped():
    known_nodes = {"node-1": {"node_id": "node-1", "node_name": "checkout-db", "region": "us-central1"}}
    result = resolve_topology_mapping(node_id="node-does-not-exist", known_nodes=known_nodes)
    assert result["mapped"] is False
    assert result["node_id"] == "node-does-not-exist"


def test_known_node_id_is_marked_mapped_with_details():
    known_nodes = {"node-1": {"node_id": "node-1", "node_name": "checkout-db", "region": "us-central1"}}
    result = resolve_topology_mapping(node_id="node-1", known_nodes=known_nodes)
    assert result["mapped"] is True
    assert result["node_name"] == "checkout-db"
