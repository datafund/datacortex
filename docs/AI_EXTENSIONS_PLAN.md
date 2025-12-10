# Datacortex AI Extensions Plan

## Overview

This document outlines the implementation plan for four AI-powered extensions to Datacortex that transform it from a visualization tool into an intelligent knowledge assistant.

**Core Vision**: Your knowledge graph has hidden structure - connections that should exist but don't, clusters that form naturally, insights that span topics. These extensions surface that hidden structure through AI analysis.

## Architecture

### Key Insight: Claude Code IS the LLM

No external API integration needed for natural language generation. Claude Code session handles all synthesis.

```
┌─────────────────────────────────────────────────────────────┐
│                    DATACORTEX SERVER                         │
│  - Embeddings (pre-computed, stored in SQLite)              │
│  - Vector similarity (pure math)                             │
│  - Graph metrics (NetworkX)                                  │
│  - Structured data endpoints                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    Compact Text Format (not JSON)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SESSION                       │
│  - Natural language explanations                             │
│  - Bridge suggestions                                        │
│  - Insight summaries                                         │
│  - Question answering synthesis                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Exchange Format

**JSON is wasteful** for Claude Code consumption. Use compact text formats instead:

#### Similar Pairs (Daily Digest)
```
# SIMILAR_PAIRS threshold=0.75
Data Tokenization | Real World Assets | 0.87 | unlinked
KYC State Machine | Verity Compliance | 0.82 | unlinked
Swarm Storage | IPFS Overview | 0.79 | linked
```

#### Cluster Analysis (Insights)
```
# CLUSTER id=3 size=47 avg_words=342
## HUBS
Data Tokenization | 0.045 | 523w | rwa,tokenization,verity
Swarm Storage | 0.032 | 412w | storage,decentralized
API Design | 0.028 | 298w | api,patterns

## TAGS tokenization:12 data:10 api:8 rwa:6

## SAMPLE Data Tokenization
Data tokenization transforms data ownership into tradeable assets...
[first 500 chars]
```

#### Search Results (Q&A)
```
# SEARCH q="data tokenization" expanded=true
## RESULTS
0.92 | Data Tokenization | zettel | 523w
Data tokenization transforms data ownership into tradeable...

0.85 | Real World Assets | zettel | 412w
RWAs represent physical or digital assets on blockchain...

0.78 | Verity Specification | page | 2341w
Verity enables data owners to monetize datasets...
```

#### Knowledge Gaps
```
# GAPS
## GAP cluster_a=3 cluster_b=7 semantic=0.72 links=2 gap=0.58
Cluster A (47 docs): Data Tokenization, Swarm Storage, API Design...
Cluster B (23 docs): Trading Journal, Position Sizing, Risk Management...
Shared tags: data, analytics
```

**Benefits**:
- ~60% smaller than JSON
- No parsing overhead for Claude
- Human-readable for debugging
- Natural tabular structure

### Shared Infrastructure

```
src/datacortex/
├── ai/                          # AI module
│   ├── __init__.py
│   ├── embeddings.py            # Vector embedding generation
│   ├── similarity.py            # Cosine similarity operations
│   └── cache.py                 # Embedding cache (SQLite)
├── digest/                      # Extension 1: Daily Digest
│   └── generator.py
├── gaps/                        # Extension 2: Knowledge Gaps
│   └── detector.py
├── insights/                    # Extension 3: Insight Extraction
│   └── analyzer.py
└── qa/                          # Extension 4: Question Answering
    └── retriever.py
