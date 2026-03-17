---
summary: "Knowledge graph — semantic search, graph statistics, link analysis, and visualization"
triggers: ["knowledge graph", "search for", "find backlinks", "orphan documents", "graph stats"]
context: on_match
---

# Datacortex Module

## Purpose

Indexes Datacore knowledge bases (markdown, org-mode) and provides semantic search, link analysis, and interactive graph visualization. Shows how documents connect through wiki-links and tags. Includes temporal pulse snapshots for tracking knowledge growth over time.

## Quick Start
> Say "knowledge graph" to launch the interactive graph explorer.

## How It Works

### Indexing & Search
Reads from the shared zettel database (`zettel_db.py`). Provides full-text search, backlink discovery, orphan detection, and task queries across all indexed content.

### Graph Visualization
D3.js force-directed graph with zoom/pan, node filtering (space, type, degree), timeline slider for pulse history, and minimap. Served via FastAPI on port 8765.

### Pulse Snapshots
Timestamped graph snapshots for tracking how the knowledge base evolves. Generate, list, and diff pulses over time.

## Agents & Commands

| Name | Type | When to use |
|------|------|-------------|
| `/datacortex` | command | Interactive graph exploration with web UI |
| `datacortex` | skill | Knowledge graph queries and visualization |
| `search` | tool | Full-text search across indexed content |
| `backlinks` | tool | Find all documents linking to a file |
| `orphans` | tool | Find unlinked documents |
| `stats` | tool | Graph and database statistics |
| `tasks` | tool | Query tasks from indexed org files |
| `patterns` | tool | Query learning patterns |
| `find_by_skill` | tool | Find agents by skill keyword |

## Key Paths

| Path | Purpose |
|------|---------|
| `src/datacortex/` | Python package (core, indexer, metrics, pulse, api, cli) |
| `frontend/` | D3.js graph visualization |
| `config/datacortex.yaml` | Base configuration |
| `config/datacortex.local.yaml` | User overrides (gitignored) |
| `pulses/` | Generated snapshots (gitignored) |

## Setup

```
cd /path/to/datacortex && pip install -e .
```

Reuses `~/.datacore/lib/zettel_db.py` and `zettel_processor.py` -- no separate database setup needed.

---

*This file covers structure, capability, and stable configuration. Learned behavior, user corrections, and operational preferences live as engrams -- call `datacore.recall` for those.*
