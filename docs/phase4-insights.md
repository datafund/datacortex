# Phase 4: Insight Extraction - Implementation Documentation

## Overview

Phase 4 implements cluster analysis and insight extraction for the Datacortex AI Extensions. This module analyzes knowledge graph clusters to extract meaningful patterns, identify hubs, and generate actionable insights.

## Location

All files are in: `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/`

## Components

### 1. Core Module: `src/datacortex/insights/`

#### `__init__.py`
Empty module initialization file.

#### `analyzer.py`
Main cluster analysis logic with the following key functions:

**Data Models:**
- `ClusterAnalysis` - Detailed analysis of a single cluster
  - `cluster_id`: Cluster identifier
  - `size`: Number of documents in cluster
  - `stats`: Metrics (avg_words, total_words, avg_centrality, density)
  - `hubs`: Top 10 documents by centrality
  - `tag_freq`: Top 10 most common tags
  - `connections`: Links to other clusters
  - `samples`: Content excerpts from top 5 documents

- `InsightsResult` - Complete analysis result
  - `clusters`: List of ClusterAnalysis objects
  - `total_docs`: Total documents analyzed
  - `total_clusters`: Number of clusters found
  - `generated_at`: ISO timestamp

**Main Functions:**

```python
def analyze_clusters(spaces: list[str]) -> InsightsResult:
    """
    Analyze all clusters in the given spaces.

    Algorithm:
    1. Build graph and compute Louvain clusters
    2. For each cluster:
       - Compute statistics
       - Extract hub documents
       - Count tag frequency
       - Find connections to other clusters
       - Sample content from top documents
    3. Return sorted by cluster size descending
    """

def analyze_single_cluster(cluster_id: int, spaces: list[str]) -> ClusterAnalysis:
    """Detailed analysis for one specific cluster."""

def load_document_content(conn, file_id: str) -> str:
    """Load full content from files table in database."""
```

**Helper Functions:**

```python
def get_cluster_stats(members: list, edges: list) -> dict:
    """Compute avg_words, total_words, avg_centrality, density."""

def get_hub_documents(members: list, top_n: int = 10) -> list[dict]:
    """Top documents by centrality with metadata."""

def get_tag_frequency(members: list) -> list[tuple[str, int]]:
    """Tag counts across cluster members."""

def get_cluster_connections(cluster_id: int, all_clusters: dict, edges: list) -> list[dict]:
    """Links from this cluster to other clusters."""

def get_content_samples(members: list, conn, top_n: int = 5, excerpt_len: int = 500) -> list[dict]:
    """Load content excerpts for top documents."""
```

#### `formatter.py`
Formats insights to compact TSV/markdown output:

```python
def format_insights(result: InsightsResult, include_samples: bool = True) -> str:
    """
    Format cluster insights to compact TSV/markdown.

    Output format:
    # CLUSTER_INSIGHTS clusters=N total_docs=N generated=TIMESTAMP

    ## CLUSTER id=N size=N
    ### STATS
    avg_words: N
    total_words: N
    avg_centrality: 0.XXX
    density: 0.XX

    ### HUBS
    Title | 0.XXX | NNNw | tags

    ### TAGS
    tag: count

    ### CONNECTIONS
    cluster_N: N links

    ### SAMPLES
    #### Title (NNNw)
    [excerpt...]
    """

def format_cluster_summary(result: InsightsResult) -> str:
    """Format brief summary table of all clusters."""
```

### 2. CLI Command: `src/datacortex/cli/commands.py`

Added `insights` command with the following options:

```bash
datacortex insights                     # All clusters summary
datacortex insights --cluster 3         # Single cluster detail
datacortex insights --no-samples        # Skip content samples
datacortex insights --top 5             # Only top N clusters by size
datacortex insights --space datafund    # Specific space only
```

**Options:**
- `--space, -s`: Analyze specific space (default: all spaces)
- `--cluster, -c`: Analyze single cluster by ID
- `--no-samples`: Skip content samples (faster analysis)
- `--top, -t`: Limit to top N clusters by size

**Output:**
- Writes to: `/tmp/datacortex_insights_{timestamp}.txt`
- Also prints to stdout

### 3. Datacore Command: `/.datacore/commands/datacortex-insights.md`

