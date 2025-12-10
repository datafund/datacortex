"""Format digest results as compact TSV/markdown for Claude."""

from .generator import DigestResult


def format_digest(result: DigestResult) -> str:
    """Format digest result as compact TSV/markdown.

    Args:
        result: DigestResult to format

    Returns:
        Formatted string ready for Claude consumption
    """
    lines = []

    # Header
    lines.append(f"# DATACORTEX DAILY DIGEST")
    lines.append(f"# Generated: {result.generated_at}")
    lines.append("")

    # Similar pairs section
    lines.append(f"# SIMILAR_PAIRS threshold={result.threshold} count={len(result.similar_pairs)}")
    lines.append("# format: doc_a | doc_b | similarity | recency | centrality | score")

    if result.similar_pairs:
        for pair in result.similar_pairs:
            line = (
                f"{pair.doc_a} | {pair.doc_b} | "
                f"{pair.similarity:.2f} | {pair.recency_score:.2f} | "
                f"{pair.centrality_avg:.2f} | {pair.final_score:.2f}"
            )
            lines.append(line)
    else:
        lines.append("(none)")

    lines.append("")

    # Orphans section
    lines.append(f"# ORPHANS count={len(result.orphans)}")
    lines.append("# format: title | words | created_at | path")

    if result.orphans:
        for orphan in result.orphans:
            line = (
                f"{orphan.title} | {orphan.word_count}w | "
                f"{orphan.created_at[:10] if orphan.created_at else 'unknown'} | "
                f"{orphan.path}"
            )
            lines.append(line)
    else:
        lines.append("(none)")

    lines.append("")

    return "\n".join(lines)
