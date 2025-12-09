"""Graph API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from ...core.config import load_config
from ...indexer.graph_builder import build_graph

router = APIRouter()


@router.get("")
@router.get("/")
async def get_graph(
    spaces: Optional[str] = Query(None, description="Comma-separated list of spaces"),
    types: Optional[str] = Query(None, description="Comma-separated list of node types"),
    min_degree: int = Query(0, description="Minimum degree filter"),
    include_stubs: bool = Query(True, description="Include stub nodes"),
):
    """Get current graph data for D3 visualization.

    Returns nodes and links in D3-compatible format.
    """
    config = load_config()

    # Parse space list
    if spaces:
        space_list = [s.strip() for s in spaces.split(',')]
    else:
        space_list = config.spaces

    # Override config for this request
    config.graph.include_stubs = include_stubs
    config.graph.min_degree = min_degree

    graph = build_graph(spaces=space_list, config=config)

    # Filter by types if specified
    nodes = graph.nodes
    if types:
        type_list = [t.strip().lower() for t in types.split(',')]
        nodes = [n for n in nodes if n.type.value in type_list]
        # Also filter edges
        valid_ids = {n.id for n in nodes}
        edges = [e for e in graph.edges if e.source in valid_ids]
    else:
        edges = graph.edges

    return {
        "nodes": [n.model_dump(mode='json') for n in nodes],
        "links": [e.model_dump(mode='json') for e in edges],
        "spaces": graph.spaces,
        "generated_at": graph.generated_at.isoformat(),
        "stats": graph.stats.model_dump(),
    }


@router.get("/subgraph/{node_id}")
async def get_subgraph(
    node_id: str,
    depth: int = Query(2, description="Depth of subgraph (1-3)"),
):
    """Get subgraph centered on a specific node (ego network).

    Returns the node and all nodes within `depth` hops.
    """
    config = load_config()
    graph = build_graph(config=config)

    # Find the center node
    center_node = None
    for node in graph.nodes:
        if node.id == node_id:
            center_node = node
            break

    if not center_node:
        return {"error": "Node not found", "nodes": [], "links": []}

    # Build adjacency map
    adjacency: dict[str, set[str]] = {}
    for edge in graph.edges:
        if edge.source not in adjacency:
            adjacency[edge.source] = set()
        adjacency[edge.source].add(edge.target)
        # Add reverse for undirected traversal
        if edge.target not in adjacency:
            adjacency[edge.target] = set()
        adjacency[edge.target].add(edge.source)

    # BFS to find nodes within depth
    visited = {node_id}
    frontier = {node_id}
    depth = min(depth, 3)  # Cap at 3

    for _ in range(depth):
        next_frontier = set()
        for nid in frontier:
            for neighbor in adjacency.get(nid, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    # Filter nodes and edges
    subgraph_nodes = [n for n in graph.nodes if n.id in visited]
    subgraph_edges = [e for e in graph.edges if e.source in visited and e.target in visited]

    return {
        "center": node_id,
        "depth": depth,
        "nodes": [n.model_dump(mode='json') for n in subgraph_nodes],
        "links": [e.model_dump(mode='json') for e in subgraph_edges],
    }


@router.post("/refresh")
async def refresh_graph():
    """Trigger re-indexing of source files.

    Note: This requires the zettel_db sync to be run externally.
    This endpoint just rebuilds the graph from the current database.
    """
    config = load_config()
    graph = build_graph(config=config)

    return {
        "status": "refreshed",
        "stats": graph.stats.model_dump(),
    }
