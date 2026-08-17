"""Re-ranking logic for search results."""

from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from ..ai.similarity import cosine_similarity


def get_recency_score(updated_at: str) -> float:
    """Score 0-1, decays over 30 days from today.

    Args:
        updated_at: ISO timestamp string

    Returns:
        Recency score between 0 and 1
    """
    try:
        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        # If parsing fails, assume old document
        return 0.0

    now = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
    age_days = (now - updated).days

    # Linear decay over 30 days
    if age_days <= 0:
        return 1.0
    elif age_days >= 30:
        return 0.0
    else:
        return 1.0 - (age_days / 30.0)


def get_centrality_score(degree: int, max_degree: int) -> float:
    """Normalize degree to 0-1 range.

    Args:
        degree: Node degree (number of connections)
        max_degree: Maximum degree in the graph

    Returns:
        Centrality score between 0 and 1
    """
    if max_degree == 0:
        return 0.0
    return min(1.0, degree / max_degree)


def rerank_results(
    candidates: list[str],
    original_candidates: set[str],
    query_embedding: np.ndarray,
    embeddings: dict[str, np.ndarray],
    metadata: dict[str, dict],
) -> list[tuple[str, float, dict]]:
    """Re-rank candidates by weighted score.

    Re-ranks candidates using a weighted combination of:
    - vec_score (60%): cosine similarity to query
    - recency (20%): how recently updated
    - centrality (20%): graph connectivity
    - direct_boost (1.2x): if from original vector search

    Args:
        candidates: List of file_ids to rank
        original_candidates: Set of file_ids from original vector search
        query_embedding: Query embedding vector
        embeddings: Dict mapping file_id to embedding vector
        metadata: Dict mapping file_id to metadata dict with 'updated_at', 'degree', 'max_degree'

    Returns:
        List of (file_id, final_score, scores_dict) tuples, sorted by final_score descending
        scores_dict contains: vec_score, recency_score, centrality_score, direct_boost, final_score
    """
    results = []

    for file_id in candidates:
        # Skip if no embedding
        if file_id not in embeddings:
            continue

        # Get metadata
        meta = metadata.get(file_id, {})

        # Vector similarity score
        vec_score = cosine_similarity(query_embedding, embeddings[file_id])

        # Recency score
        updated_at = meta.get('updated_at', '')
        recency_score = get_recency_score(updated_at)

        # Centrality score
        degree = meta.get('degree', 0)
        max_degree = meta.get('max_degree', 1)
        centrality_score = get_centrality_score(degree, max_degree)

        # Direct match boost (1.2x for original vector search results)
        direct_boost = 1.2 if file_id in original_candidates else 1.0

        # Weighted final score
        weighted_score = (
            vec_score * 0.6 +
            recency_score * 0.2 +
            centrality_score * 0.2
        )
        final_score = weighted_score * direct_boost

        scores = {
            'vec_score': vec_score,
            'recency_score': recency_score,
            'centrality_score': centrality_score,
            'direct_boost': direct_boost,
            'final_score': final_score,
        }

        results.append((file_id, final_score, scores))

    # Sort by final score descending
    results.sort(key=lambda x: -x[1])

    return results
