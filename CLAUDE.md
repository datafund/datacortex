# Datacortex

Knowledge graph visualization for Datacore.

## Overview

Datacortex indexes Datacore knowledge bases (markdown files, org-mode tasks) and generates interactive graph visualizations showing how documents are connected through wiki-links and tags.

## Structure

```
src/datacortex/
├── core/           # Models, config, database wrapper
├── indexer/        # File scanning, graph building from zettel_db
├── metrics/        # NetworkX centrality, Louvain clustering
├── pulse/          # Temporal snapshots
├── api/            # FastAPI backend
└── cli/            # Click CLI commands

frontend/           # D3.js force-directed graph visualization
config/             # YAML configuration
pulses/             # Generated snapshots (gitignored)
```

## Key Patterns

### Reuses Datacore Infrastructure

This project reads from the existing Datacore knowledge database:
- `~/.datacore/lib/zettel_db.py` - Database connection and schema
- `~/.datacore/lib/zettel_processor.py` - Link extraction patterns

Import pattern:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Data" / ".datacore" / "lib"))
from zettel_db import get_connection
```

### Data Models

- **Node**: Document with metrics (degree, centrality, cluster)
- **Edge**: Wiki-link between documents
- **Graph**: Collection of nodes + edges with stats
- **Pulse**: Timestamped graph snapshot

### Configuration

Base config in `config/datacortex.yaml`, user overrides in `config/datacortex.local.yaml` (gitignored).

## CLI Commands

```bash
datacortex generate     # Output graph JSON to stdout
datacortex stats        # Show graph statistics
datacortex pulse generate/list/diff
datacortex serve        # Start FastAPI server on :8765
datacortex orphans      # Find unlinked documents
```

## API Endpoints

- `GET /api/graph` - Current graph (filterable)
- `GET /api/pulse` - List pulses
- `GET /api/pulse/{id}` - Get specific pulse
- `POST /api/pulse/generate` - Create new pulse
- `GET /api/nodes/{id}` - Node details
- `GET /api/nodes/search?q=` - Search nodes

## Frontend

D3.js force-directed graph with:
- Zoom/pan navigation
- Node click for details
- Filter controls (space, type, degree)
- Timeline slider for pulse history
