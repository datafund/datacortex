# Datacortex AI Extensions - Complete Integration Example

## Overview

This document shows how all 4 phases of Datacortex AI Extensions work together to provide comprehensive knowledge graph analysis.

## The Four Phases

| Phase | Module | Purpose | Output |
|-------|--------|---------|--------|
| 1 | `ai.embeddings` | Semantic understanding | Vector embeddings |
| 2 | `digest` | Daily maintenance | Link suggestions |
| 3 | `gaps` | Missing connections | Knowledge gaps |
| 4 | `insights` | Strategic patterns | Cluster analysis |

## Complete Workflow

### Morning Routine: Knowledge Maintenance

```bash
# 1. Generate daily digest (Phase 2)
datacortex digest --top-n 20

# Output: Link suggestions for orphaned documents
# - Recently created docs needing links
# - High-quality unlinked content
# - Semantic similarity matches
```

**Use case**: Spend 10 minutes each morning linking new documents to existing knowledge.

### Weekly Review: Gap Analysis

```bash
# 2. Detect knowledge gaps (Phase 3)
datacortex gaps --min-score 0.3

# Output: Semantically similar but unconnected clusters
# - Cluster pairs that should be linked
# - Shared tags indicating common themes
# - Boundary nodes for potential bridges
```

**Use case**: Weekly identify missing connections between topic areas.

### Monthly Strategic: Insights & Planning

```bash
# 3. Extract cluster insights (Phase 4)
datacortex insights --top 10

# Output: Strategic analysis of knowledge clusters
# - Hub documents (most central)
# - Theme identification
# - Cluster connections
# - Content samples
```

**Use case**: Monthly strategic review of knowledge organization.

### Datacore Integration

```bash
# All-in-one AI-assisted workflow
/datacortex-insights

# Claude synthesizes:
# 1. Cluster names and summaries
# 2. Key themes and patterns
# 3. Gap analysis
# 4. Actionable recommendations
```

## Example Session

### 1. Setup (One-time)

```bash
cd /Users/tex/repos/datacore/1-datafund/2-projects/datacortex

# Install datacortex
pip install -e .

# Compute embeddings (Phase 1)
datacortex embed
```

### 2. Daily Digest Workflow

```bash
# Generate digest
datacortex digest --space datafund --top-n 15 > /tmp/digest.txt

# Review output
cat /tmp/digest.txt
```

**Example output**:
```
# LINK_SUGGESTIONS similarity_threshold=0.75 orphan_count=8

## RECENTLY_CREATED created_within=7_days

### Doc: "Verity Token Economics"
path: 1-datafund/3-knowledge/pages/verity-tokenomics.md
words: 523
created: 2025-12-03
suggestions:
  Data Tokenization Overview | 0.89 | 1-datafund/3-knowledge/zettel/data-tokenization.md
  RWA Compliance Framework | 0.82 | 1-datafund/3-knowledge/pages/rwa-compliance.md
  Token Distribution Model | 0.78 | 1-datafund/3-knowledge/literature/token-economics.md
```

**Action**: Add wiki-links to the 3 suggested documents.

### 3. Weekly Gap Detection

```bash
# Detect gaps
datacortex gaps --space datafund > /tmp/gaps.txt

# Review
cat /tmp/gaps.txt
```

**Example output**:
```
# KNOWLEDGE_GAPS gap_count=3 cluster_count=12

## GAP id=1 gap_score=0.62
cluster_a: 3 (size=47) Technical Implementation
cluster_b: 7 (size=23) User Experience
semantic_similarity: 0.68
link_density: 0.06
cross_links: 2

### SHARED_TAGS
verity, platform, workflow

### BOUNDARY_NODES
API Integration Guide
User Onboarding Flow

### RECOMMENDATIONS
- Create bridge document connecting technical architecture to UX flows
- Link API docs to user workflows
- Add system diagrams showing end-to-end user journey
```

