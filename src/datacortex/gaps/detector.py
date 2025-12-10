"""Gap detection logic for knowledge clusters."""

from dataclasses import dataclass
from datetime import datetime
from collections import Counter

import numpy as np
import networkx as nx

from ..ai.embeddings import compute_embeddings_for_space
from ..ai.similarity import cosine_similarity
from ..core.database import get_connection, space_exists
from ..indexer.graph_builder import build_graph
from ..metrics.clusters import compute_clusters


@dataclass
class ClusterInfo:
    """Information about a cluster."""
    cluster_id: int
    size: int
    hub_docs: list[str]  # top 5 by centrality
    top_tags: list[tuple[str, int]]  # tag, count


@dataclass
class KnowledgeGap:
    """A gap between two semantically similar but poorly connected clusters."""
    cluster_a: int
    cluster_b: int
    semantic_similarity: float  # cosine sim of cluster centroids
    link_density: float  # actual links / max possible
    cross_links: int  # actual link count
    gap_score: float  # semantic_sim - link_density
    cluster_a_info: ClusterInfo
    cluster_b_info: ClusterInfo
    shared_tags: list[str]
    boundary_nodes: list[str]  # nodes that link to both clusters


@dataclass
class GapsResult:
    """Complete result of gap detection."""
    gaps: list[KnowledgeGap]
    cluster_count: int
    generated_at: str


def get_cluster_centroid(cluster_members: list[str], embeddings: dict) -> np.ndarray:
    """Compute average embedding of cluster members.

    Args:
        cluster_members: List of file IDs in cluster
        embeddings: Dict mapping file_id to embedding vector

    Returns:
        Centroid vector (average of member embeddings)
    """
    member_embeddings = []
    for member_id in cluster_members:
        if member_id in embeddings:
            member_embeddings.append(embeddings[member_id])

    if not member_embeddings:
        # Return zero vector if no embeddings found
        return np.zeros(768)  # Default embedding dimension

    # Average the embeddings
    centroid = np.mean(member_embeddings, axis=0)
    return centroid


def get_cluster_info(cluster_id: int, members: list, graph) -> ClusterInfo:
    """Extract hub docs (top 5 centrality) and top tags for cluster.

    Args:
        cluster_id: Cluster identifier
        members: List of Node objects in cluster
        graph: Graph object with nodes and edges

    Returns:
        ClusterInfo with size, hubs, and top tags
    """
    # Get top 5 by centrality (or degree as proxy)
    sorted_members = sorted(members, key=lambda n: n.centrality or n.degree, reverse=True)
    hub_docs = [node.title for node in sorted_members[:5]]

    # Count tags across all cluster members
    tag_counter = Counter()
    for node in members:
        for tag in node.tags:
            tag_counter[tag] += 1

    # Get top 5 tags
    top_tags = tag_counter.most_common(5)

    return ClusterInfo(
        cluster_id=cluster_id,
        size=len(members),
        hub_docs=hub_docs,
        top_tags=top_tags
    )


def find_boundary_nodes(cluster_a_members, cluster_b_members, edges) -> list[str]:
    """Find nodes that have links to both clusters.

    Args:
        cluster_a_members: List of Node objects in cluster A
        cluster_b_members: List of Node objects in cluster B
        edges: List of Edge objects

    Returns:
        List of node titles that bridge both clusters
    """
    cluster_a_ids = {node.id for node in cluster_a_members}
    cluster_b_ids = {node.id for node in cluster_b_members}

    boundary = set()

    # Check edges for nodes connecting both clusters
    for edge in edges:
        if not edge.resolved:
            continue

        source_in_a = edge.source in cluster_a_ids
        source_in_b = edge.source in cluster_b_ids
        target_in_a = edge.target in cluster_a_ids
        target_in_b = edge.target in cluster_b_ids

        # If source is in one cluster and target in the other
        if (source_in_a and target_in_b) or (source_in_b and target_in_a):
            # Find the node objects
            for node in cluster_a_members + cluster_b_members:
                if node.id == edge.source or node.id == edge.target:
                    boundary.add(node.title)

    return sorted(list(boundary))


def find_shared_tags(cluster_a_members, cluster_b_members) -> list[str]:
    """Find tags that appear in both clusters.

    Args:
        cluster_a_members: List of Node objects in cluster A
        cluster_b_members: List of Node objects in cluster B

    Returns:
        List of shared tag names
    """
    tags_a = set()
    for node in cluster_a_members:
        tags_a.update(node.tags)

    tags_b = set()
    for node in cluster_b_members:
        tags_b.update(node.tags)

    shared = tags_a & tags_b
    return sorted(list(shared))


