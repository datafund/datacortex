# Datacortex Embeddings - Phase 1 Implementation

## Overview

Phase 1 implements the embedding infrastructure for semantic search and document similarity in Datacortex. This enables AI-powered discovery of related documents across the knowledge graph.

## Architecture

### Components

```
src/datacortex/ai/
├── __init__.py         # Module initialization
├── embeddings.py       # Embedding generation (sentence-transformers)
├── cache.py           # SQLite caching layer
└── similarity.py      # Similarity computation
```

### Data Flow

1. **Document Retrieval**: Read documents from existing `files` table in knowledge.db
2. **Text Preparation**: Combine title + first 500 chars of content
3. **Embedding Generation**: Use sentence-transformers/all-mpnet-base-v2 model
4. **Caching**: Store embeddings in new `embeddings` table with content hashing
5. **Similarity**: Compute pairwise cosine similarity on demand

## Implementation Details

### Model Selection

- **Model**: `sentence-transformers/all-mpnet-base-v2`
- **Embedding dimension**: 768
- **Download location**: `~/.cache/huggingface/`
- **Performance**: ~100-200 docs/sec on CPU

### Caching Strategy

Embeddings are cached in SQLite with content-based invalidation:

```sql
CREATE TABLE embeddings (
    file_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    model TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

- **Storage**: numpy arrays serialized to BLOB via `.tobytes()`
- **Change detection**: MD5 hash of title + first 500 chars
- **Incremental updates**: Only recompute when content changes

### Batch Processing

- Batch size: 32 documents (balances memory and speed)
- Progress bar enabled for user feedback
- Parallel processing: model inference is batched by sentence-transformers

## CLI Usage

### Compute Embeddings

```bash
# Compute for all spaces (incremental)
datacortex embed

# Compute for specific space
datacortex embed --space personal

# Force recompute all (ignore cache)
datacortex embed --force
datacortex embed --space datafund --force
```

### Output Example

```
==================================================
  DATACORTEX EMBEDDING COMPUTATION
==================================================
  Model: sentence-transformers/all-mpnet-base-v2
  Spaces: personal, datafund
  Mode: INCREMENTAL (cache enabled)
==================================================

Processing space: personal
Computing embeddings for 150 new/changed documents...
Batches: 100%|████████████| 5/5 [00:12<00:00,  2.45s/it]
  Completed: 1500 documents in 12.5s
  Speed: 120.0 docs/sec

Processing space: datafund
All embeddings up to date (using cache)
  Completed: 800 documents in 0.2s

==================================================
  SUMMARY
==================================================
  Total documents: 2300
  Total time: 12.7s
  Average speed: 181.1 docs/sec
==================================================
```

## API Usage

### Python API

```python
from datacortex.ai.embeddings import compute_embeddings_for_space
from datacortex.ai.similarity import compute_similarity_matrix, find_similar_pairs

# Compute embeddings for a space
embeddings = compute_embeddings_for_space("personal")
# Returns: dict[str, np.ndarray] mapping file_id to embedding

# Compute similarity matrix
file_ids, matrix = compute_similarity_matrix(embeddings)
# Returns: (list of file_ids, NxN similarity matrix)

# Find similar pairs
pairs = find_similar_pairs(file_ids, matrix, threshold=0.75)
# Returns: list of (file_id1, file_id2, similarity) tuples
```

### Embedding Individual Documents

```python
from datacortex.ai.embeddings import embed_text, embed_documents

# Single text
text = "Machine learning is a subset of AI"
embedding = embed_text(text)  # Returns: np.ndarray (768,)

# Multiple documents
docs = [
    {"id": "doc1", "title": "ML", "content": "Machine learning..."},
    {"id": "doc2", "title": "DL", "content": "Deep learning..."},
]
embeddings = embed_documents(docs)
# Returns: dict[str, np.ndarray] mapping doc_id to embedding
```

### Similarity Computation

```python
from datacortex.ai.similarity import cosine_similarity, find_most_similar

# Pairwise similarity
sim = cosine_similarity(embedding1, embedding2)  # Returns: float (0 to 1)

