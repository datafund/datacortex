"""Generate daily digest of link suggestions based on semantic similarity."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from ..ai.embeddings import compute_embeddings_for_space
from ..ai.similarity import compute_similarity_matrix, find_similar_pairs
from ..core.database import get_connection, space_exists


@dataclass
class SimilarPair:
    """A pair of documents that should be linked."""
    doc_a: str  # title
    doc_b: str  # title
    path_a: str
    path_b: str
    similarity: float
    recency_score: float
    centrality_avg: float
    final_score: float


@dataclass
class OrphanDoc:
    """A document with no incoming links."""
    title: str
    path: str
    word_count: int
    created_at: str


@dataclass
class DigestResult:
    """Complete digest with suggestions."""
    similar_pairs: list[SimilarPair]
    orphans: list[OrphanDoc]
    threshold: float
    generated_at: str


def get_existing_links(conn) -> set[tuple[str, str]]:
    """Return set of (source_id, target_id) for all resolved links.

    Args:
        conn: SQLite connection to space database

    Returns:
        Set of (source_id, target_id) tuples
    """
    cursor = conn.execute("""
        SELECT source_id, target_id
        FROM links
        WHERE resolved = 1 AND target_id IS NOT NULL
    """)

    links = set()
    for row in cursor:
        links.add((row['source_id'], row['target_id']))

    return links


def get_recency_score(updated_at: str) -> float:
    """Score from 0-1, where 1 = updated today, decays over 30 days.

    Args:
        updated_at: ISO format datetime string

    Returns:
        Score from 0 to 1
    """
    try:
        updated = datetime.fromisoformat(updated_at)
    except (ValueError, TypeError):
        return 0.0

    now = datetime.now()
    days_old = (now - updated).total_seconds() / 86400  # Convert to days

    # Decay over 30 days
    if days_old <= 0:
        return 1.0
    elif days_old >= 30:
        return 0.0
    else:
        return 1.0 - (days_old / 30.0)


def get_orphans(conn, min_word_count: int = 50) -> list[OrphanDoc]:
    """Documents with no incoming links (in_degree = 0).

    Args:
        conn: SQLite connection to space database
        min_word_count: Minimum word count to consider

    Returns:
        List of OrphanDoc objects sorted by word count descending
    """
    cursor = conn.execute("""
        SELECT f.title, f.path, f.word_count, f.created_at
        FROM files f
        WHERE f.word_count >= ?
          AND f.is_stub = 0
          AND NOT EXISTS (
              SELECT 1 FROM links l
              WHERE l.target_id = f.id AND l.resolved = 1
          )
        ORDER BY f.word_count DESC
        LIMIT 50
    """, (min_word_count,))

    orphans = []
    for row in cursor:
        orphans.append(OrphanDoc(
            title=row['title'] or 'Untitled',
            path=row['path'],
            word_count=row['word_count'] or 0,
            created_at=row['created_at'] or '',
        ))

    return orphans


def get_file_metadata(conn) -> dict[str, dict]:
    """Get metadata for all files.

    Returns:
        Dict mapping file_id to metadata dict with title, path, updated_at, centrality
    """
    cursor = conn.execute("""
        SELECT id, title, path, updated_at
        FROM files
        WHERE is_stub = 0
    """)

    metadata = {}
    for row in cursor:
        metadata[row['id']] = {
            'title': row['title'] or row['id'],
            'path': row['path'],
            'updated_at': row['updated_at'] or '',
        }

    return metadata


def get_centrality_scores(conn) -> dict[str, float]:
    """Get centrality scores if available (from graph metrics).

    For now, use degree as proxy for centrality.

    Returns:
        Dict mapping file_id to centrality score (0-1)
    """
    # Count in-degree and out-degree for each file
    cursor = conn.execute("""
        SELECT source_id as file_id, COUNT(*) as out_degree
        FROM links
        WHERE resolved = 1
        GROUP BY source_id
    """)

    degrees = {}
    for row in cursor:
        degrees[row['file_id']] = row['out_degree']

    cursor = conn.execute("""
        SELECT target_id as file_id, COUNT(*) as in_degree
        FROM links
        WHERE resolved = 1 AND target_id IS NOT NULL
        GROUP BY target_id
    """)

    for row in cursor:
        file_id = row['file_id']
        degrees[file_id] = degrees.get(file_id, 0) + row['in_degree']

    # Normalize to 0-1 range
    if not degrees:
        return {}

    max_degree = max(degrees.values())
    if max_degree == 0:
        return {fid: 0.0 for fid in degrees}

    return {fid: deg / max_degree for fid, deg in degrees.items()}


def generate_digest(
    spaces: list[str],
    threshold: float = 0.75,
    top_n: int = 20,
    min_orphan_words: int = 50
) -> DigestResult:
    """Generate daily digest of link suggestions.

    Args:
        spaces: List of space names to include
        threshold: Minimum similarity threshold (default 0.75)
        top_n: Number of top suggestions to return (default 20)
        min_orphan_words: Minimum word count for orphans (default 50)

    Returns:
        DigestResult with similar pairs and orphans
    """
    all_pairs: list[SimilarPair] = []
    all_orphans: list[OrphanDoc] = []

    for space in spaces:
        if not space_exists(space):
            continue

        print(f"Processing space: {space}")

        # Compute/load embeddings
        embeddings = compute_embeddings_for_space(space, force=False)

        if not embeddings:
            print(f"  No embeddings found for {space}")
            continue

        # Compute similarity matrix
        file_ids, matrix = compute_similarity_matrix(embeddings)

        # Find similar pairs above threshold
        similar = find_similar_pairs(file_ids, matrix, threshold=threshold)

        print(f"  Found {len(similar)} similar pairs above threshold {threshold}")

        # Get metadata and existing links
        conn = get_connection(space)
        metadata = get_file_metadata(conn)
        existing_links = get_existing_links(conn)
        centrality = get_centrality_scores(conn)
        orphans = get_orphans(conn, min_word_count=min_orphan_words)
        conn.close()

        # Filter out already-linked pairs and score remaining
        for file_a, file_b, similarity in similar:
            # Skip if already linked in either direction
            if (file_a, file_b) in existing_links or (file_b, file_a) in existing_links:
                continue

            # Skip if metadata missing
            if file_a not in metadata or file_b not in metadata:
                continue

            meta_a = metadata[file_a]
            meta_b = metadata[file_b]

            # Compute recency scores
            recency_a = get_recency_score(meta_a['updated_at'])
            recency_b = get_recency_score(meta_b['updated_at'])
            recency_avg = (recency_a + recency_b) / 2.0

            # Get centrality scores
            centrality_a = centrality.get(file_a, 0.0)
            centrality_b = centrality.get(file_b, 0.0)
            centrality_avg = (centrality_a + centrality_b) / 2.0

            # Compute final score: similarity * 0.5 + recency * 0.3 + centrality * 0.2
            final_score = (
                similarity * 0.5 +
                recency_avg * 0.3 +
                centrality_avg * 0.2
            )

            pair = SimilarPair(
                doc_a=meta_a['title'],
                doc_b=meta_b['title'],
                path_a=meta_a['path'],
                path_b=meta_b['path'],
                similarity=similarity,
                recency_score=recency_avg,
                centrality_avg=centrality_avg,
                final_score=final_score,
            )
            all_pairs.append(pair)

        all_orphans.extend(orphans)

    # Sort by final score and take top N
    all_pairs.sort(key=lambda p: -p.final_score)
    all_pairs = all_pairs[:top_n]

    return DigestResult(
        similar_pairs=all_pairs,
        orphans=all_orphans[:top_n],  # Limit orphans too
        threshold=threshold,
        generated_at=datetime.now().isoformat(),
    )
