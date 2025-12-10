# Datacortex

Knowledge graph visualization and AI-powered analysis for [Datacore](https://github.com/datafund/datacore).

## Features

- **Graph Visualization**: Interactive D3.js force-directed graph
- **Temporal Pulses**: Snapshot graph state over time
- **Multi-Space**: Configure which Datacore spaces to include
- **Metrics**: Degree centrality, PageRank, Louvain clustering
- **AI Extensions**: Semantic search, link suggestions, gap detection, Q&A

## Installation

```bash
cd ~/Data/1-datafund/2-projects/datacortex
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# 1. Compute embeddings (first time, ~5-10 min)
datacortex embed

# 2. Start visualization server
datacortex serve
# Open http://localhost:8765

# 3. Get AI-powered suggestions
datacortex digest              # Link suggestions
datacortex gaps                # Knowledge gaps
datacortex insights            # Cluster analysis
datacortex search "query"      # Question answering
```

## CLI Commands

```bash
# Graph generation
datacortex generate --spaces personal,datafund
datacortex stats

# Pulse snapshots
datacortex pulse generate
datacortex pulse list
datacortex pulse diff 2025-01-01 2025-01-15

# AI Extensions
datacortex embed [--space NAME] [--force]
datacortex digest [--threshold 0.8] [--top-n 20]
datacortex gaps [--min-score 0.3]
datacortex insights [--cluster N] [--top 5]
datacortex search "query" [--top 10] [--no-expand]

# Server
datacortex serve [--port 8765]
```

## Datacore Commands

Use from Claude Code for AI-synthesized insights. These commands run the CLI tools and have Claude synthesize natural language recommendations from the results.

| Command | Model | Purpose |
|---------|-------|---------|
| `/datacortex` | - | Launch visualization server and open browser |
| `/datacortex-digest` | haiku | Link suggestions based on semantic similarity |
| `/datacortex-gaps` | haiku | Bridge suggestions between knowledge clusters |
| `/datacortex-insights` | sonnet | Deep cluster analysis with themes and patterns |
| `/datacortex-ask [question]` | haiku | Answer questions from your knowledge base (RAG) |

**Model assignments**: Commands use `## Model` hints to tell Claude Code which model to use. Haiku is fast/cheap for suggestions; Sonnet provides deeper analysis for insights.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATACORTEX SERVER                         │
│  - Embeddings (sentence-transformers, cached in SQLite)     │
│  - Vector similarity (cosine, matrix computation)           │
│  - Graph metrics (NetworkX, Louvain clustering)             │
│  - Compact output (TSV/markdown, ~60% smaller than JSON)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SESSION                       │
│  - Natural language synthesis                                │
│  - Link suggestions with reasoning                          │
│  - Bridge recommendations                                    │
│  - Question answering with citations                        │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
datacortex/
├── src/datacortex/
│   ├── core/           # Models, config, database
│   ├── indexer/        # Graph building from zettel_db
│   ├── metrics/        # Centrality, clustering
│   ├── pulse/          # Temporal snapshots
│   ├── ai/             # Embeddings, similarity, cache
│   ├── digest/         # Daily link suggestions
│   ├── gaps/           # Knowledge gap detection
│   ├── insights/       # Cluster analysis
│   ├── qa/             # Question answering (RAG)
│   ├── api/            # FastAPI backend
│   └── cli/            # Click commands
├── frontend/           # D3.js visualization
├── config/             # YAML configuration
└── docs/               # Documentation
```

## AI Extensions

Datacortex includes 5 AI-powered features that work together. The server computes embeddings, similarity, and metrics; Claude Code synthesizes natural language insights from the results.

### Phase 1: Embeddings (`datacortex embed`)

Compute semantic embeddings for all documents using local sentence-transformers (no API keys needed).

- **Model**: `sentence-transformers/all-mpnet-base-v2` (768 dimensions, high quality)
- **Content**: Title + first 500 characters (balanced quality/speed)
- **Cache**: SQLite with content hash invalidation (only recomputes changed docs)
- **Speed**: ~25 docs/sec on M1 Mac

```bash
datacortex embed              # Incremental (only new/changed)
datacortex embed --force      # Recompute all
datacortex embed --space personal  # Single space
```

### Phase 2: Daily Digest (`datacortex digest`)

Find documents that should be linked based on semantic similarity but aren't yet connected.

- **Similar pairs**: Documents with cosine similarity > 0.75 that have no existing link
- **Scoring**: `similarity * 0.5 + recency * 0.3 + centrality * 0.2`
- **Orphans**: Documents with no incoming links (candidates for integration)
- **Output**: Compact TSV format for Claude Code to synthesize recommendations

```bash
datacortex digest --threshold 0.8 --top-n 20
```

### Phase 3: Knowledge Gaps (`datacortex gaps`)

Detect sparse areas between knowledge clusters that need bridge notes.

- **Cluster centroids**: Mean embedding of all documents in each Louvain cluster
- **Gap score**: `semantic_similarity - link_density` (high similarity but few links = gap)
- **Boundary nodes**: Documents that link to both clusters (potential bridges)
- **Bridge suggestions**: Topics that could connect the clusters

```bash
datacortex gaps --min-score 0.3
```

### Phase 4: Insight Extraction (`datacortex insights`)

Analyze knowledge clusters to identify themes, hubs, and patterns.

- **Cluster stats**: Size, density, average centrality
- **Hub documents**: Top 10 by PageRank centrality (most connected/influential)
- **Tag frequency**: Top 10 tags revealing cluster themes
- **Content samples**: Excerpts from top docs for context

```bash
datacortex insights --cluster 3    # Single cluster detail
datacortex insights --top 5        # Top 5 clusters by size
```

### Phase 5: Question Answering (`datacortex search`)

RAG (Retrieval-Augmented Generation) pipeline for "What do I know about X?" queries.

- **Pipeline**: Embed query → vector search top 10 → graph expansion (1-hop neighbors) → re-rank
- **Re-ranking**: `vec_score * 0.6 + recency * 0.2 + centrality * 0.2`
- **Direct match boost**: 1.2x for original vector search hits
- **Full content**: Complete document text included for Claude to synthesize answers

```bash
datacortex search "data tokenization" --top 10
datacortex search "DMCC pilot" --no-expand  # Skip graph expansion
```

## Configuration

Create `config/datacortex.local.yaml` to override defaults:

```yaml
spaces:
  - personal
  - datafund

server:
  port: 8765

graph:
  include_stubs: false
  compute_clusters: true

ai:
  embedding_model: sentence-transformers/all-mpnet-base-v2
  content_length: 500
  qa_model: claude-3-haiku-20240307
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
