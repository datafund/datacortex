"""Format gap detection results as compact TSV/markdown."""

from .detector import GapsResult


def format_gaps(result: GapsResult) -> str:
    """Format gaps result as compact TSV/markdown.

    Args:
        result: GapsResult to format

    Returns:
        Formatted string ready for Claude consumption

    Format:
        # KNOWLEDGE_GAPS count=5 generated=2025-12-10T12:30:00
        ## GAP rank=1 gap_score=0.58
        clusters: 3, 7
        semantic_sim: 0.72
        link_density: 0.02
        cross_links: 2

        ### CLUSTER_3 size=47
        HUBS: Data Tokenization, Swarm Storage, API Design
        TAGS: tokenization(12), data(10), api(8)

        ### CLUSTER_7 size=23
        HUBS: Trading Journal, Position Sizing, Risk Management
        TAGS: trading(8), risk(5), analytics(4)

        SHARED_TAGS: data, analytics
        BOUNDARY_NODES: Market Data Feed
    """
    lines = []

    # Header
    lines.append(f"# KNOWLEDGE_GAPS count={len(result.gaps)} generated={result.generated_at}")
    lines.append(f"# Total clusters analyzed: {result.cluster_count}")
    lines.append("")

    if not result.gaps:
        lines.append("(No knowledge gaps detected above threshold)")
        lines.append("")
        return "\n".join(lines)

    # Format each gap
    for rank, gap in enumerate(result.gaps, start=1):
        lines.append(f"## GAP rank={rank} gap_score={gap.gap_score:.2f}")
        lines.append(f"clusters: {gap.cluster_a}, {gap.cluster_b}")
        lines.append(f"semantic_sim: {gap.semantic_similarity:.2f}")
        lines.append(f"link_density: {gap.link_density:.4f}")
        lines.append(f"cross_links: {gap.cross_links}")
        lines.append("")

        # Cluster A info
        lines.append(f"### CLUSTER_{gap.cluster_a} size={gap.cluster_a_info.size}")

        if gap.cluster_a_info.hub_docs:
            hubs_str = ", ".join(gap.cluster_a_info.hub_docs[:5])
            lines.append(f"HUBS: {hubs_str}")
        else:
            lines.append("HUBS: (none)")

        if gap.cluster_a_info.top_tags:
            tags_str = ", ".join([f"{tag}({count})" for tag, count in gap.cluster_a_info.top_tags])
            lines.append(f"TAGS: {tags_str}")
        else:
            lines.append("TAGS: (none)")

        lines.append("")

        # Cluster B info
        lines.append(f"### CLUSTER_{gap.cluster_b} size={gap.cluster_b_info.size}")

        if gap.cluster_b_info.hub_docs:
            hubs_str = ", ".join(gap.cluster_b_info.hub_docs[:5])
            lines.append(f"HUBS: {hubs_str}")
        else:
            lines.append("HUBS: (none)")

        if gap.cluster_b_info.top_tags:
            tags_str = ", ".join([f"{tag}({count})" for tag, count in gap.cluster_b_info.top_tags])
            lines.append(f"TAGS: {tags_str}")
        else:
            lines.append("TAGS: (none)")

        lines.append("")

        # Shared context
        if gap.shared_tags:
            lines.append(f"SHARED_TAGS: {', '.join(gap.shared_tags)}")
        else:
            lines.append("SHARED_TAGS: (none)")

        if gap.boundary_nodes:
            # Limit to first 10 boundary nodes to keep output compact
            boundary_str = ", ".join(gap.boundary_nodes[:10])
            if len(gap.boundary_nodes) > 10:
                boundary_str += f" (and {len(gap.boundary_nodes) - 10} more)"
            lines.append(f"BOUNDARY_NODES: {boundary_str}")
        else:
            lines.append("BOUNDARY_NODES: (none)")

        lines.append("")

    return "\n".join(lines)
