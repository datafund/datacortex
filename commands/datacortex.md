# /datacortex

Knowledge graph visualization for your Datacore installation.

## Usage

```
/datacortex [subcommand]
```

## Subcommands

| Command | Description |
|---------|-------------|
| `serve` | Start web UI at http://localhost:8765 |
| `stats` | Show graph statistics (nodes, edges, clusters) |
| `generate` | Output graph JSON to stdout |
| `pulse generate` | Create temporal snapshot |
| `pulse list` | List available snapshots |
| `pulse diff <date1> <date2>` | Compare two snapshots |
| `orphans` | Find unlinked documents |

## Examples

```bash
# Start the visualization server
/datacortex serve

# View statistics about your knowledge graph
/datacortex stats

# Create a snapshot of current graph state
/datacortex pulse generate

# Find notes with no incoming or outgoing links
/datacortex orphans
```

## Requirements

- Python 3.10+
- Datacortex module installed (`pip install -e .`)
- Datacore knowledge database populated

## What It Shows

The visualization displays:
- **Nodes**: Documents in your knowledge base (journals, pages, zettels)
- **Edges**: Wiki-links between documents (`[[Page Name]]`)
- **Metrics**: Degree centrality, PageRank, community clustering
- **Filtering**: By space, node type, connection count

## Installation

If not already installed:

```bash
cd ~/Data/1-datafund/2-projects/datacortex
pip install -e .
```

Or symlink as a module:

```bash
cd ~/Data/.datacore/modules
ln -s ~/Data/1-datafund/2-projects/datacortex datacortex
```
