"""Build knowledge graph from Datacore database."""

from datetime import datetime
from typing import Optional

from ..core.config import DatacortexConfig
from ..core.database import get_connection, space_exists
from ..core.models import Edge, Graph, GraphStats, Node, NodeType


def map_type(db_type: str) -> NodeType:
    """Map database file type to NodeType enum."""
    type_map = {
        'zettel': NodeType.ZETTEL,
        'page': NodeType.PAGE,
        'journal': NodeType.JOURNAL,
        'literature': NodeType.LITERATURE,
        'clipping': NodeType.CLIPPING,
        'org_task': NodeType.ORG_TASK,
        'stub': NodeType.STUB,
    }
    return type_map.get(db_type, NodeType.UNKNOWN)


def build_graph(
    spaces: Optional[list[str]] = None,
    config: Optional[DatacortexConfig] = None
) -> Graph:
    """Build knowledge graph from datacore database.

    Args:
        spaces: List of spaces to include (default: from config)
        config: Configuration (default: load from files)

    Returns:
        Graph with nodes and edges
    """
    if config is None:
        from ..core.config import load_config
        config = load_config()

    if spaces is None:
        spaces = config.spaces

    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_node_ids: set[str] = set()
    tags_map: dict[str, list[str]] = {}

    for space in spaces:
        if not space_exists(space):
            continue

        conn = get_connection(space)
        cursor = conn.cursor()

        # Fetch all files
        cursor.execute("""
            SELECT id, path, space, type, title, word_count,
                   maturity, is_stub, created_at, updated_at
            FROM files
        """)

        for row in cursor.fetchall():
            if row['id'] in seen_node_ids:
                continue

            # Filter stubs if configured
            if row['is_stub'] and not config.graph.include_stubs:
                continue

            node = Node(
                id=row['id'],
                title=row['title'] or row['id'],
                path=row['path'],
                space=row['space'],
                type=map_type(row['type']),
                maturity=row['maturity'],
                is_stub=bool(row['is_stub']),
                word_count=row['word_count'] or 0,
                created_at=parse_datetime(row['created_at']),
                updated_at=parse_datetime(row['updated_at']),
            )
            nodes.append(node)
            seen_node_ids.add(row['id'])

        # Fetch all links
        cursor.execute("""
            SELECT source_id, target_id, target_title, syntax, resolved
            FROM links
        """)

        for row in cursor.fetchall():
            source_id = row['source_id']
            target_id = row['target_id'] or row['target_title']
            resolved = bool(row['resolved'])

            # Skip unresolved if configured
            if not resolved and not config.graph.include_unresolved:
                continue

            # Skip if source not in our node set
            if source_id not in seen_node_ids:
                continue

            edge = Edge(
                id=f"{source_id}->{target_id}",
                source=source_id,
                target=target_id,
                syntax=row['syntax'] or 'wiki-link',
                resolved=resolved,
            )
            edges.append(edge)

        # Fetch tags
        cursor.execute("""
            SELECT file_id, GROUP_CONCAT(normalized_tag, ',') as tags
            FROM tags
            GROUP BY file_id
        """)

        for row in cursor.fetchall():
            if row['tags']:
                tags_map[row['file_id']] = [t for t in row['tags'].split(',') if t]

        conn.close()

    # Attach tags to nodes
    for node in nodes:
        node.tags = tags_map.get(node.id, [])

    # Compute degrees
    compute_degrees(nodes, edges)

    # Compute centrality if configured
    if config.graph.compute_centrality:
        from ..metrics.centrality import compute_pagerank
        compute_pagerank(nodes, edges)

    # Compute clusters if configured
    cluster_count = 0
    if config.graph.compute_clusters:
        from ..metrics.clusters import compute_clusters
        cluster_count = compute_clusters(nodes, edges)

    # Filter by min_degree if configured
    if config.graph.min_degree > 0:
        nodes = [n for n in nodes if n.degree >= config.graph.min_degree]
        valid_ids = {n.id for n in nodes}
        edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]

    # Compute stats
    stats = compute_stats(nodes, edges)
    stats.cluster_count = cluster_count

    return Graph(
        nodes=nodes,
        edges=edges,
        spaces=spaces,
        generated_at=datetime.now(),
        stats=stats,
    )


def compute_degrees(nodes: list[Node], edges: list[Edge]) -> None:
    """Compute in/out/total degree for each node in place."""
    in_degree: dict[str, int] = {}
    out_degree: dict[str, int] = {}

    for edge in edges:
        out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
        if edge.resolved:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    for node in nodes:
        node.in_degree = in_degree.get(node.id, 0)
        node.out_degree = out_degree.get(node.id, 0)
        node.degree = node.in_degree + node.out_degree


def compute_stats(nodes: list[Node], edges: list[Edge]) -> GraphStats:
    """Compute graph statistics."""
    resolved_count = sum(1 for e in edges if e.resolved)
    degrees = [n.degree for n in nodes]
    orphan_count = sum(1 for d in degrees if d == 0)

    nodes_by_type: dict[str, int] = {}
    nodes_by_space: dict[str, int] = {}

    for node in nodes:
        type_key = node.type.value
        nodes_by_type[type_key] = nodes_by_type.get(type_key, 0) + 1
        nodes_by_space[node.space] = nodes_by_space.get(node.space, 0) + 1

    return GraphStats(
        node_count=len(nodes),
        edge_count=len(edges),
        resolved_edges=resolved_count,
        unresolved_edges=len(edges) - resolved_count,
        avg_degree=sum(degrees) / len(degrees) if degrees else 0.0,
        max_degree=max(degrees) if degrees else 0,
        orphan_count=orphan_count,
        nodes_by_type=nodes_by_type,
        nodes_by_space=nodes_by_space,
    )


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from database."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