Location: `/Users/tex/repos/datacore/.datacore/commands/datacortex-insights.md`

This command integrates with Datacore's slash command system to provide AI-assisted insight synthesis.

**Usage:**
```bash
/datacortex-insights
```

**Behavior:**
1. Runs `datacortex insights` to generate cluster analysis
2. Reads the output file
3. Synthesizes insights using Claude
4. Generates comprehensive report with:
   - Cluster names (3-5 words)
   - Summaries (2-3 sentences)
   - Key themes (3-5 bullets)
   - Pattern analysis
   - Connection analysis
   - Gap identification
   - Actionable recommendations

### 4. Tests: `tests/test_insights.py`

Comprehensive test suite covering:
- Data model creation
- Cluster statistics computation
- Hub document extraction
- Tag frequency counting
- Cluster connection analysis
- Formatting functions
- Summary generation

## Integration Points

### Database Schema
Reads from Datacore's `zettel_db` schema:
- `files` table: For loading document content
- Uses existing `get_connection()` wrapper

### Dependencies
- `networkx`: Graph operations
- `build_graph()`: From existing indexer module
- `compute_clusters()`: From existing metrics module
- Reuses Louvain clustering from Phase 3

## Usage Examples

### Basic Analysis
```python
from datacortex.insights.analyzer import analyze_clusters
from datacortex.insights.formatter import format_insights

# Analyze all clusters
result = analyze_clusters(['datafund', 'personal'])

# Format output
formatted = format_insights(result, include_samples=True)
print(formatted)
```

### Single Cluster Deep Dive
```python
from datacortex.insights.analyzer import analyze_single_cluster

# Analyze specific cluster
analysis = analyze_single_cluster(cluster_id=3, spaces=['datafund'])

print(f"Cluster {analysis.cluster_id}: {analysis.size} documents")
print(f"Density: {analysis.stats['density']}")
print(f"Top hub: {analysis.hubs[0]['title']}")
```

### CLI Usage
```bash
# Full analysis
datacortex insights

# Quick analysis without samples
datacortex insights --no-samples

# Top 5 clusters only
datacortex insights --top 5

# Single cluster detail
datacortex insights --cluster 3

# Specific space
datacortex insights --space datafund
```

### Integration with Datacore
```bash
# In Claude Code CLI
/datacortex-insights

# This will:
# 1. Generate raw analysis
# 2. AI synthesizes insights
# 3. Produces strategic report with recommendations
```

## Output Format

### Raw Output (from CLI)
```
# CLUSTER_INSIGHTS clusters=12 total_docs=1283 generated=2025-12-10T12:30:00

## CLUSTER id=3 size=47
### STATS
avg_words: 342
total_words: 16074
avg_centrality: 0.012
density: 0.08

### HUBS
Data Tokenization | 0.045 | 523w | rwa,tokenization,verity
Swarm Storage | 0.032 | 412w | storage,decentralized
API Design | 0.028 | 298w | api,patterns

### TAGS
tokenization: 12
data: 10
api: 8
rwa: 6
storage: 5

### CONNECTIONS
cluster_1: 5 links
cluster_5: 2 links

### SAMPLES
#### Data Tokenization (523w)
Data tokenization transforms data ownership into tradeable assets...
```

### AI-Synthesized Report (from /datacortex-insights)
```markdown
# Datacortex Cluster Insights

## Cluster 3: Data Asset Tokenization
Size: 47 documents | Density: 0.08 | Avg Centrality: 0.012

### Summary
This cluster focuses on tokenizing data as Real World Assets (RWAs)
using blockchain infrastructure...

### Key Themes
- Data tokenization mechanisms
- Decentralized storage solutions
- API design patterns

### Patterns
Strong focus on technical implementation with moderate internal
connectivity. Hub documents cover infrastructure (Swarm) and
financial instruments (tokenization).

### Connections
- Cluster 1 (5 links): Legal/compliance framework
- Cluster 5 (2 links): Market research

### Gaps & Opportunities
Missing connections to user experience cluster. Need bridge documents
connecting technical implementation to end-user workflows.

### Recommendations
1. Create overview document linking tokenization tech to UX
2. Expand API documentation with usage examples
3. Link storage docs to data provenance requirements
```

