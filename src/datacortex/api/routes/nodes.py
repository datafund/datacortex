"""Node API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.config import load_config
from ...indexer.graph_builder import build_graph

router = APIRouter()


@router.get("/search")
async def search_nodes(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Maximum results"),
):
    """Search nodes by title."""
    config = load_config()
    graph = build_graph(config=config)

    query_lower = q.lower()
    results = []

    for node in graph.nodes:
        # Match on title or tags
        if query_lower in node.title.lower():
            results.append(node)
        elif any(query_lower in tag.lower() for tag in node.tags):
            results.append(node)

        if len(results) >= limit:
            break

    # Sort by degree (most connected first)
    results.sort(key=lambda n: n.degree, reverse=True)

    return {
        "query": q,
        "count": len(results),
        "nodes": [n.model_dump(mode='json') for n in results],
    }


@router.get("/{node_id}")
async def get_node(node_id: str):
    """Get detailed information about a specific node."""
    config = load_config()
    graph = build_graph(config=config)

    # Find the node
    target_node = None
    for node in graph.nodes:
        if node.id == node_id:
            target_node = node
            break

    if not target_node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Find incoming links (backlinks)
    backlinks = []
    outlinks = []

    for edge in graph.edges:
        if edge.target == node_id:
            backlinks.append({
                "source_id": edge.source,
                "syntax": edge.syntax,
            })
        if edge.source == node_id:
            outlinks.append({
                "target_id": edge.target,
                "target_title": edge.target,  # Will be resolved below
                "syntax": edge.syntax,
                "resolved": edge.resolved,
            })

    # Resolve node titles for links
    node_titles = {n.id: n.title for n in graph.nodes}

    for link in backlinks:
        link["source_title"] = node_titles.get(link["source_id"], link["source_id"])

    for link in outlinks:
        link["target_title"] = node_titles.get(link["target_id"], link["target_id"])

    return {
        "node": target_node.model_dump(mode='json'),
        "backlinks": backlinks,
        "outlinks": outlinks,
        "backlink_count": len(backlinks),
        "outlink_count": len(outlinks),
    }


@router.get("/{node_id}/neighbors")
async def get_neighbors(
    node_id: str,
    direction: str = Query("both", description="Link direction: in, out, both"),
):
    """Get nodes directly connected to this node."""
    config = load_config()
    graph = build_graph(config=config)

    # Find connected node IDs
    neighbor_ids: set[str] = set()

    for edge in graph.edges:
        if direction in ("out", "both") and edge.source == node_id:
            neighbor_ids.add(edge.target)
        if direction in ("in", "both") and edge.target == node_id:
            neighbor_ids.add(edge.source)

    # Get neighbor nodes
    neighbors = [n for n in graph.nodes if n.id in neighbor_ids]
    neighbors.sort(key=lambda n: n.degree, reverse=True)

    return {
        "center": node_id,
        "direction": direction,
        "count": len(neighbors),
        "neighbors": [n.model_dump(mode='json') for n in neighbors],
    }
