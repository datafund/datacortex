# Phase 3: Knowledge Gaps Implementation

## Summary

Phase 3 has been successfully implemented. The knowledge gaps feature detects semantically similar clusters that have few connections, helping identify opportunities to strengthen the knowledge base.

## Implementation Status: COMPLETE

All components have been implemented and are ready for use.

## Files Created

### 1. Core Module Files

#### `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/gaps/__init__.py`
- Empty init file marking the gaps module

#### `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/gaps/detector.py` (10.8 KB)
- `detect_gaps()` - Main gap detection function
- `ClusterInfo` - Dataclass for cluster metadata (size, hubs, tags)
- `KnowledgeGap` - Dataclass for gap representation
- `GapsResult` - Complete result with all detected gaps

**Algorithm:**
1. Build graph and compute Louvain clusters
2. Load embeddings for all spaces
3. Compute cluster centroids (mean of member embeddings)
4. For each cluster pair:
   - Compute semantic similarity (cosine of centroids)
   - Compute link density (cross_links / (size_a * size_b))
   - Calculate gap_score = semantic_sim - link_density
5. Filter gaps above threshold
6. Find boundary nodes and shared tags
7. Return sorted by gap_score descending

**Helper Functions:**
- `get_cluster_centroid()` - Average embedding of cluster members
- `get_cluster_info()` - Extract hub docs (top 5 centrality) and top tags
- `find_boundary_nodes()` - Nodes that link to both clusters
- `find_shared_tags()` - Tags appearing in both clusters
- `count_cross_links()` - Count edges between clusters

#### `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/gaps/formatter.py` (3.5 KB)
- `format_gaps()` - Formats GapsResult as compact TSV/markdown
- Output includes:
  - Gap rank and score
  - Semantic similarity vs link density
  - Hub documents for each cluster
  - Top tags for each cluster
  - Shared tags between clusters
  - Boundary nodes that bridge clusters

**Output Format:**
```
# KNOWLEDGE_GAPS count=5 generated=2025-12-10T12:30:00
## GAP rank=1 gap_score=0.58
clusters: 3, 7
semantic_sim: 0.72
link_density: 0.02
cross_links: 2

### CLUSTER_3 size=47
HUBS: Data Tokenization, Swarm Storage, API Design
TAGS: tokenization(12), data(10), api(8)

### CLUSTER_7 size=23
HUBS: Trading Journal, Position Sizing, Risk Management
TAGS: trading(8), risk(5), analytics(4)

SHARED_TAGS: data, analytics
BOUNDARY_NODES: Market Data Feed
```

### 2. CLI Integration

#### `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/cli/commands.py`
Added `gaps` command with options:
- `datacortex gaps` - Detect gaps for all spaces
- `datacortex gaps --space personal` - Single space
- `datacortex gaps --min-score 0.4` - Custom threshold

Output written to: `/tmp/datacortex_gaps_{timestamp}.txt`

### 3. Datacore Command

#### `/Users/tex/repos/datacore/.datacore/commands/datacortex-gaps.md`
Complete command documentation including:
- Overview of knowledge gaps concept
- Synthesis guidelines for Claude
- How to name clusters based on hub docs and tags
- Bridge action recommendations (expand nodes, create notes, add links, unify tags)
- Output format guidelines
- Prioritization criteria

## Integration with Existing System

The gaps module integrates cleanly with existing Datacortex components:

1. **Clustering**: Uses `metrics/clusters.py` - `compute_clusters()` with Louvain algorithm
2. **Embeddings**: Uses `ai/embeddings.py` - `compute_embeddings_for_space()` with caching
3. **Similarity**: Uses `ai/similarity.py` - `cosine_similarity()` for centroid comparison
4. **Graph Building**: Uses `indexer/graph_builder.py` - `build_graph()` for full graph
5. **Database**: Uses `core/database.py` - `get_connection()`, `space_exists()`

## Usage

### Command Line

```bash
# Analyze all spaces with default threshold (0.3)
datacortex gaps

# Analyze specific space
datacortex gaps --space personal

# Use higher threshold for only significant gaps
datacortex gaps --min-score 0.5
```

### Datacore Integration

```bash
# From Claude Code CLI
/datacortex-gaps
```

This will:
1. Run `datacortex gaps` to generate analysis
2. Read the output file
3. Synthesize actionable bridge suggestions
4. Present gaps with specific recommendations

## Key Metrics

Each knowledge gap includes:
- **Semantic Similarity**: How related the clusters are (0-1)
- **Link Density**: Actual connections / maximum possible (0-1)
- **Gap Score**: Semantic similarity minus link density
- **Cross Links**: Absolute count of connections
- **Cluster Sizes**: Number of documents in each cluster
- **Hub Documents**: Top 5 most central documents per cluster
- **Top Tags**: Most frequent tags per cluster (with counts)
- **Shared Tags**: Tags appearing in both clusters
- **Boundary Nodes**: Documents that already link both clusters

## Gap Score Interpretation

- **High gap score (>0.5)**: Clusters are very related but barely connected - high priority
- **Medium gap score (0.3-0.5)**: Some semantic relationship, few connections - worth investigating
- **Low gap score (<0.3)**: Either not very related or already well-connected - can ignore

## Bridge Recommendations

The formatter and command work together to suggest:

1. **Expand Boundary Nodes** (easiest)
   - Documents already linking both clusters
   - Add more explicit connections in their content

2. **Create Bridge Notes** (most impactful)
   - New documents explicitly connecting themes
   - Suggested titles and key points

3. **Add Direct Links** (quick wins)
   - Specific wiki-links between existing documents
   - Strategic connections between hub docs

4. **Unify Tags** (organizational)
   - Standardize shared tags
   - Add spanning tags to both clusters

## Output Storage

All gap analyses are written to:
```
/tmp/datacortex_gaps_{timestamp}.txt
```

Format: `YYYYMMDD_HHMMSS`

Example: `/tmp/datacortex_gaps_20251210_133000.txt`

## Dependencies

All dependencies already specified in `pyproject.toml`:
- `numpy` - Array operations for centroids
- `networkx` - Graph analysis (already used for clustering)
- `sentence-transformers` - Embeddings (already used in Phase 1)

No new dependencies required.

## Testing

To test after installation:

```bash
# Install datacortex in development mode
pip install -e .

# Ensure embeddings are computed
datacortex embed

# Run gap detection
datacortex gaps --space personal

# View output
cat /tmp/datacortex_gaps_*.txt | tail -1 | xargs cat
```

## Next Steps

1. Install datacortex in development mode: `pip install -e .`
2. Compute embeddings if not already done: `datacortex embed`
3. Run gap detection: `datacortex gaps`
4. Test the `/datacortex-gaps` command in Claude Code CLI
5. Review gap suggestions and implement bridge recommendations

## Architecture Notes

The gaps module follows the same pattern as the digest module:
- `detector.py` - Core algorithm and data structures
- `formatter.py` - Output formatting for Claude consumption
- CLI integration in `commands.py`
- Datacore command in `.datacore/commands/`

This consistency makes the codebase easy to understand and extend.

## Future Enhancements

Potential improvements for future phases:
1. Temporal analysis - track how gaps close over time
2. Gap visualization in the web UI
3. Automated link suggestions (not just manual recommendations)
4. Gap prioritization based on user activity (recent edits/views)
5. Integration with `/today` briefing to show new gaps

---

**Status**: Phase 3 Complete
**Date**: 2025-12-10
**Location**: `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/`
