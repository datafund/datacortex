# Daily Digest Usage Guide

## Quick Start

### From Claude Code

```
/datacortex-digest
```

This will automatically:
1. Generate the digest
2. Parse the results
3. Provide natural language recommendations

### From Command Line

```bash
# Basic usage (all spaces)
datacortex digest

# Single space
datacortex digest --space datafund

# Custom threshold and limits
datacortex digest --threshold 0.8 --top-n 30 --min-words 100
```

## First Time Setup

Before running the digest, you need to compute embeddings:

```bash
# Compute embeddings for all spaces (one-time or when content changes)
datacortex embed

# Compute for specific space
datacortex embed --space datafund

# Force recompute all
datacortex embed --force
```

## Understanding the Output

### Similar Pairs Section

```
# SIMILAR_PAIRS threshold=0.75 count=20
# format: doc_a | doc_b | similarity | recency | centrality | score
Data Tokenization | Real World Assets | 0.87 | 0.9 | 0.04 | 0.73
```

**Columns:**
- **doc_a, doc_b**: Document titles that should be linked
- **similarity**: Cosine similarity of embeddings (0-1, higher = more similar)
- **recency**: How recently updated (0-1, higher = more recent)
- **centrality**: Average graph connectivity (0-1, higher = more connected)
- **score**: Final weighted score (higher = better suggestion)

**Interpretation:**
- **0.80-1.00**: Very strong connection, definitely link
- **0.75-0.80**: Strong connection, should probably link
- **0.70-0.75**: Moderate connection, consider linking
- **<0.70**: Weak connection, only link if contextually relevant

### Orphans Section

```
# ORPHANS count=10
# format: title | words | created_at | path
Autonomous AI Legal Entity | 278w | 2025-12-09 | 3-knowledge/pages/ai-legal.md
```

**Columns:**
- **title**: Document title
- **words**: Word count (higher = more substantial)
- **created_at**: Creation date
- **path**: File path

**Interpretation:**
- High word count + recent = Important document that needs integration
- High word count + old = Possibly forgotten content
- Low word count + old = May be a stub or placeholder

## Workflow

### Daily Routine

1. **Morning**: Run digest to see new connections
   ```bash
   datacortex digest --threshold 0.8
   ```

2. **Review**: Check top 10-15 suggestions
   - Add obvious links immediately
   - Flag questionable suggestions for review

3. **Weekly**: Process orphans
   - Review orphans with >200 words
   - Add links from related documents
   - Update or archive low-value orphans

### Integration with Knowledge Management

The digest helps maintain knowledge graph health by:

1. **Discovering Hidden Connections**
   - Semantic similarity reveals non-obvious links
   - Helps build comprehensive concept networks

2. **Preventing Information Silos**
   - Identifies isolated documents
   - Suggests integration points

3. **Guiding Content Development**
   - High-similarity pairs suggest related topics
   - Orphans highlight gaps in linking structure

## Tuning Parameters

### Threshold (`-t, --threshold`)

Controls minimum similarity for suggestions:

- **0.85-1.00**: Very conservative, only strongest matches
- **0.75-0.85**: Balanced (default 0.75)
- **0.60-0.75**: Exploratory, finds weaker connections
- **<0.60**: Too broad, likely false positives

**When to adjust:**
- Raise threshold: Too many weak suggestions
- Lower threshold: Missing obvious connections

### Top N (`-n, --top-n`)

Number of suggestions to return (default: 20):

- **10-20**: Daily review (default 20)
- **30-50**: Weekly deep dive
- **50+**: Initial knowledge graph audit

### Min Words (`-w, --min-words`)

Minimum word count for orphans (default: 50):

- **100+**: Substantial documents only
- **50**: Balanced (default)
- **20-50**: Include smaller notes
- **<20**: Include stubs (not recommended)

## Common Scenarios

### Scenario 1: Initial Knowledge Graph Audit

```bash
# Find all strong connections
datacortex digest --threshold 0.85 --top-n 100 --min-words 100 > initial_audit.txt
```

Review and add the top 50 links to build foundational structure.

### Scenario 2: Daily Maintenance

```bash
# Quick daily check
datacortex digest --threshold 0.8 --top-n 10
```

Add 3-5 top suggestions each day.

### Scenario 3: Orphan Cleanup

```bash
# Focus on substantial orphans
datacortex digest --threshold 0.9 --top-n 5 --min-words 200
```

Review orphans section, add links or archive.

### Scenario 4: Topic Deep Dive

```bash
# Find all connections in specific space
datacortex digest --space research --threshold 0.70 --top-n 50
```

Use for focused topic development.

## Troubleshooting

### No suggestions returned

**Possible causes:**
1. Threshold too high - try lowering to 0.70
2. Documents already well-linked - good problem to have!
3. Embeddings not computed - run `datacortex embed` first
4. Small document set - need at least 10-20 documents

### Too many weak suggestions

**Solutions:**
1. Raise threshold to 0.80 or 0.85
2. Reduce top-n to focus on best suggestions
3. Review and improve document content quality

### Embeddings out of date

If documents have changed significantly:

```bash
# Recompute embeddings for changed documents
datacortex embed

# Force recompute all (slower)
datacortex embed --force
```

### Wrong DATA_ROOT detected

If running from subdirectory, set explicitly:

```bash
export DATACORE_ROOT=/Users/tex/repos/datacore
datacortex digest
```

## Advanced Usage

### Scripting

Capture output for programmatic processing:

```bash
# Save to file
datacortex digest > digest_$(date +%Y%m%d).txt

# Extract just similar pairs
datacortex digest | awk '/^# SIMILAR_PAIRS/,/^# ORPHANS/'

# Count suggestions
datacortex digest | grep -c "^[^#]"
```

### Monitoring Trends

Track digest over time to measure knowledge graph health:

```bash
# Weekly digest archive
mkdir -p digests/$(date +%Y-%m)
datacortex digest > digests/$(date +%Y-%m)/digest_$(date +%Y%m%d).txt

# Compare orphan counts over time
grep "^# ORPHANS count=" digests/*/*.txt
```

### Integration with Obsidian

Use digest output to guide Obsidian linking:

1. Run digest: `datacortex digest --threshold 0.8 --top-n 20`
2. For each suggestion, open both documents in Obsidian
3. Add wiki-link in appropriate context
4. Re-run digest to see progress

## Best Practices

1. **Run Regularly**: Daily or weekly for best results
2. **Start Conservative**: Use higher threshold initially, lower as needed
3. **Act on Top Suggestions**: Focus on highest-scoring pairs
4. **Review Context**: Don't add links blindly - read both documents
5. **Update Embeddings**: Re-embed after major content changes
6. **Track Progress**: Monitor orphan count over time
7. **Batch Process**: Set aside dedicated time for linking sessions

## Performance

### Timing

On a typical knowledge base (1000-2000 documents):

- **Embedding computation**: 5-10 minutes (first time)
- **Embedding updates**: 1-2 minutes (incremental)
- **Digest generation**: 5-15 seconds
- **Digest review**: 10-20 minutes (manual)

### Optimization Tips

1. **Use cache**: Embeddings are cached, don't use `--force` unless needed
2. **Limit scope**: Use `--space` for focused analysis
3. **Batch embeddings**: Run `embed` once, then `digest` multiple times
4. **Schedule off-hours**: Run embedding computation overnight

## Support

For issues or questions:
1. Check this guide first
2. Review PHASE2_DIGEST.md for technical details
3. Check datacortex documentation
4. Open issue in datacore repo
