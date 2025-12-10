#!/usr/bin/env python3
"""
Example usage of Datacortex embedding infrastructure.

This demonstrates the key features of Phase 1:
- Computing embeddings for documents
- Finding similar documents
- Using the caching system
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from datacortex.ai.embeddings import (
    embed_text,
    embed_documents,
    compute_embeddings_for_space,
)
from datacortex.ai.similarity import (
    compute_similarity_matrix,
    find_similar_pairs,
    find_most_similar,
)
from datacortex.core.database import get_connection


def example_1_basic_embedding():
    """Example 1: Embed a single piece of text."""
    print("\n" + "="*60)
    print("Example 1: Basic Text Embedding")
    print("="*60)

    text = "Machine learning and artificial intelligence are transforming software development."
    embedding = embed_text(text)

    print(f"\nInput text: {text}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 dimensions: {embedding[:5]}")


def example_2_batch_embedding():
    """Example 2: Embed multiple documents in batch."""
    print("\n" + "="*60)
    print("Example 2: Batch Document Embedding")
    print("="*60)

    docs = [
        {
            "id": "ml-basics",
            "title": "Introduction to Machine Learning",
            "content": "Machine learning is a subset of AI that enables computers to learn from data..."
        },
        {
            "id": "dl-overview",
            "title": "Deep Learning Overview",
            "content": "Deep learning uses neural networks with multiple layers to learn hierarchical representations..."
        },
        {
            "id": "cooking-guide",
            "title": "How to Cook Pasta",
            "content": "Boil water in a large pot, add salt, then add pasta and cook for 8-10 minutes..."
        },
    ]

    embeddings = embed_documents(docs)

    print(f"\nEmbedded {len(embeddings)} documents:")
    for doc_id in embeddings:
        print(f"  - {doc_id}: {embeddings[doc_id].shape}")


def example_3_similarity():
    """Example 3: Compute document similarity."""
    print("\n" + "="*60)
    print("Example 3: Document Similarity")
    print("="*60)

    docs = [
        {
            "id": "ml-basics",
            "title": "Introduction to Machine Learning",
            "content": "Machine learning is a subset of AI that enables computers to learn from data..."
        },
        {
            "id": "dl-overview",
            "title": "Deep Learning Overview",
            "content": "Deep learning uses neural networks with multiple layers to learn hierarchical representations..."
        },
        {
            "id": "cooking-guide",
            "title": "How to Cook Pasta",
            "content": "Boil water in a large pot, add salt, then add pasta and cook for 8-10 minutes..."
        },
    ]

    embeddings = embed_documents(docs)
    file_ids, matrix = compute_similarity_matrix(embeddings)

    print("\nSimilarity Matrix:")
    print(f"File IDs: {file_ids}")
    print("\nMatrix:")
    for i, fid1 in enumerate(file_ids):
        row_str = f"  {fid1:15} "
        for j, fid2 in enumerate(file_ids):
            row_str += f" {matrix[i][j]:.3f}"
        print(row_str)

    print("\n\nKey observations:")
    print(f"  - ML vs DL similarity: {matrix[0][1]:.3f} (high - related topics)")
    print(f"  - ML vs Cooking similarity: {matrix[0][2]:.3f} (low - unrelated topics)")


def example_4_find_similar():
    """Example 4: Find most similar documents."""
    print("\n" + "="*60)
    print("Example 4: Find Similar Documents")
    print("="*60)

    docs = [
        {"id": "ml-1", "title": "ML Basics", "content": "Machine learning fundamentals..."},
        {"id": "ml-2", "title": "ML Advanced", "content": "Advanced machine learning techniques..."},
        {"id": "dl-1", "title": "Deep Learning", "content": "Deep neural networks..."},
        {"id": "nlp-1", "title": "NLP", "content": "Natural language processing..."},
        {"id": "cooking-1", "title": "Cooking", "content": "How to cook pasta..."},
    ]

    embeddings = embed_documents(docs)
    file_ids, matrix = compute_similarity_matrix(embeddings)

    # Find documents similar to ml-1
    target = "ml-1"
    similar = find_most_similar(target, file_ids, matrix, top_k=3)

    print(f"\nDocuments most similar to '{target}':")
    for fid, similarity in similar:
        doc = next(d for d in docs if d["id"] == fid)
        print(f"  {fid:12} (similarity: {similarity:.3f}) - {doc['title']}")


def example_5_similar_pairs():
    """Example 5: Find all similar pairs above threshold."""
    print("\n" + "="*60)
    print("Example 5: Find Similar Pairs")
    print("="*60)

    docs = [
        {"id": "ml-1", "title": "ML Basics", "content": "Machine learning fundamentals..."},
        {"id": "ml-2", "title": "ML Advanced", "content": "Advanced machine learning techniques..."},
        {"id": "dl-1", "title": "Deep Learning", "content": "Deep neural networks..."},
        {"id": "nlp-1", "title": "NLP", "content": "Natural language processing..."},
        {"id": "cooking-1", "title": "Cooking", "content": "How to cook pasta..."},
    ]

    embeddings = embed_documents(docs)
    file_ids, matrix = compute_similarity_matrix(embeddings)

    # Find pairs with similarity > 0.6
    pairs = find_similar_pairs(file_ids, matrix, threshold=0.6)

    print(f"\nFound {len(pairs)} similar pairs (threshold=0.6):")
    for fid1, fid2, similarity in pairs:
        print(f"  {fid1:12} <-> {fid2:12}  similarity: {similarity:.3f}")


def example_6_space_embeddings():
    """Example 6: Compute embeddings for an entire space."""
    print("\n" + "="*60)
    print("Example 6: Space-wide Embeddings")
    print("="*60)

    space = "personal"  # or "datafund", "datacore"

    try:
        print(f"\nComputing embeddings for space: {space}")
        print("This will use caching - only new/changed docs will be processed.\n")

        embeddings = compute_embeddings_for_space(space, force=False)

        print(f"\nTotal embeddings: {len(embeddings)}")

        if embeddings:
            # Show some stats
            first_id = list(embeddings.keys())[0]
            print(f"Embedding dimension: {embeddings[first_id].shape[0]}")

            # You can now use these embeddings for similarity search
            file_ids, matrix = compute_similarity_matrix(embeddings)
            print(f"Similarity matrix shape: {matrix.shape}")

    except Exception as e:
        print(f"\nNote: Could not compute embeddings for space '{space}'")
        print(f"Error: {e}")
        print("\nMake sure:")
        print(f"  1. Space exists with knowledge database")
        print(f"  2. Run 'python zettel_db.py init --space {space}' if needed")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DATACORTEX EMBEDDING EXAMPLES")
    print("="*60)

    example_1_basic_embedding()
    example_2_batch_embedding()
    example_3_similarity()
    example_4_find_similar()
    example_5_similar_pairs()
    example_6_space_embeddings()

    print("\n" + "="*60)
    print("  EXAMPLES COMPLETE")
    print("="*60 + "\n")
