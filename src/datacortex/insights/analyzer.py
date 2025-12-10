"""Cluster analysis logic for knowledge insights."""

from dataclasses import dataclass
from datetime import datetime
from collections import Counter
from typing import Optional

import networkx as nx

from ..core.database import get_connection, space_exists
from ..indexer.graph_builder import build_graph
from ..metrics.clusters import compute_clusters


@dataclass
class ClusterAnalysis:
    """Detailed analysis of a single cluster."""
    cluster_id: int
    size: int
    stats: dict  # avg_words, total_words, avg_centrality, density
    hubs: list[dict]  # title, centrality, word_count, tags, path
    tag_freq: list[tuple[str, int]]  # tag, count - top 10
    connections: list[dict]  # cluster_id, link_count
    samples: list[dict]  # title, word_count, excerpt (500 chars)


@dataclass
class InsightsResult:
    """Complete result of cluster insight analysis."""
    clusters: list[ClusterAnalysis]
    total_docs: int
    total_clusters: int
    generated_at: str


def load_document_content(conn, file_id: str) -> str:
    """Load full content from files table.

    Args:
        conn: Database connection
        file_id: File ID to load

    Returns:
        Content string or empty string if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM files WHERE id = ?
    """, (file_id,))
    row = cursor.fetchone()
    return row['content'] if row else ""


def get_cluster_stats(members: list, edges: list) -> dict:
    """Compute statistics for a cluster.

    Args:
        members: List of Node objects in cluster
        edges: List of Edge objects for computing density

    Returns:
        Dict with avg_words, total_words, avg_centrality, density
    """
    if not members:
        return {
            'avg_words': 0,
            'total_words': 0,
            'avg_centrality': 0.0,
            'density': 0.0
        }

    total_words = sum(node.word_count for node in members)
    avg_words = total_words / len(members)

    centralities = [node.centrality for node in members if node.centrality is not None]
    avg_centrality = sum(centralities) / len(centralities) if centralities else 0.0

    # Compute density: actual edges / max possible edges
    member_ids = {node.id for node in members}
    internal_edges = 0

    for edge in edges:
        if edge.resolved and edge.source in member_ids and edge.target in member_ids:
            internal_edges += 1

    max_edges = (len(members) * (len(members) - 1)) / 2 if len(members) > 1 else 0
    density = internal_edges / max_edges if max_edges > 0 else 0.0

    return {
        'avg_words': int(avg_words),
        'total_words': total_words,
        'avg_centrality': round(avg_centrality, 3),
        'density': round(density, 3)
    }


def get_hub_documents(members: list, top_n: int = 10) -> list[dict]:
    """Get top documents by centrality with metadata.

    Args:
        members: List of Node objects
        top_n: Number of hubs to return

    Returns:
        List of dicts with title, centrality, word_count, tags, path
    """
    # Sort by centrality (use degree as fallback)
    sorted_members = sorted(
        members,
        key=lambda n: n.centrality if n.centrality is not None else n.degree,
        reverse=True
    )

    hubs = []
    for node in sorted_members[:top_n]:
        hubs.append({
            'title': node.title,
            'centrality': node.centrality if node.centrality is not None else 0.0,
            'word_count': node.word_count,
            'tags': node.tags[:5],  # Limit to top 5 tags
            'path': node.path
        })

    return hubs


def get_tag_frequency(members: list) -> list[tuple[str, int]]:
    """Get tag frequency counts across cluster members.

    Args:
        members: List of Node objects

    Returns:
        List of (tag, count) tuples, sorted by count descending
    """
    tag_counter = Counter()

    for node in members:
        for tag in node.tags:
            tag_counter[tag] += 1

    # Return top 10 tags
    return tag_counter.most_common(10)


def get_cluster_connections(cluster_id: int, all_clusters: dict, edges: list) -> list[dict]:
    """Get connections from this cluster to other clusters.

    Args:
        cluster_id: Current cluster ID
        all_clusters: Dict mapping cluster_id to list of Node objects
        edges: List of Edge objects

    Returns:
        List of dicts with cluster_id and link_count, sorted by count descending
    """
    # Get member IDs for current cluster
    current_members = {node.id for node in all_clusters[cluster_id]}

    # Count links to each other cluster
    connections = Counter()

    for edge in edges:
        if not edge.resolved:
            continue

        source_in_current = edge.source in current_members
        target_in_current = edge.target in current_members

        # Skip internal edges
        if source_in_current and target_in_current:
            continue

        # Find which cluster the other end is in
        other_node_id = None
        if source_in_current:
            other_node_id = edge.target
        elif target_in_current:
            other_node_id = edge.source

        if other_node_id:
            # Find which cluster this node belongs to
            for other_cluster_id, other_members in all_clusters.items():
                if other_cluster_id == cluster_id:
                    continue
                if any(node.id == other_node_id for node in other_members):
                    connections[other_cluster_id] += 1
                    break

    # Return sorted list
    result = [
        {'cluster_id': cid, 'link_count': count}
        for cid, count in connections.most_common(10)
    ]

    return result


