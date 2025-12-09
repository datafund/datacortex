"""Centrality metrics for the knowledge graph."""

from typing import Optional

import networkx as nx

from ..core.models import Edge, Node


def compute_pagerank(nodes: list[Node], edges: list[Edge], damping: float = 0.85) -> None:
    """Compute PageRank centrality and update nodes in place.

    Args:
        nodes: List of nodes to update
        edges: List of edges for the graph
        damping: PageRank damping factor (default 0.85)
    """
    G = nx.DiGraph()

    # Add all nodes
    for node in nodes:
        G.add_node(node.id)

    # Add edges (only resolved ones contribute to PageRank)
    for edge in edges:
        if edge.resolved:
            G.add_edge(edge.source, edge.target, weight=edge.weight)

    # Compute PageRank
    try:
        pagerank = nx.pagerank(G, alpha=damping, weight='weight')
    except nx.PowerIterationFailedConvergence:
        # Fall back to simpler calculation
        pagerank = {node.id: 1.0 / len(nodes) for node in nodes}

    # Normalize to 0-1 range
    max_pr = max(pagerank.values()) if pagerank else 1.0
    if max_pr == 0:
        max_pr = 1.0

    # Update nodes
    for node in nodes:
        node.centrality = pagerank.get(node.id, 0.0) / max_pr


def compute_betweenness(nodes: list[Node], edges: list[Edge]) -> dict[str, float]:
    """Compute betweenness centrality.

    Returns dict mapping node_id to betweenness score (does not update nodes).
    """
    G = nx.Graph()

    for node in nodes:
        G.add_node(node.id)

    for edge in edges:
        if edge.resolved:
            G.add_edge(edge.source, edge.target)

    return nx.betweenness_centrality(G)


def compute_eigenvector(nodes: list[Node], edges: list[Edge]) -> dict[str, float]:
    """Compute eigenvector centrality.

    Returns dict mapping node_id to eigenvector score.
    """
    G = nx.Graph()

    for node in nodes:
        G.add_node(node.id)

    for edge in edges:
        if edge.resolved:
            G.add_edge(edge.source, edge.target)

    try:
        return nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        # Fall back to degree centrality
        return nx.degree_centrality(G)


def find_hubs(nodes: list[Node], top_n: int = 10) -> list[Node]:
    """Find the most central nodes (hubs).

    Args:
        nodes: List of nodes with centrality computed
        top_n: Number of top nodes to return

    Returns:
        Top N nodes by centrality
    """
    sorted_nodes = sorted(nodes, key=lambda n: n.centrality, reverse=True)
    return sorted_nodes[:top_n]
