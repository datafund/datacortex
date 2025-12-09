# Datacortex

Knowledge graph visualization for [Datacore](https://github.com/datafund/datacore) with temporal pulse tracking.

## Features

- **Graph Visualization**: Interactive D3.js force-directed graph of your knowledge base
- **Temporal Pulses**: Snapshot graph state over time to track evolution
- **Multi-Space**: Configure which Datacore spaces to include
- **Metrics**: Degree centrality, PageRank, community clustering
- **Search & Filter**: Find nodes by title, filter by type/space

## Installation

```bash
cd ~/Data/1-datafund/2-projects/datacortex
pip install -e .
```

## Usage

### CLI Commands

```bash
# Generate graph JSON
datacortex generate --spaces personal,datafund

# Show statistics
datacortex stats

# Generate a pulse snapshot
datacortex pulse generate

# List available pulses
datacortex pulse list

# Compare two pulses
datacortex pulse diff 2025-01-01 2025-01-15

# Start web server
datacortex serve
```

### Web Interface

```bash
datacortex serve
# Open http://localhost:8765
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
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Architecture

```
datacortex/
├── src/datacortex/
│   ├── core/           # Models, config, database
│   ├── indexer/        # File scanning, graph building
│   ├── metrics/        # Centrality, clustering
│   ├── pulse/          # Snapshot generation
│   ├── api/            # FastAPI backend
│   └── cli/            # Click commands
├── frontend/           # D3.js visualization
├── config/             # YAML configuration
└── pulses/             # Generated snapshots
```

## License

MIT
