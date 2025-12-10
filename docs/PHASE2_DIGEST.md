# Phase 2: Daily Digest Implementation

**Status**: Complete
**Date**: 2025-12-10

## Overview

Phase 2 implements a daily digest system that suggests document links based on semantic similarity using embeddings from Phase 1. The digest identifies pairs of documents that should be linked but aren't, as well as orphan documents with no incoming links.

## Implementation

### 1. Digest Module Structure

```
src/datacortex/digest/
├── __init__.py          # Module init
├── generator.py         # Core digest generation logic
└── formatter.py         # Compact TSV/markdown formatting
```

### 2. Core Components

#### generator.py

Main digest generation with the following functions:

- **`generate_digest(spaces, threshold, top_n, min_orphan_words)`**
  - Main entry point for digest generation
  - Computes/loads embeddings for each space
  - Finds similar pairs above threshold
  - Filters out already-linked pairs
  - Scores pairs using weighted formula
  - Returns top N suggestions

- **`get_existing_links(conn)`**
  - Returns set of (source_id, target_id) for all resolved links
  - Used to filter out already-linked pairs

- **`get_recency_score(updated_at)`**
  - Scores documents by recency (0-1)
  - 1.0 = updated today
  - Decays linearly over 30 days

- **`get_orphans(conn, min_word_count)`**
  - Finds documents with no incoming links
  - Filters by minimum word count
  - Returns up to 50 orphans sorted by word count

- **`get_file_metadata(conn)`**
  - Retrieves title, path, updated_at for all files
  - Used to enrich similarity pairs

- **`get_centrality_scores(conn)`**
  - Computes centrality using degree as proxy
  - Normalizes to 0-1 range
  - Used in final scoring

**Data Classes:**

```python
@dataclass
class SimilarPair:
    doc_a: str              # title
    doc_b: str              # title
    path_a: str
    path_b: str
    similarity: float       # cosine similarity (0-1)
    recency_score: float    # recency average (0-1)
    centrality_avg: float   # centrality average (0-1)
    final_score: float      # weighted score

@dataclass
class OrphanDoc:
    title: str
    path: str
    word_count: int
    created_at: str

@dataclass
class DigestResult:
    similar_pairs: list[SimilarPair]
    orphans: list[OrphanDoc]
    threshold: float
    generated_at: str
```

**Scoring Formula:**

```
final_score = similarity * 0.5 + recency * 0.3 + centrality * 0.2
```

- **similarity (50%)**: Semantic similarity of embeddings
- **recency (30%)**: How recently documents were updated
- **centrality (20%)**: Average graph connectivity

#### formatter.py

Formats digest results as compact TSV/markdown for Claude consumption:

```
# DATACORTEX DAILY DIGEST
# Generated: 2025-12-10T13:30:00

# SIMILAR_PAIRS threshold=0.75 count=20
# format: doc_a | doc_b | similarity | recency | centrality | score
Data Tokenization | Real World Assets | 0.87 | 0.9 | 0.04 | 0.73
KYC State Machine | Verity Compliance | 0.82 | 0.8 | 0.02 | 0.66

# ORPHANS count=10
# format: title | words | created_at | path
Autonomous AI Legal Entity | 278w | 2025-12-09 | ...
Data Business | 156w | 2025-12-08 | ...
```

### 3. CLI Command

Added to `src/datacortex/cli/commands.py`:

```bash
datacortex digest [OPTIONS]

Options:
  -s, --space TEXT         # Generate for specific space (default: all)
  -t, --threshold FLOAT    # Similarity threshold (default: 0.75)
  -n, --top-n INTEGER      # Number of top suggestions (default: 20)
  -w, --min-words INTEGER  # Minimum words for orphans (default: 50)
```

**Behavior:**

1. Computes/loads embeddings for specified spaces
2. Computes similarity matrix
3. Finds similar pairs above threshold
4. Filters out already-linked pairs
5. Scores pairs using weighted formula
6. Formats as compact TSV/markdown
7. Writes to `/tmp/datacortex_digest_{timestamp}.txt`
8. Prints path to stderr and content to stdout

### 4. Datacore Command

Created `.datacore/commands/datacortex-digest.md`:

This command wraps the CLI tool and provides guidance for Claude Code to:

1. Run `datacortex digest`
2. Read the output file
3. Synthesize natural language suggestions
4. Present actionable link recommendations

**Synthesis Guidelines:**

- Explain why pairs should be linked
- Suggest which document should link to which
- Identify isolated orphans and suggest integration
- Focus on high-scoring pairs and substantial orphans

## Usage

### Basic Usage

```bash
# Generate digest for all spaces
datacortex digest

# Generate for specific space
datacortex digest --space datafund

# Adjust threshold and result count
datacortex digest --threshold 0.8 --top-n 30
```

### From Claude Code

```
/datacortex-digest
```

This will:
1. Run the digest generation
2. Read and parse the output
3. Provide natural language recommendations
4. Suggest specific links to add

## Integration Points

### Reuses Phase 1 Infrastructure

- `compute_embeddings_for_space()` from `ai/embeddings.py`
- `compute_similarity_matrix()` from `ai/similarity.py`
- `find_similar_pairs()` from `ai/similarity.py`
- `get_connection()` from `core/database.py`

### Database Tables

Reads from:
- `files` - Document metadata
- `links` - Existing link relationships
- `embeddings` - Cached embeddings (via Phase 1)

## Configuration

Uses settings from `config/datacortex.yaml`:

```yaml
spaces:
  - personal
  - datafund
  - datacore
```

## Testing

The implementation has been tested with:

- 1283 files in datafund space
- 2859 existing links
- Embeddings computed on-demand

To test manually:

```bash
# Set the correct data root
export DATACORE_ROOT=/Users/tex/repos/datacore

# Generate digest
cd /Users/tex/repos/datacore/1-datafund/2-projects/datacortex
.venv/bin/datacortex digest --space datafund --threshold 0.85 --top-n 5
```

## Future Enhancements

Possible improvements for future phases:

1. **Confidence Scoring**: Add confidence metrics based on link direction probability
2. **Temporal Trends**: Track which suggestions were acted upon vs ignored
3. **Link Direction**: Use document maturity/type to suggest which way to link
4. **Batch Processing**: Allow applying suggestions in bulk with review
5. **Email Digest**: Send daily email with suggestions
6. **Integration with Obsidian**: Direct integration to add links in-place

## Files Created

1. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/digest/__init__.py`
2. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/digest/generator.py`
3. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/digest/formatter.py`
4. `/Users/tex/repos/datacore/.datacore/commands/datacortex-digest.md`

## Files Modified

1. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/cli/commands.py`
   - Added `digest` command

## Notes

- The digest command requires embeddings to be computed first (via Phase 1)
- Embeddings are cached and only recomputed for changed documents
- The scoring formula can be tuned by adjusting weights in `generator.py`
- Output format is optimized for Claude consumption (compact TSV)
- Orphans are limited to 50 to avoid overwhelming output