# Find most similar documents
similar = find_most_similar(
    file_id="doc123",
    file_ids=file_ids,
    matrix=similarity_matrix,
    top_k=10
)
# Returns: list of (file_id, similarity) tuples
```

## Database Schema

### embeddings Table

Added to each space's `.datacore/knowledge.db`:

| Column | Type | Description |
|--------|------|-------------|
| `file_id` | TEXT PRIMARY KEY | References files.id |
| `embedding` | BLOB | Serialized numpy array (768 floats) |
| `model` | TEXT | Model identifier for version tracking |
| `content_hash` | TEXT | MD5 hash for change detection |
| `created_at` | TEXT | ISO timestamp of computation |

### Integration with files Table

The existing `files` table provides document data:

| Column | Used For |
|--------|----------|
| `id` | Primary key and embedding cache key |
| `title` | Included in embedding text |
| `content` | First 500 chars included in embedding |

## Performance Characteristics

### Computation Speed

- **Cold start** (first run): ~100-150 docs/sec (model loading + inference)
- **Warm cache** (no changes): ~1000+ docs/sec (cache reads only)
- **Incremental** (some changes): Depends on change ratio

### Memory Usage

- **Model**: ~400MB RAM
- **Embeddings**: 3KB per document (768 floats × 4 bytes)
- **Batch processing**: ~50MB per batch of 32 documents

### Storage

- **Per document**: ~3KB in SQLite BLOB
- **1000 documents**: ~3MB database overhead
- **10000 documents**: ~30MB database overhead

## Testing

Run the test script to verify functionality:

```bash
python test_embeddings.py
```

Tests cover:
- Basic text embedding
- Batch document embedding
- Similarity computation (pairwise and matrix)
- Content hashing
- Cache consistency

## Future Enhancements (Phase 2+)

### Planned Features

1. **API Endpoints**
   - `GET /api/similar/{file_id}` - Find similar documents
   - `GET /api/search/semantic?q=` - Semantic search
   - `POST /api/embeddings/compute` - Trigger recomputation

2. **Frontend Integration**
   - "Related Documents" sidebar in graph UI
   - Semantic search bar
   - Similarity heatmap visualization

3. **Advanced Features**
   - Multi-model support (switch between embedding models)
   - Dimension reduction (UMAP/t-SNE for visualization)
   - Clustering (identify document clusters)
   - Topic modeling (extract themes)

4. **Performance Optimization**
   - GPU acceleration for batch processing
   - Approximate nearest neighbor search (FAISS/Annoy)
   - Incremental similarity matrix updates

## Dependencies

Added to `pyproject.toml`:

```toml
sentence-transformers = ">=2.2.0"
numpy = ">=1.24.0"
```

These bring in transitive dependencies:
- `transformers` - Hugging Face model loading
- `torch` - PyTorch backend
- `tokenizers` - Fast text tokenization
- `huggingface-hub` - Model download and caching

## Configuration

### Model Location

Models download to `~/.cache/huggingface/hub/` automatically. To change location:

```bash
export HF_HOME=/path/to/cache
```

### Database Location

Embeddings are stored in each space's knowledge database:

- Personal: `~/Data/0-personal/.datacore/knowledge.db`
- Datafund: `~/Data/1-datafund/.datacore/knowledge.db`
- Datacore: `~/Data/2-datacore/.datacore/knowledge.db`

## Troubleshooting

### Out of Memory

If you encounter OOM errors:

1. Reduce batch size in `embeddings.py`:
   ```python
   embeddings = model.encode(texts, batch_size=16)  # Default: 32
   ```

2. Process spaces individually:
   ```bash
   datacortex embed --space personal
   datacortex embed --space datafund
   ```

### Slow Performance

If embedding is slow:

1. Check model is cached (first run downloads ~400MB)
2. Use incremental mode (default) instead of `--force`
3. Consider GPU acceleration (requires CUDA-enabled PyTorch)

### Cache Inconsistency

If embeddings seem stale:

```bash
datacortex embed --force  # Recompute all
```

Or manually clear cache:

```bash
sqlite3 ~/Data/0-personal/.datacore/knowledge.db "DELETE FROM embeddings"
```

## Files Created

### Core Implementation

- `src/datacortex/ai/__init__.py` - Module initialization
- `src/datacortex/ai/embeddings.py` - Embedding generation (175 lines)
- `src/datacortex/ai/cache.py` - SQLite caching (140 lines)
- `src/datacortex/ai/similarity.py` - Similarity computation (130 lines)

### Supporting Files

- `test_embeddings.py` - Integration tests (150 lines)
- `EMBEDDINGS.md` - This documentation

### Modified Files

- `pyproject.toml` - Added dependencies
- `src/datacortex/cli/commands.py` - Added `embed` command

## Next Steps

With Phase 1 complete, the infrastructure is ready for:

1. **Phase 2**: API endpoints for similarity queries
2. **Phase 3**: Frontend integration with graph UI
3. **Phase 4**: Advanced features (clustering, search, recommendations)

The foundation is modular and extensible - each component can be enhanced independently without breaking the core functionality.