## Architecture Decisions

### 1. Reuse Existing Infrastructure
- Uses `zettel_db` for database access
- Leverages existing graph builder and clustering
- Follows established patterns from Phases 1-3

### 2. Compact Output Format
- TSV/markdown hybrid for machine + human readability
- Consistent header format for parsing
- Hierarchical sections with clear delimiters

### 3. Two-Tier Analysis
- **Tier 1**: Automated cluster statistics and metrics
- **Tier 2**: AI-assisted insight synthesis and recommendations
- Separation allows fast iteration on AI prompting

### 4. Content Sampling
- First 500 chars of top 5 documents
- Breaks at sentence/word boundaries
- Balances context with output size

## Performance Considerations

### Optimization Strategies
1. **Content Loading**: Only loads content for top 5 samples per cluster
2. **Cluster Filtering**: Skips clusters smaller than 3 nodes
3. **Connection Limiting**: Top 10 connections per cluster
4. **Database**: Single connection reused across analysis

### Expected Performance
- **Small space** (100-200 docs): < 5 seconds
- **Medium space** (500-1000 docs): 10-20 seconds
- **Large space** (2000+ docs): 30-60 seconds

Most time spent in:
1. Graph building (reused from previous phases)
2. Louvain clustering (reused, cached)
3. Content loading from database

## Extension Points

### Future Enhancements

1. **Temporal Analysis**
   - Track cluster evolution over time
   - Identify growing/shrinking clusters
   - Detect emerging topics

2. **Semantic Analysis**
   - Use embeddings for cluster naming
   - Suggest cluster merges/splits
   - Identify semantic drift

3. **Interactive Reports**
   - HTML/React output format
   - Drill-down views
   - Visual cluster maps

4. **Automated Actions**
   - Auto-create bridge documents
   - Suggest specific link targets
   - Generate stub documents for gaps

## Testing

Run tests:
```bash
pytest tests/test_insights.py -v
```

Test coverage:
- Data model creation
- Statistics computation
- Hub extraction
- Tag frequency
- Cluster connections
- Formatting
- Summary generation

## Dependencies

Required packages (already in `pyproject.toml`):
- `networkx>=3.2`
- `scipy>=1.11.0`
- `python-louvain>=0.16`
- `pydantic>=2.5.0`
- `click>=8.1.0`

## Files Created

### Source Code
1. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/insights/__init__.py`
2. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/insights/analyzer.py`
3. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/insights/formatter.py`

### CLI Integration
4. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/src/datacortex/cli/commands.py` (modified)

### Datacore Command
5. `/Users/tex/repos/datacore/.datacore/commands/datacortex-insights.md`

### Tests
6. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/tests/test_insights.py`

### Documentation
7. `/Users/tex/repos/datacore/1-datafund/2-projects/datacortex/docs/phase4-insights.md` (this file)

## Next Steps

After implementation:

1. **Install/Update Package**
   ```bash
   cd /Users/tex/repos/datacore/1-datafund/2-projects/datacortex
   pip install -e .
   ```

2. **Test CLI**
   ```bash
   datacortex insights --help
   datacortex insights --top 3
   ```

3. **Test Datacore Integration**
   ```bash
   # In Claude Code
   /datacortex-insights
   ```

4. **Review Output**
   - Check `/tmp/datacortex_insights_*.txt` files
   - Verify cluster analysis is meaningful
   - Refine synthesis prompts if needed

5. **Iterate on AI Synthesis**
   - Adjust `/datacortex-insights.md` command
   - Improve synthesis guidelines
   - Add domain-specific patterns

## Conclusion

Phase 4 completes the Datacortex AI Extensions pipeline:
- **Phase 1**: Embeddings and similarity
- **Phase 2**: Daily digest generation
- **Phase 3**: Knowledge gap detection
- **Phase 4**: Insight extraction (this phase)

The system now provides comprehensive knowledge graph analysis:
1. **Embeddings** - Semantic understanding
2. **Digest** - Daily maintenance suggestions
3. **Gaps** - Missing connections
4. **Insights** - Strategic patterns and themes

All phases integrate with Datacore's slash command system for seamless AI-assisted knowledge work.
