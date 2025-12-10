"""Format search results to compact markdown."""

from .retriever import SearchResults


def format_search_results(results: SearchResults) -> str:
    """Format search results as compact markdown.

    Args:
        results: SearchResults object

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    lines.append(f'# SEARCH q="{results.query}"')
    lines.append('')

    # Parameters
    lines.append('## PARAMS')
    lines.append(f'expanded: {str(results.expanded).lower()}')
    lines.append(f'top_k: {results.top_k}')
    lines.append(f'generated_at: {results.generated_at}')
    lines.append('')

    # Results
    lines.append('## RESULTS')

    if not results.results:
        lines.append('No results found.')
        return '\n'.join(lines)

    lines.append('')

    for i, result in enumerate(results.results, 1):
        # Result header
        lines.append(f'### {i}. {result.title}')
        lines.append('')

        # Scores
        lines.append(f'relevance: {result.relevance:.2f}')
        lines.append(f'vec_score: {result.vec_score:.2f}')
        lines.append(f'recency: {result.recency_score:.2f}')
        lines.append(f'centrality: {result.centrality_score:.2f}')
        lines.append('')

        # Metadata
        lines.append(f'path: {result.path}')
        lines.append(f'type: {result.doc_type}')
        lines.append(f'words: {result.word_count}')

        if result.tags:
            lines.append(f'tags: {", ".join(result.tags)}')

        lines.append('')

        # Content
        lines.append('--- CONTENT ---')
        lines.append(result.content.strip())
        lines.append('--- END ---')
        lines.append('')

    return '\n'.join(lines)