**Action**: Create "Verity Platform Overview" document linking tech and UX.

### 4. Monthly Insights Review

```bash
# Extract insights
datacortex insights --top 5 > /tmp/insights.txt

# AI synthesis
/datacortex-insights
```

**Example AI synthesis**:

```markdown
# Datacortex Cluster Insights - December 2025

## Cluster 3: Data Asset Tokenization (47 docs)
Density: 0.08 | Avg Centrality: 0.012

### Summary
Technical infrastructure for tokenizing data as RWAs. Strong coverage
of blockchain mechanics and storage, with emerging focus on compliance
integration.

### Key Themes
- ERC-3643 token standard implementation
- Swarm decentralized storage
- SPV structure for asset ownership
- Data provenance and immutability

### Patterns
High-quality technical documentation with good internal density.
Hub documents are well-maintained specs and architecture docs.
Recent additions focus on compliance layer.

### Connections
- Cluster 1 (5 links): Legal/Compliance - strong bridge via RWA regs
- Cluster 7 (2 links): User Experience - weak, needs strengthening
- Cluster 9 (3 links): Market Research - competitive analysis

### Gaps & Opportunities
Missing: Operational playbooks connecting tech specs to deployment.
Need: Security audit documentation, disaster recovery procedures.
Opportunity: Link technical capabilities to market positioning.

### Recommendations
1. **Create**: "Verity Deployment Playbook" (tech → ops)
2. **Expand**: Security documentation with audit results
3. **Link**: Token mechanics to competitive advantages
4. **Bridge**: Technical architecture to user journeys
5. **Document**: Data migration and recovery procedures
```

**Actions**:
- Create deployment playbook
- Commission security audit
- Document recovery procedures
- Link tech capabilities to market position

## Python API Integration

### Custom Analysis Pipeline

```python
from datacortex.insights.analyzer import analyze_clusters
from datacortex.gaps.detector import detect_gaps
from datacortex.digest.generator import generate_digest

# Full analysis pipeline
spaces = ['datafund']

# 1. Cluster insights
insights = analyze_clusters(spaces)
print(f"Found {len(insights.clusters)} clusters")

# 2. Knowledge gaps
gaps = detect_gaps(spaces, min_gap_score=0.3)
print(f"Detected {len(gaps.gaps)} knowledge gaps")

# 3. Daily maintenance
digest = generate_digest(spaces, threshold=0.75, top_n=20)
print(f"Generated {len(digest.suggestions)} link suggestions")

# Custom reporting
for cluster in insights.clusters[:3]:
    print(f"\nCluster {cluster.cluster_id}: {cluster.size} docs")
    print(f"  Top hub: {cluster.hubs[0]['title']}")
    print(f"  Density: {cluster.stats['density']}")

    # Find gaps involving this cluster
    cluster_gaps = [g for g in gaps.gaps
                    if g.cluster_a == cluster.cluster_id
                    or g.cluster_b == cluster.cluster_id]
    print(f"  Gaps: {len(cluster_gaps)}")
```

### Automated Reports

