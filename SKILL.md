---
name: Datacortex for Datacore
description: "Knowledge graph — semantic search, graph statistics, link analysis, and visualization"
version: 0.1.0
author: datacore-one
license: MIT
tags: [knowledge-graph, search, visualization, zettelkasten, links]
x-datacore:
  module: datacortex
  tools: 6
  skills: 1
  agents: 0
  commands: 1
  workflows: 0
  engram_count: 0
  injection_policy: on_match
  match_terms: [graph, knowledge, search, links, orphans, backlinks, zettel, datacortex]
---

# Datacortex for Datacore

Knowledge graph engine — indexes all Datacore content into a SQLite database
with semantic search, link analysis, graph statistics, and D3.js visualization.

## What This Module Provides

**Tools** (MCP):
- `datacore.datacortex.search` — Full-text search across all indexed content
- `datacore.datacortex.stats` — Graph statistics (node counts, link density, clusters)
- `datacore.datacortex.backlinks` — Find all documents linking to a given file
- `datacore.datacortex.orphans` — Find unlinked documents (no incoming/outgoing links)
- `datacore.datacortex.tasks` — Query tasks from indexed org files
- `datacore.datacortex.patterns` — Query learning patterns from indexed data

**Skills**:
- Knowledge graph exploration and visualization

**Commands**:
- `/datacortex` — Interactive graph exploration with web UI

## When to Use

Triggers: graph, knowledge, search, links, orphans, backlinks, zettel, datacortex.
