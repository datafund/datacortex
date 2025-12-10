"""Format insights to compact TSV/markdown."""

from .analyzer import InsightsResult, ClusterAnalysis


def format_insights(result: InsightsResult, include_samples: bool = True) -> str:
    """Format cluster insights to compact TSV/markdown.

    Args:
        result: InsightsResult from analyzer
        include_samples: Whether to include content samples

    Returns:
        Formatted string with cluster analysis
    """
    lines = []

    # Header
    lines.append(f"# CLUSTER_INSIGHTS clusters={result.total_clusters} total_docs={result.total_docs} generated={result.generated_at}")
    lines.append("")

    # Each cluster
    for cluster in result.clusters:
        lines.append(f"## CLUSTER id={cluster.cluster_id} size={cluster.size}")
        lines.append("")

        # Stats
        lines.append("### STATS")
        lines.append(f"avg_words: {cluster.stats['avg_words']}")
        lines.append(f"total_words: {cluster.stats['total_words']}")
        lines.append(f"avg_centrality: {cluster.stats['avg_centrality']}")
        lines.append(f"density: {cluster.stats['density']}")
        lines.append("")

        # Hubs
        lines.append("### HUBS")
        for hub in cluster.hubs:
            tags = ','.join(hub['tags'][:3]) if hub['tags'] else 'none'
            lines.append(f"{hub['title']} | {hub['centrality']:.3f} | {hub['word_count']}w | {tags}")
        lines.append("")

        # Tags
        lines.append("### TAGS")
        for tag, count in cluster.tag_freq:
            lines.append(f"{tag}: {count}")
        lines.append("")

        # Connections
        if cluster.connections:
            lines.append("### CONNECTIONS")
            for conn in cluster.connections:
                lines.append(f"cluster_{conn['cluster_id']}: {conn['link_count']} links")
            lines.append("")

        # Samples
        if include_samples and cluster.samples:
            lines.append("### SAMPLES")
            for sample in cluster.samples:
                lines.append(f"#### {sample['title']} ({sample['word_count']}w)")
                lines.append(sample['excerpt'])
                lines.append("")

    return '\n'.join(lines)


def format_cluster_summary(result: InsightsResult) -> str:
    """Format a brief summary of all clusters.

    Args:
        result: InsightsResult from analyzer

    Returns:
        Brief summary with cluster sizes and top tags
    """
    lines = []

    lines.append(f"# CLUSTER SUMMARY")
    lines.append(f"Total clusters: {result.total_clusters}")
    lines.append(f"Total documents: {result.total_docs}")
    lines.append(f"Generated: {result.generated_at}")
    lines.append("")

    # Table header
    lines.append("| ID | Size | Top Tags | Top Hub |")
    lines.append("|----|------|----------|---------|")

    for cluster in result.clusters:
        top_tags = ', '.join([tag for tag, _ in cluster.tag_freq[:3]]) if cluster.tag_freq else 'none'
        top_hub = cluster.hubs[0]['title'] if cluster.hubs else 'none'

        lines.append(f"| {cluster.cluster_id} | {cluster.size} | {top_tags} | {top_hub} |")

    return '\n'.join(lines)
