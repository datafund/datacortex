"""Semantic similarity computation using embeddings."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score (0 to 1)
    """
    # Normalize vectors
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b)

    # Compute dot product
    similarity = np.dot(a_norm, b_norm)

    return float(similarity)


def compute_similarity_matrix(embeddings: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    """Compute pairwise similarity matrix for all embeddings.

    Args:
        embeddings: Dict mapping file_id to embedding vector

    Returns:
        Tuple of (file_ids, similarity_matrix)
        - file_ids: Ordered list of file identifiers
        - similarity_matrix: NxN numpy array where matrix[i][j] is similarity between file_ids[i] and file_ids[j]
    """
    if not embeddings:
        return [], np.array([])

    # Sort file_ids for consistent ordering
    file_ids = sorted(embeddings.keys())

    # Stack embeddings into matrix
    embedding_matrix = np.vstack([embeddings[fid] for fid in file_ids])

    # Normalize each embedding
    norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
    normalized_embeddings = embedding_matrix / norms

    # Compute pairwise cosine similarity via matrix multiplication
    # similarity[i][j] = dot(normalized_embeddings[i], normalized_embeddings[j])
    similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)

    return file_ids, similarity_matrix


def find_similar_pairs(
    file_ids: list[str],
    matrix: np.ndarray,
    threshold: float = 0.75
) -> list[tuple[str, str, float]]:
    """Find pairs of documents with similarity above threshold.

    Args:
        file_ids: Ordered list of file identifiers
        matrix: NxN similarity matrix
        threshold: Minimum similarity score (default 0.75)

    Returns:
        List of (file_id1, file_id2, similarity) tuples, sorted by similarity descending
    """
    if len(file_ids) == 0:
        return []

    pairs = []

    # Iterate upper triangle to avoid duplicates
    n = len(file_ids)
    for i in range(n):
        for j in range(i + 1, n):
            similarity = matrix[i][j]

            if similarity >= threshold:
                pairs.append((file_ids[i], file_ids[j], float(similarity)))

    # Sort by similarity descending
    pairs.sort(key=lambda x: -x[2])

    return pairs


def find_most_similar(
    file_id: str,
    file_ids: list[str],
    matrix: np.ndarray,
    top_k: int = 10
) -> list[tuple[str, float]]:
    """Find most similar documents to a given document.

    Args:
        file_id: Target file identifier
        file_ids: Ordered list of all file identifiers
        matrix: NxN similarity matrix
        top_k: Number of similar documents to return

    Returns:
        List of (file_id, similarity) tuples, sorted by similarity descending
        Excludes the target document itself
    """
    if file_id not in file_ids:
        return []

    # Find index of target file
    idx = file_ids.index(file_id)

    # Get similarity scores for this file
    similarities = matrix[idx]

    # Create list of (file_id, similarity) pairs, excluding self
    similar = []
    for i, fid in enumerate(file_ids):
        if i != idx:
            similar.append((fid, float(similarities[i])))

    # Sort by similarity descending and return top_k
    similar.sort(key=lambda x: -x[1])
    return similar[:top_k]
