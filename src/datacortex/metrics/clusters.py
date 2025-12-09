"""Community detection and clustering for the knowledge graph."""

from typing import Optional

import networkx as nx

from ..core.models import Edge, GraphStats, Node


def compute_clusters(nodes: list[Node], edges: list[Edge]) -> int:
    """Detect communities using Louvain algorithm and update nodes in place.

    Args:
        nodes: List of nodes to update with cluster_id
        edges: List of edges for the graph

    Returns:
        Number of clusters found
    """
    G = nx.Graph()

    # Add all nodes
    for node in nodes:
        G.add_node(node.id)

    # Add edges (undirected for community detection)
    for edge in edges:
        if edge.resolved:
            # NetworkX doesn't allow self-loops for community detection
            if edge.source != edge.target:
                G.add_edge(edge.source, edge.target)

    # Use Louvain community detection
    try:
        from community import community_louvain
        partition = community_louvain.best_partition(G)
    except ImportError:
        # Fall back to networkx built-in (greedy modularity)
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = greedy_modularity_communities(G)
            partition = {}
            for i, community in enumerate(communities):
                for node_id in community:
                    partition[node_id] = i
        except Exception:
            # No clustering available
            for node in nodes:
                node.cluster_id = 0
            return 1

    # Update nodes with cluster IDs
    for node in nodes:
        node.cluster_id = partition.get(node.id, 0)

    # Count unique clusters
    cluster_count = len(set(partition.values())) if partition else 1
    return cluster_count


def get_cluster_stats(nodes: list[Node]) -> dict[int, dict]:
    """Get statistics for each cluster.

    Returns:
        Dict mapping cluster_id to stats (size, top nodes, types)
    """
    clusters: dict[int, list[Node]] = {}

    for node in nodes:
        cluster_id = node.cluster_id or 0
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(node)

    stats = {}
    for cluster_id, cluster_nodes in clusters.items():
        # Count types in cluster
        type_counts: dict[str, int] = {}
        for n in cluster_nodes:
            type_key = n.type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

        # Get top nodes by degree
        top_nodes = sorted(cluster_nodes, key=lambda n: n.degree, reverse=True)[:5]

        stats[cluster_id] = {
            'size': len(cluster_nodes),
            'types': type_counts,
            'top_nodes': [{'id': n.id, 'title': n.title, 'degree': n.degree} for n in top_nodes],
        }

    return stats


def find_bridges(nodes: list[Node], edges: list[Edge]) -> list[str]:
    """Find bridge nodes that connect different clusters.

    Returns:
        List of node IDs that are bridges between clusters
    """
    # Build adjacency with cluster info
    node_map = {n.id: n for n in nodes}
    bridges = []

    for edge in edges:
        if not edge.resolved:
            continue

        source_node = node_map.get(edge.source)
        target_node = node_map.get(edge.target)

        if source_node and target_node:
            if source_node.cluster_id != target_node.cluster_id:
                bridges.append(edge.source)
                bridges.append(edge.target)

    # Return unique bridge nodes
    return list(set(bridges))