def count_cross_links(cluster_a_members, cluster_b_members, edges) -> int:
    """Count edges between the two clusters.

    Args:
        cluster_a_members: List of Node objects in cluster A
        cluster_b_members: List of Node objects in cluster B
        edges: List of Edge objects

    Returns:
        Number of edges connecting the clusters
    """
    cluster_a_ids = {node.id for node in cluster_a_members}
    cluster_b_ids = {node.id for node in cluster_b_members}

    cross_link_count = 0

    for edge in edges:
        if not edge.resolved:
            continue

        source_in_a = edge.source in cluster_a_ids
        source_in_b = edge.source in cluster_b_ids
        target_in_a = edge.target in cluster_a_ids
        target_in_b = edge.target in cluster_b_ids

        # Count if edge connects the two clusters
        if (source_in_a and target_in_b) or (source_in_b and target_in_a):
            cross_link_count += 1

    return cross_link_count


def detect_gaps(spaces: list[str], min_gap_score: float = 0.3) -> GapsResult:
    """Detect knowledge gaps between clusters.

    Args:
        spaces: List of space names to analyze
        min_gap_score: Minimum gap score threshold (default 0.3)

    Returns:
        GapsResult with detected gaps sorted by gap_score descending

    Algorithm:
        1. Build graph and compute clusters using Louvain
        2. Load embeddings for all nodes
        3. Compute cluster centroids (mean of member embeddings)
        4. For each cluster pair:
           - Compute semantic similarity (cosine of centroids)
           - Compute link density (cross_links / (size_a * size_b))
           - gap_score = semantic_sim - link_density
        5. Filter to gaps above threshold
        6. Find boundary nodes and shared tags
        7. Return sorted by gap_score descending
    """
    print(f"Building graph from spaces: {', '.join(spaces)}")

    # Build graph with clustering
    from ..core.config import load_config
    config = load_config()
    graph = build_graph(spaces=spaces, config=config)

    # Ensure clustering is computed
    if graph.stats.cluster_count == 0:
        print("Computing clusters...")
        cluster_count = compute_clusters(graph.nodes, graph.edges)
        graph.stats.cluster_count = cluster_count
    else:
        print(f"Using existing {graph.stats.cluster_count} clusters")

    # Load embeddings for all spaces
    all_embeddings = {}
    for space in spaces:
        if not space_exists(space):
            continue

        print(f"Loading embeddings for space: {space}")
        space_embeddings = compute_embeddings_for_space(space, force=False)
        all_embeddings.update(space_embeddings)

    print(f"Loaded {len(all_embeddings)} embeddings")

    # Group nodes by cluster
    clusters = {}
    for node in graph.nodes:
        cluster_id = node.cluster_id if node.cluster_id is not None else 0
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(node)

    print(f"Analyzing {len(clusters)} clusters")

    # Compute cluster centroids
    cluster_centroids = {}
    for cluster_id, members in clusters.items():
        member_ids = [node.id for node in members]
        centroid = get_cluster_centroid(member_ids, all_embeddings)
        cluster_centroids[cluster_id] = centroid

    # Analyze all cluster pairs
    gaps = []
    cluster_ids = sorted(clusters.keys())

    for i, cluster_a_id in enumerate(cluster_ids):
        for cluster_b_id in cluster_ids[i+1:]:
            cluster_a_members = clusters[cluster_a_id]
            cluster_b_members = clusters[cluster_b_id]

            size_a = len(cluster_a_members)
            size_b = len(cluster_b_members)

            # Skip if clusters are too small
            if size_a < 3 or size_b < 3:
                continue

            # Compute semantic similarity of centroids
            centroid_a = cluster_centroids[cluster_a_id]
            centroid_b = cluster_centroids[cluster_b_id]

            # Check if centroids are valid (not all zeros)
            if np.all(centroid_a == 0) or np.all(centroid_b == 0):
                continue

            semantic_sim = cosine_similarity(centroid_a, centroid_b)

            # Count cross links
            cross_links = count_cross_links(cluster_a_members, cluster_b_members, graph.edges)

            # Compute link density (actual / max possible)
            max_possible_links = size_a * size_b
            link_density = cross_links / max_possible_links if max_possible_links > 0 else 0.0

            # Compute gap score
            gap_score = semantic_sim - link_density

            # Filter by threshold
            if gap_score < min_gap_score:
                continue

            # Get cluster info
            cluster_a_info = get_cluster_info(cluster_a_id, cluster_a_members, graph)
            cluster_b_info = get_cluster_info(cluster_b_id, cluster_b_members, graph)

            # Find shared tags and boundary nodes
            shared_tags = find_shared_tags(cluster_a_members, cluster_b_members)
            boundary_nodes = find_boundary_nodes(cluster_a_members, cluster_b_members, graph.edges)

            gap = KnowledgeGap(
                cluster_a=cluster_a_id,
                cluster_b=cluster_b_id,
                semantic_similarity=semantic_sim,
                link_density=link_density,
                cross_links=cross_links,
                gap_score=gap_score,
                cluster_a_info=cluster_a_info,
                cluster_b_info=cluster_b_info,
                shared_tags=shared_tags,
                boundary_nodes=boundary_nodes
            )
            gaps.append(gap)

    # Sort by gap score descending
    gaps.sort(key=lambda g: -g.gap_score)

    print(f"Found {len(gaps)} knowledge gaps above threshold {min_gap_score}")

    return GapsResult(
        gaps=gaps,
        cluster_count=len(clusters),
        generated_at=datetime.now().isoformat()
    )