def get_content_samples(members: list, conn, top_n: int = 5, excerpt_len: int = 500) -> list[dict]:
    """Load content excerpts for top documents.

    Args:
        members: List of Node objects
        conn: Database connection
        top_n: Number of samples to return
        excerpt_len: Maximum length of excerpt

    Returns:
        List of dicts with title, word_count, excerpt
    """
    # Sort by centrality (use word_count as secondary sort)
    sorted_members = sorted(
        members,
        key=lambda n: (
            n.centrality if n.centrality is not None else 0,
            n.word_count
        ),
        reverse=True
    )

    samples = []
    for node in sorted_members[:top_n]:
        # Load content
        content = load_document_content(conn, node.id)

        # Extract excerpt (first excerpt_len chars, clean up)
        excerpt = content[:excerpt_len].strip()
        if len(content) > excerpt_len:
            # Try to break at sentence or word boundary
            last_period = excerpt.rfind('.')
            last_space = excerpt.rfind(' ')
            if last_period > excerpt_len * 0.7:
                excerpt = excerpt[:last_period + 1]
            elif last_space > excerpt_len * 0.7:
                excerpt = excerpt[:last_space] + '...'
            else:
                excerpt = excerpt + '...'

        samples.append({
            'title': node.title,
            'word_count': node.word_count,
            'excerpt': excerpt
        })

    return samples


def analyze_single_cluster(cluster_id: int, spaces: list[str]) -> ClusterAnalysis:
    """Detailed analysis for one cluster.

    Args:
        cluster_id: Cluster ID to analyze
        spaces: List of space names

    Returns:
        ClusterAnalysis with full details
    """
    from ..core.config import load_config
    config = load_config()

    # Build graph
    graph = build_graph(spaces=spaces, config=config)

    # Ensure clustering is computed
    if graph.stats.cluster_count == 0:
        compute_clusters(graph.nodes, graph.edges)

    # Group by cluster
    clusters = {}
    for node in graph.nodes:
        cid = node.cluster_id if node.cluster_id is not None else 0
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(node)

    if cluster_id not in clusters:
        raise ValueError(f"Cluster {cluster_id} not found")

    members = clusters[cluster_id]

    # Get database connection for content loading
    conn = get_connection(spaces[0]) if spaces else get_connection('datafund')

    # Compute analysis
    stats = get_cluster_stats(members, graph.edges)
    hubs = get_hub_documents(members, top_n=10)
    tag_freq = get_tag_frequency(members)
    connections = get_cluster_connections(cluster_id, clusters, graph.edges)
    samples = get_content_samples(members, conn, top_n=5)

    return ClusterAnalysis(
        cluster_id=cluster_id,
        size=len(members),
        stats=stats,
        hubs=hubs,
        tag_freq=tag_freq,
        connections=connections,
        samples=samples
    )


def analyze_clusters(spaces: list[str]) -> InsightsResult:
    """Analyze all clusters and extract insights.

    Args:
        spaces: List of space names to analyze

    Returns:
        InsightsResult with analysis for all clusters, sorted by size descending

    Algorithm:
        1. Build graph and compute Louvain clusters
        2. For each cluster:
           - Compute stats (avg words, density, centrality)
           - Get hub documents (top 10 by centrality)
           - Get tag frequency (top 10 tags)
           - Get connections to other clusters
           - Sample content (top 5 docs, first 500 chars)
        3. Return sorted by cluster size descending
    """
    print(f"Building graph from spaces: {', '.join(spaces)}")

    from ..core.config import load_config
    config = load_config()

    # Build graph with clustering
    graph = build_graph(spaces=spaces, config=config)

    # Ensure clustering is computed
    if graph.stats.cluster_count == 0:
        print("Computing clusters...")
        cluster_count = compute_clusters(graph.nodes, graph.edges)
        graph.stats.cluster_count = cluster_count
    else:
        print(f"Using existing {graph.stats.cluster_count} clusters")

    # Group nodes by cluster
    clusters = {}
    for node in graph.nodes:
        cluster_id = node.cluster_id if node.cluster_id is not None else 0
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(node)

    print(f"Analyzing {len(clusters)} clusters")

    # Get database connection for content loading
    # Use first available space
    conn = None
    for space in spaces:
        if space_exists(space):
            conn = get_connection(space)
            break

    if conn is None:
        # Fallback
        conn = get_connection('datafund')

    # Analyze each cluster
    cluster_analyses = []

    for cluster_id in sorted(clusters.keys()):
        members = clusters[cluster_id]

        # Skip very small clusters
        if len(members) < 3:
            continue

        print(f"  Cluster {cluster_id}: {len(members)} nodes")

        stats = get_cluster_stats(members, graph.edges)
        hubs = get_hub_documents(members, top_n=10)
        tag_freq = get_tag_frequency(members)
        connections = get_cluster_connections(cluster_id, clusters, graph.edges)
        samples = get_content_samples(members, conn, top_n=5)

        analysis = ClusterAnalysis(
            cluster_id=cluster_id,
            size=len(members),
            stats=stats,
            hubs=hubs,
            tag_freq=tag_freq,
            connections=connections,
            samples=samples
        )

        cluster_analyses.append(analysis)

    # Sort by size descending
    cluster_analyses.sort(key=lambda c: -c.size)

    print(f"Completed analysis of {len(cluster_analyses)} clusters")

    return InsightsResult(
        clusters=cluster_analyses,
        total_docs=len(graph.nodes),
        total_clusters=len(clusters),
        generated_at=datetime.now().isoformat()
    )
