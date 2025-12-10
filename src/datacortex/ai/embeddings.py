"""Embedding generation using sentence-transformers."""

import hashlib
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from ..core.database import get_connection, get_available_spaces


# Global model singleton
_model: Optional[SentenceTransformer] = None
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


def get_model() -> SentenceTransformer:
    """Lazy load and return the sentence transformer model singleton.

    Returns:
        SentenceTransformer model instance
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as numpy array
    """
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def embed_documents(docs: list[dict]) -> dict[str, np.ndarray]:
    """Batch embed multiple documents.

    Each document should have 'id', 'title', and 'content' keys.
    Embeds title + first 500 chars of content.

    Args:
        docs: List of document dicts with 'id', 'title', 'content'

    Returns:
        Dict mapping document id to embedding vector
    """
    model = get_model()

    # Prepare texts for embedding
    texts = []
    doc_ids = []
    for doc in docs:
        title = doc.get('title', '')
        content = doc.get('content', '')

        # Combine title + first 500 chars of content
        if content:
            text = f"{title}\n\n{content[:500]}"
        else:
            text = title

        texts.append(text)
        doc_ids.append(doc['id'])

    # Batch encode with reasonable batch size
    embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32, show_progress_bar=True)

    # Return as dict
    return {doc_id: embedding for doc_id, embedding in zip(doc_ids, embeddings)}


def compute_content_hash(title: str, content: str) -> str:
    """Compute MD5 hash of document content for change detection.

    Args:
        title: Document title
        content: Document content

    Returns:
        MD5 hash string
    """
    # Combine title + first 500 chars (same as what we embed)
    text = f"{title}\n\n{content[:500] if content else ''}"
    return hashlib.md5(text.encode()).hexdigest()


def compute_embeddings_for_space(space: str, force: bool = False) -> dict[str, np.ndarray]:
    """Compute embeddings for all documents in a space.

    Uses caching - only recomputes if document changed or force=True.

    Args:
        space: Space name (personal, datafund, datacore)
        force: If True, recompute all embeddings regardless of cache

    Returns:
        Dict mapping file_id to embedding vector
    """
    from .cache import (
        init_embeddings_table,
        get_cached_embedding,
        save_embedding,
        get_stale_embeddings,
    )

    conn = get_connection(space)
    init_embeddings_table(conn)

    # Load all documents from files table
    cursor = conn.execute("""
        SELECT id, title, content
        FROM files
        ORDER BY id
    """)

    docs = []
    for row in cursor:
        docs.append({
            'id': row['id'],
            'title': row['title'] or '',
            'content': row['content'] or '',
        })

    if not docs:
        return {}

    embeddings = {}

    if force:
        # Recompute all
        print(f"Computing embeddings for {len(docs)} documents (forced)...")
        embeddings = embed_documents(docs)

        # Save all to cache
        for doc in docs:
            content_hash = compute_content_hash(doc['title'], doc['content'])
            save_embedding(conn, doc['id'], embeddings[doc['id']], MODEL_NAME, content_hash)
    else:
        # Check which are stale
        stale_ids = get_stale_embeddings(conn, docs)

        # Load cached embeddings for non-stale docs
        for doc in docs:
            if doc['id'] not in stale_ids:
                cached = get_cached_embedding(conn, doc['id'])
                if cached is not None:
                    embeddings[doc['id']] = cached

        # Compute only stale embeddings
        if stale_ids:
            print(f"Computing embeddings for {len(stale_ids)} new/changed documents...")
            stale_docs = [doc for doc in docs if doc['id'] in stale_ids]
            new_embeddings = embed_documents(stale_docs)

            # Save to cache and add to results
            for doc in stale_docs:
                content_hash = compute_content_hash(doc['title'], doc['content'])
                save_embedding(conn, doc['id'], new_embeddings[doc['id']], MODEL_NAME, content_hash)
                embeddings[doc['id']] = new_embeddings[doc['id']]
        else:
            print("All embeddings up to date (using cache)")

    conn.close()
    return embeddings
