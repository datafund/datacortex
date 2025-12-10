#!/usr/bin/env python3
"""Quick test script for embedding infrastructure."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from datacortex.ai.embeddings import embed_text, embed_documents, compute_content_hash
from datacortex.ai.similarity import cosine_similarity, compute_similarity_matrix, find_similar_pairs

def test_basic_embedding():
    """Test basic text embedding."""
    print("Testing basic embedding...")

    text = "This is a test document about machine learning."
    embedding = embed_text(text)

    print(f"  Text: {text}")
    print(f"  Embedding shape: {embedding.shape}")
    print(f"  Embedding dtype: {embedding.dtype}")
    print(f"  First 5 values: {embedding[:5]}")
    print()

def test_batch_embedding():
    """Test batch document embedding."""
    print("Testing batch embedding...")

    docs = [
        {"id": "doc1", "title": "Machine Learning", "content": "Machine learning is a subset of artificial intelligence."},
        {"id": "doc2", "title": "Deep Learning", "content": "Deep learning uses neural networks with many layers."},
        {"id": "doc3", "title": "Cooking", "content": "Cooking pasta requires boiling water and salt."},
    ]

    embeddings = embed_documents(docs)

    print(f"  Embedded {len(embeddings)} documents")
    for doc_id, emb in embeddings.items():
        print(f"    {doc_id}: shape={emb.shape}")
    print()

def test_similarity():
    """Test similarity computation."""
    print("Testing similarity computation...")

    docs = [
        {"id": "doc1", "title": "Machine Learning", "content": "Machine learning is a subset of artificial intelligence."},
        {"id": "doc2", "title": "Deep Learning", "content": "Deep learning uses neural networks with many layers."},
        {"id": "doc3", "title": "Cooking", "content": "Cooking pasta requires boiling water and salt."},
    ]

    embeddings = embed_documents(docs)

    # Test pairwise similarity
    sim_ml_dl = cosine_similarity(embeddings["doc1"], embeddings["doc2"])
    sim_ml_cook = cosine_similarity(embeddings["doc1"], embeddings["doc3"])

    print(f"  Similarity (ML vs DL): {sim_ml_dl:.4f}")
    print(f"  Similarity (ML vs Cooking): {sim_ml_cook:.4f}")
    print(f"  Expected: ML-DL should be higher than ML-Cooking")
    print()

def test_similarity_matrix():
    """Test similarity matrix computation."""
    print("Testing similarity matrix...")

    docs = [
        {"id": "doc1", "title": "Machine Learning", "content": "Machine learning is a subset of artificial intelligence."},
        {"id": "doc2", "title": "Deep Learning", "content": "Deep learning uses neural networks with many layers."},
        {"id": "doc3", "title": "Cooking", "content": "Cooking pasta requires boiling water and salt."},
    ]

    embeddings = embed_documents(docs)
    file_ids, matrix = compute_similarity_matrix(embeddings)

    print(f"  Matrix shape: {matrix.shape}")
    print(f"  File IDs: {file_ids}")
    print(f"  Matrix:\n{matrix}")
    print()

    # Find similar pairs
    pairs = find_similar_pairs(file_ids, matrix, threshold=0.5)
    print(f"  Similar pairs (threshold=0.5): {len(pairs)}")
    for fid1, fid2, sim in pairs:
        print(f"    {fid1} <-> {fid2}: {sim:.4f}")
    print()

def test_content_hash():
    """Test content hashing."""
    print("Testing content hash...")

    hash1 = compute_content_hash("Title", "Content goes here...")
    hash2 = compute_content_hash("Title", "Content goes here...")
    hash3 = compute_content_hash("Title", "Different content")

    print(f"  Hash1: {hash1}")
    print(f"  Hash2: {hash2}")
    print(f"  Hash3: {hash3}")
    print(f"  Hash1 == Hash2: {hash1 == hash2}")
    print(f"  Hash1 == Hash3: {hash1 == hash3}")
    print()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DATACORTEX EMBEDDING INFRASTRUCTURE TEST")
    print("="*60 + "\n")

    try:
        test_basic_embedding()
        test_batch_embedding()
        test_similarity()
        test_similarity_matrix()
        test_content_hash()

        print("="*60)
        print("  ALL TESTS PASSED")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
