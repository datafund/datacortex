"""SQLite cache for document embeddings."""

import hashlib
import sqlite3
from datetime import datetime
from typing import Optional

import numpy as np


def init_embeddings_table(conn: sqlite3.Connection) -> None:
    """Create embeddings table if it doesn't exist.

    Args:
        conn: SQLite connection to space database
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            file_id TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            model TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()


def get_cached_embedding(conn: sqlite3.Connection, file_id: str) -> Optional[np.ndarray]:
    """Retrieve cached embedding for a file.

    Args:
        conn: SQLite connection to space database
        file_id: File identifier

    Returns:
        Embedding vector as numpy array, or None if not cached
    """
    cursor = conn.execute("""
        SELECT embedding FROM embeddings WHERE file_id = ?
    """, (file_id,))

    row = cursor.fetchone()
    if row is None:
        return None

    # Deserialize from BLOB
    embedding_bytes = row[0]
    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
    return embedding


def save_embedding(
    conn: sqlite3.Connection,
    file_id: str,
    embedding: np.ndarray,
    model: str,
    content_hash: str
) -> None:
    """Save or update embedding in cache.

    Args:
        conn: SQLite connection to space database
        file_id: File identifier
        embedding: Embedding vector
        model: Model name used
        content_hash: MD5 hash of content for change detection
    """
    # Serialize embedding to bytes
    embedding_bytes = embedding.astype(np.float32).tobytes()
    created_at = datetime.now().isoformat()

    conn.execute("""
        INSERT OR REPLACE INTO embeddings (file_id, embedding, model, content_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (file_id, embedding_bytes, model, content_hash, created_at))

    conn.commit()


def get_stale_embeddings(conn: sqlite3.Connection, files: list[dict]) -> list[str]:
    """Find file_ids that need embedding recomputation.

    Returns IDs where:
    - No cached embedding exists
    - Content hash changed (content was modified)

    Args:
        conn: SQLite connection to space database
        files: List of file dicts with 'id', 'title', 'content'

    Returns:
        List of file_ids needing recomputation
    """
    from .embeddings import compute_content_hash

    stale_ids = []

    for file in files:
        file_id = file['id']
        title = file.get('title', '')
        content = file.get('content', '')

        # Compute current content hash
        current_hash = compute_content_hash(title, content)

        # Check cached embedding
        cursor = conn.execute("""
            SELECT content_hash FROM embeddings WHERE file_id = ?
        """, (file_id,))

        row = cursor.fetchone()
        if row is None:
            # No cache entry - needs embedding
            stale_ids.append(file_id)
        elif row[0] != current_hash:
            # Content changed - needs recompute
            stale_ids.append(file_id)

    return stale_ids


def load_all_embeddings(conn: sqlite3.Connection) -> dict[str, np.ndarray]:
    """Load all cached embeddings for a space.

    Args:
        conn: SQLite connection to space database

    Returns:
        Dict mapping file_id to embedding vector
    """
    cursor = conn.execute("""
        SELECT file_id, embedding FROM embeddings
    """)

    embeddings = {}
    for row in cursor:
        file_id = row[0]
        embedding_bytes = row[1]
        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
        embeddings[file_id] = embedding

    return embeddings
