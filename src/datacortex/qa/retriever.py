"""RAG retrieval pipeline for question answering."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ..ai.cache import get_cached_embedding, init_embeddings_table
from ..ai.embeddings import embed_text
from ..ai.similarity import cosine_similarity
from ..core.database import get_connection
from .ranker import rerank_results


@dataclass
class SearchResult:
    """Single search result with metadata and content."""
    file_id: str
    title: str
    path: str
    doc_type: str
    word_count: int
    tags: list[str]
    relevance: float  # final score
    vec_score: float  # cosine similarity
    recency_score: float
    centrality_score: float
    content: str  # full content


@dataclass
class ReasoningHop:
    """Single hop in multi-hop reasoning path (DIP-0016)."""
    hop: int
    query: str
    results_count: int
    selected_ids: list[str]


@dataclass
class SearchResults:
    """Collection of search results with metadata."""
    query: str
    results: list[SearchResult]
    expanded: bool
    top_k: int
    generated_at: str
    # DIP-0016: Multi-hop reasoning path
    reasoning_path: list[ReasoningHop] = None


def load_embeddings_for_space(space: str) -> tuple[dict[str, np.ndarray], dict[str, dict]]:
    """Load all cached embeddings and metadata for a space.

    Args:
        space: Space name

    Returns:
        Tuple of (embeddings_dict, metadata_dict)
        - embeddings_dict: file_id -> embedding vector
        - metadata_dict: file_id -> {title, path, type, updated_at, degree, tags, word_count}
    """
    conn = get_connection(space)
    init_embeddings_table(conn)

    embeddings = {}
    metadata = {}

    # Load embeddings from cache
    cursor = conn.execute("""
        SELECT file_id, embedding
        FROM embeddings
    """)

    for row in cursor:
        embeddings[row['file_id']] = np.frombuffer(row['embedding'], dtype=np.float32)

    # Load metadata from files
    cursor = conn.execute("""
        SELECT id, title, path, type, updated_at, word_count
        FROM files
    """)

    files_meta = {}
    for row in cursor:
        files_meta[row['id']] = {
            'title': row['title'] or row['id'],
            'path': row['path'],
            'type': row['type'],
            'updated_at': row['updated_at'],
            'word_count': row['word_count'] or 0,
        }

    # Load tags
    cursor = conn.execute("""
        SELECT file_id, GROUP_CONCAT(normalized_tag, ',') as tags
        FROM tags
        GROUP BY file_id
    """)

    tags_map = {}
    for row in cursor:
        if row['tags']:
            tags_map[row['file_id']] = [t for t in row['tags'].split(',') if t]

    # Load degrees (count incoming + outgoing links)
    cursor = conn.execute("""
        SELECT source_id as file_id, COUNT(*) as degree
        FROM links
        WHERE resolved = 1
        GROUP BY source_id
    """)

    degree_out = {}
    for row in cursor:
        degree_out[row['file_id']] = row['degree']

    cursor = conn.execute("""
        SELECT target_id as file_id, COUNT(*) as degree
        FROM links
        WHERE resolved = 1 AND target_id IS NOT NULL
        GROUP BY target_id
    """)

    degree_in = {}
    for row in cursor:
        degree_in[row['file_id']] = row['degree']

    # Combine metadata
    max_degree = 1
    for file_id in files_meta:
        degree = degree_out.get(file_id, 0) + degree_in.get(file_id, 0)
        max_degree = max(max_degree, degree)

        metadata[file_id] = {
            **files_meta[file_id],
            'degree': degree,
            'max_degree': max_degree,  # Will update after we know max
            'tags': tags_map.get(file_id, []),
        }

    # Update max_degree for all
    for file_id in metadata:
        metadata[file_id]['max_degree'] = max_degree

    conn.close()

    return embeddings, metadata


def expand_with_neighbors(
    candidates: list[str],
    space: str,
    depth: int = 1
) -> set[str]:
    """Add 1-hop neighbors to candidate set.

    Args:
        candidates: Initial candidate file_ids
        space: Space name
        depth: Expansion depth (default 1)

    Returns:
        Expanded set of file_ids
    """
    conn = get_connection(space)

    expanded = set(candidates)

    # Get outgoing neighbors
    placeholders = ','.join('?' * len(candidates))
    cursor = conn.execute(f"""
        SELECT DISTINCT target_id
        FROM links
        WHERE source_id IN ({placeholders})
          AND resolved = 1
          AND target_id IS NOT NULL
    """, candidates)

    for row in cursor:
        expanded.add(row['target_id'])

    # Get incoming neighbors
    cursor = conn.execute(f"""
        SELECT DISTINCT source_id
        FROM links
        WHERE target_id IN ({placeholders})
          AND resolved = 1
    """, candidates)

    for row in cursor:
        expanded.add(row['source_id'])

    conn.close()

    return expanded


def load_full_content(space: str, file_ids: list[str]) -> dict[str, str]:
    """Load full content for multiple documents.

    Args:
        space: Space name
        file_ids: List of file IDs to load

    Returns:
        Dict mapping file_id to content string
    """
    if not file_ids:
        return {}

    conn = get_connection(space)

    placeholders = ','.join('?' * len(file_ids))
    cursor = conn.execute(f"""
        SELECT id, content
        FROM files
        WHERE id IN ({placeholders})
    """, file_ids)

    content_map = {}
    for row in cursor:
        content_map[row['id']] = row['content'] or ''

    conn.close()

    return content_map


def search(
    query: str,
    spaces: list[str],
    top_k: int = 5,
    expand: bool = True,
    max_hops: int = 1,
    track_reasoning: bool = False
) -> SearchResults:
    """RAG retrieval pipeline with optional multi-hop reasoning (DIP-0016).

    Pipeline:
    1. Embed query using same model as corpus
    2. Load all embeddings from cache
    3. Vector search - find top 10 candidates by cosine similarity
    4. Graph expansion (if enabled) - add N-hop neighbors (max_hops)
    5. Re-rank all candidates:
       - vec_score * 0.6 + recency * 0.2 + centrality * 0.2
       - Direct match boost: 1.2x for original candidates
    6. Take top_k results
    7. Load full content for each result

    Args:
        query: Search query string
        spaces: List of space names to search
        top_k: Number of results to return (default 5)
        expand: Whether to expand with graph neighbors (default True)
        max_hops: Maximum graph expansion depth (default 1, DIP-0016)
        track_reasoning: Whether to track reasoning path (default False, DIP-0016)

    Returns:
        SearchResults object with ranked results and optional reasoning path
    """
    # Step 1: Embed query
    query_embedding = embed_text(query)

    # Step 2: Load embeddings and metadata from all spaces
    all_embeddings = {}
    all_metadata = {}

    for space in spaces:
        embeddings, metadata = load_embeddings_for_space(space)
        all_embeddings.update(embeddings)
        all_metadata.update(metadata)

    # DIP-0016: Track reasoning path
    reasoning_path = [] if track_reasoning else None

    if not all_embeddings:
        return SearchResults(
            query=query,
            results=[],
            expanded=expand,
            top_k=top_k,
            generated_at=datetime.now().isoformat(),
            reasoning_path=reasoning_path
        )

    # Step 3: Vector search - find top 10 candidates by cosine similarity
    candidates = []
    for file_id, embedding in all_embeddings.items():
        similarity = cosine_similarity(query_embedding, embedding)
        candidates.append((file_id, similarity))

    candidates.sort(key=lambda x: -x[1])
    top_10_candidates = [c[0] for c in candidates[:10]]
    original_candidates = set(top_10_candidates)

    # DIP-0016: Record first hop
    if track_reasoning:
        reasoning_path.append(ReasoningHop(
            hop=1,
            query=query,
            results_count=len(candidates),
            selected_ids=top_10_candidates[:5]  # Top 5 for path
        ))

    # Step 4: Graph expansion (if enabled) - DIP-0016: multi-hop support
    expanded_candidates = []
    if expand:
        # For each space, expand within that space
        space_candidates = {}
        for file_id in top_10_candidates:
            meta = all_metadata.get(file_id, {})
            # Determine space from path - match both relative and absolute
            path = meta.get('path', '')
            if '0-personal/' in path or '/0-personal/' in path:
                space_key = 'personal'
            elif '1-datafund/' in path or '/1-datafund/' in path:
                space_key = 'datafund'
            elif '2-datacore/' in path or '/2-datacore/' in path:
                space_key = 'datacore'
            else:
                # Try to infer from spaces list
                space_key = spaces[0] if spaces else 'personal'

            if space_key not in space_candidates:
                space_candidates[space_key] = []
            space_candidates[space_key].append(file_id)

        # DIP-0016: Multi-hop expansion
        expanded_set = set(top_10_candidates)
        current_frontier = list(top_10_candidates)

        for hop_num in range(max_hops):
            new_neighbors = set()
            for space_key, space_cands in space_candidates.items():
                if space_key in spaces:
                    # Get neighbors of current frontier within this space
                    frontier_in_space = [fid for fid in current_frontier
                                         if fid in space_cands or fid in expanded_set]
                    if frontier_in_space:
                        neighbors = expand_with_neighbors(frontier_in_space, space_key)
                        new_neighbors.update(neighbors - expanded_set)

            if not new_neighbors:
                break  # No more expansion possible

            expanded_set.update(new_neighbors)
            current_frontier = list(new_neighbors)

            # DIP-0016: Record hop in reasoning path
            if track_reasoning:
                reasoning_path.append(ReasoningHop(
                    hop=hop_num + 2,  # Hop 2, 3, etc.
                    query=f"graph expansion hop {hop_num + 1}",
                    results_count=len(new_neighbors),
                    selected_ids=list(new_neighbors)[:5]
                ))

        expanded_candidates = list(expanded_set)
    else:
        expanded_candidates = top_10_candidates

    # Step 5: Re-rank all candidates
    ranked = rerank_results(
        candidates=expanded_candidates,
        original_candidates=original_candidates,
        query_embedding=query_embedding,
        embeddings=all_embeddings,
        metadata=all_metadata,
    )

    # Step 6: Take top_k results
    top_results = ranked[:top_k]

    # Step 7: Load full content
    # Group by space - detect from path patterns
    space_file_ids = {}
    for file_id, _, _ in top_results:
        meta = all_metadata.get(file_id, {})
        path = meta.get('path', '')
        # Match both relative and absolute paths
        if '0-personal/' in path or '/0-personal/' in path:
            space_key = 'personal'
        elif '1-datafund/' in path or '/1-datafund/' in path:
            space_key = 'datafund'
        elif '2-datacore/' in path or '/2-datacore/' in path:
            space_key = 'datacore'
        else:
            space_key = spaces[0] if spaces else 'personal'

        if space_key not in space_file_ids:
            space_file_ids[space_key] = []
        space_file_ids[space_key].append(file_id)

    all_content = {}
    for space_key, file_ids in space_file_ids.items():
        if space_key in spaces:
            all_content.update(load_full_content(space_key, file_ids))

    # Build search results
    results = []
    for file_id, final_score, scores in top_results:
        meta = all_metadata.get(file_id, {})
        content = all_content.get(file_id, '')

        result = SearchResult(
            file_id=file_id,
            title=meta.get('title', file_id),
            path=meta.get('path', ''),
            doc_type=meta.get('type', 'unknown'),
            word_count=meta.get('word_count', 0),
            tags=meta.get('tags', []),
            relevance=scores['final_score'],
            vec_score=scores['vec_score'],
            recency_score=scores['recency_score'],
            centrality_score=scores['centrality_score'],
            content=content,
        )
        results.append(result)

    return SearchResults(
        query=query,
        results=results,
        expanded=expand,
        top_k=top_k,
        generated_at=datetime.now().isoformat(),
        reasoning_path=reasoning_path  # DIP-0016
    )