```

### Embedding Strategy

**Options**:

1. **Local model** (recommended): `sentence-transformers/all-MiniLM-L6-v2`
   - Free, no API keys
   - 384 dimensions, ~90MB model
   - Good quality for semantic search

2. **One-time API call**: OpenAI `text-embedding-3-small`
   - Better quality
   - ~$0.02 for all 1,300 docs (one-time)
   - Can be run from Claude Code session

**Storage**: SQLite table in knowledge.db
```sql
CREATE TABLE embeddings (
    file_id TEXT PRIMARY KEY,
    embedding BLOB,          -- numpy array as bytes
    model TEXT,
    created_at TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

**Caching Strategy**:
- Compute embeddings incrementally (only new/modified files)
- Store in SQLite for persistence
- ~1,300 notes × 384 dims × 4 bytes = ~2MB total

---

## Extension 1: Daily Digest

### Purpose
Generate "you should link these" suggestions based on content similarity.

### Server Computes
1. All pairwise similarities above threshold (0.75)
2. Filter to unlinked pairs only
3. Score by: similarity × recency × centrality
4. Return top 20 candidates

### Output Format
```
# SIMILAR_PAIRS threshold=0.75 count=20
# format: doc_a | doc_b | similarity | recency_score | centrality_avg
Data Tokenization | Real World Assets | 0.87 | 0.9 | 0.04
KYC State Machine | Verity Compliance | 0.82 | 0.8 | 0.02
...

# ORPHANS count=3
Autonomous AI Legal Entity | 278w | created=2025-12-09
Data Business | 156w | created=2025-12-08
```

### Claude Code Synthesizes
- "You should link X and Y because both discuss..."
- "These were created 2 days apart, suggesting related thinking"
- "3 notes have no incoming links and might be forgotten"

### CLI
```bash
datacortex digest              # Compact format for Claude
datacortex digest --threshold 0.8
```

---

## Extension 2: Knowledge Gaps

### Purpose
Detect sparse areas between clusters needing bridge notes.

### Server Computes
1. Cluster centroids (average embedding of members)
2. Semantic similarity between all cluster pairs
3. Actual link density between cluster pairs
4. Gap score = semantic_similarity - link_density

### Output Format
```
# GAPS count=5
## GAP rank=1 gap_score=0.58
clusters: 3, 7
semantic_sim: 0.72
link_density: 0.02
cross_links: 2

### CLUSTER_3 size=47 name=pending
HUBS: Data Tokenization, Swarm Storage, API Design
TAGS: tokenization, data, api, storage

### CLUSTER_7 size=23 name=pending
HUBS: Trading Journal, Position Sizing, Risk Management
TAGS: trading, risk, analytics

### SHARED_TAGS: data, analytics
### BOUNDARY_NODES (link both clusters): Market Data Feed
```

### Claude Code Synthesizes
- "Cluster 3 (Data Infrastructure) and Cluster 7 (Trading) are semantically related but poorly connected"
- "Consider creating a bridge note about 'Trading Data Pipeline'"
- "Expand [[Position Sizing]] to reference data feeds"

---

## Extension 3: Insight Extraction

### Purpose
Provide cluster analysis data for Claude Code to synthesize summaries.

### Server Computes
1. Cluster membership and statistics
2. Hub documents (top 10 by centrality)
3. Tag frequency distribution
4. Content samples (first 500 chars of top 5 docs)
5. Inter-cluster connections

### Output Format
```
# CLUSTER id=3 size=47
## STATS
avg_words: 342
total_words: 16074
avg_centrality: 0.012
density: 0.08

## HUBS
Data Tokenization | 0.045 | 523w | rwa,tokenization,verity
Swarm Storage | 0.032 | 412w | storage,decentralized
API Design | 0.028 | 298w | api,patterns
...

## TAG_FREQ
tokenization: 12
data: 10
api: 8
rwa: 6
storage: 5

## CONNECTIONS
cluster_1: 5 links (Trading)
cluster_5: 2 links (Legal)

## SAMPLES
### Data Tokenization (523w)
Data tokenization transforms data ownership into tradeable assets
through blockchain-based tokens. The SPV structure enables...
[500 chars]

### Swarm Storage (412w)
Swarm provides decentralized storage for data provenance...
[500 chars]
```

### Claude Code Synthesizes
- "This cluster focuses on technical data infrastructure"
- "Key themes: decentralized storage, tokenization, API patterns"
- "Missing: No notes on data migration or performance benchmarks"
- Suggested name: "Data Infrastructure"

---

## Extension 4: Question Answering

### Purpose
RAG retrieval for "What do I know about X?" queries.

### Server Computes
1. Embed query (using same model as corpus)
2. Vector search → top 10 candidates
3. Graph expansion → add 1-hop neighbors
4. Re-rank by: relevance × recency × centrality
5. Return top 5 with full content

### Output Format
```
# SEARCH q="data tokenization"
## PARAMS
expanded: true
top_k: 5

## RESULTS
### 1. Data Tokenization
relevance: 0.92
path: 3-knowledge/zettel/Data-Tokenization.md
type: zettel
words: 523
tags: rwa, tokenization, verity
--- CONTENT ---
Data tokenization transforms data ownership into tradeable assets...
[full content]
--- END ---

### 2. Real World Assets
relevance: 0.85
path: 3-knowledge/zettel/Real-World-Assets.md
...
```

### Claude Code Synthesizes
- Read retrieved documents
- Generate answer with [[wiki-link]] citations
- Assess confidence based on relevance scores

---

## Implementation Phases

### Phase 1: Embedding Infrastructure
1. Add `ai/` module with embedding generation
2. Create embeddings table in SQLite
3. Implement incremental computation (only new/modified)
4. CLI: `datacortex embed` to generate embeddings

**Deliverables**:
- `src/datacortex/ai/embeddings.py`
- `src/datacortex/ai/cache.py`
- Database migration

### Phase 2: Daily Digest
1. Implement similarity pair detection
2. Add scoring algorithm
3. Compact output format
4. CLI: `datacortex digest`

### Phase 3: Knowledge Gaps
1. Cluster centroid computation
2. Inter-cluster analysis
3. Gap scoring
4. CLI: `datacortex gaps`

### Phase 4: Insight Extraction
1. Cluster analysis aggregation
2. Content sampling
3. Compact output format
4. CLI: `datacortex insights`

### Phase 5: Question Answering
1. Vector search implementation
2. Graph expansion
3. Re-ranking
4. CLI: `datacortex search "query"`

---

## Dependencies

### New Python Dependencies

```toml
[project.dependencies]
# Existing...
# New:
sentence-transformers = ">=2.2.0"  # Local embeddings
numpy = ">=1.24.0"                  # Vector operations
```

### Optional (for API embeddings)
```toml
[project.optional-dependencies]
openai = ["openai>=1.0.0"]
```

---

## No External LLM API Needed

- Server computes structured data
- Claude Code session generates all natural language
- Embedding generation can use local model or one-time API call
- Zero runtime API costs

---

## Datacore Integration

### Commands
- `/datacortex digest` - Show link suggestions
- `/datacortex gaps` - Show knowledge gaps
- `/datacortex insights` - Cluster analysis
- `/datacortex ask "question"` - Q&A

### Agent
The `datacortex` agent reads compact output and synthesizes insights.

---

## Success Metrics

1. **Daily Digest Adoption**: Are suggestions leading to new links?
2. **Gap Detection Accuracy**: Do suggested bridges make sense?
3. **Insight Quality**: Are cluster summaries useful?
4. **QA Relevance**: Do answers cite the right sources?