```python
from datetime import datetime
from pathlib import Path

def generate_monthly_report(spaces: list[str]):
    """Generate comprehensive monthly knowledge report."""

    # Analyze
    insights = analyze_clusters(spaces)
    gaps = detect_gaps(spaces)
    digest = generate_digest(spaces, top_n=50)

    # Format
    report = []
    report.append(f"# Monthly Knowledge Report - {datetime.now().strftime('%B %Y')}")
    report.append("")
    report.append(f"## Overview")
    report.append(f"- Total documents: {insights.total_docs}")
    report.append(f"- Total clusters: {insights.total_clusters}")
    report.append(f"- Knowledge gaps: {len(gaps.gaps)}")
    report.append(f"- Link suggestions: {len(digest.suggestions)}")
    report.append("")

    report.append("## Top Clusters")
    for i, cluster in enumerate(insights.clusters[:10], 1):
        report.append(f"### {i}. Cluster {cluster.cluster_id} ({cluster.size} docs)")
        report.append(f"Top hub: {cluster.hubs[0]['title']}")
        top_tags = ', '.join(t for t, _ in cluster.tag_freq[:5])
        report.append(f"Tags: {top_tags}")
        report.append("")

    report.append("## Priority Gaps")
    for i, gap in enumerate(gaps.gaps[:5], 1):
        report.append(f"### {i}. Gap Score {gap.gap_score:.2f}")
        report.append(f"Between clusters {gap.cluster_a} and {gap.cluster_b}")
        report.append(f"Semantic similarity: {gap.semantic_similarity:.2f}")
        report.append(f"Link density: {gap.link_density:.3f}")
        report.append("")

    # Save
    output = Path(f"/tmp/monthly_report_{datetime.now().strftime('%Y%m')}.md")
    output.write_text('\n'.join(report))
    return output

# Run
report_path = generate_monthly_report(['datafund', 'personal'])
print(f"Report saved: {report_path}")
```

## Integration with Other Tools

### Obsidian Integration

```bash
# Generate insights
datacortex insights > ~/Obsidian/Reports/datacortex-insights.md

# Add to daily note template
echo "![[datacortex-insights.md]]" >> ~/Obsidian/Daily/$(date +%Y-%m-%d).md
```

### GitHub Actions (CI/CD)

```yaml
name: Weekly Knowledge Analysis

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9am

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install Datacortex
        run: |
          cd datacortex
          pip install -e .

      - name: Generate Insights
        run: |
          datacortex insights --top 10 > weekly-insights.md
          datacortex gaps > weekly-gaps.md

      - name: Create Issue
        uses: peter-evans/create-issue-from-file@v4
        with:
          title: Weekly Knowledge Analysis
          content-filepath: weekly-insights.md
          labels: knowledge-analysis, weekly
```

### Slack Integration

```python
import requests
from datacortex.insights.analyzer import analyze_clusters

def post_to_slack(webhook_url: str, message: str):
    """Post message to Slack."""
    requests.post(webhook_url, json={'text': message})

# Weekly insights to Slack
insights = analyze_clusters(['datafund'])

message = f"""
📊 Weekly Knowledge Analysis

*Clusters*: {len(insights.clusters)}
*Total Docs*: {insights.total_docs}

*Top 3 Clusters*:
"""

for cluster in insights.clusters[:3]:
    top_hub = cluster.hubs[0]['title'] if cluster.hubs else 'N/A'
    message += f"\n• Cluster {cluster.cluster_id}: {cluster.size} docs - {top_hub}"

post_to_slack(SLACK_WEBHOOK, message)
```

## Best Practices

### Daily
- ✓ Review digest for new link suggestions
- ✓ Process orphaned documents
- ✓ Link new captures to existing knowledge

### Weekly
- ✓ Review knowledge gaps
- ✓ Create bridge documents
- ✓ Tag and categorize new content

### Monthly
- ✓ Run full insights analysis
- ✓ Strategic review with AI synthesis
- ✓ Plan knowledge organization improvements
- ✓ Identify emerging themes and topics

### Quarterly
- ✓ Comprehensive cluster analysis
- ✓ Reorganize folder structure if needed
- ✓ Archive stale content
- ✓ Update index pages

## Conclusion

The Datacortex AI Extensions provide a complete toolkit for knowledge graph analysis:

1. **Embeddings** (Phase 1) - Foundation for semantic analysis
2. **Digest** (Phase 2) - Daily maintenance and link suggestions
3. **Gaps** (Phase 3) - Identify missing connections
4. **Insights** (Phase 4) - Strategic cluster analysis

Together, these tools enable:
- Proactive knowledge maintenance
- Strategic organization improvements
- Automated insight generation
- AI-assisted knowledge work

All integrated with Datacore's slash command system for seamless AI collaboration.
