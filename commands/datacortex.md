# /datacortex

Knowledge graph visualization for your Datacore installation.

## Usage

```
/datacortex [subcommand] [args]
```

## Implementation

This command wraps the `datacortex` CLI. Run the user's subcommand:

```bash
datacortex $ARGUMENTS
```

Where `$ARGUMENTS` is everything after `/datacortex`.

**Examples:**
- `/datacortex serve` → `datacortex serve`
- `/datacortex stats` → `datacortex stats`
- `/datacortex pulse generate` → `datacortex pulse generate`

If the `datacortex` command is not found, inform the user to install it:
```bash
cd ~/Data/1-datafund/2-projects/datacortex && pip install -e .
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

## What It Shows

The visualization displays:
- **Nodes**: Documents in your knowledge base (journals, pages, zettels)
- **Edges**: Wiki-links between documents (`[[Page Name]]`)
- **Metrics**: Degree centrality, PageRank, community clustering
- **Filtering**: By space, node type, connection count

## Installation

### 1. Install Python package (required)

```bash
cd ~/Data/1-datafund/2-projects/datacortex
pip install -e .
```

### 2. Install slash command (to enable /datacortex)

```bash
# Symlink command to Claude commands directory
mkdir -p ~/.claude/commands
ln -s ~/Data/1-datafund/2-projects/datacortex/commands/datacortex.md ~/.claude/commands/datacortex.md
```

### 3. Register as module (optional, for discovery)

```bash
cd ~/Data/.datacore/modules
ln -s ~/Data/1-datafund/2-projects/datacortex datacortex
```

## Requirements

- Python 3.10+
- Datacore knowledge database populated (`~/.datacore/knowledge.db`)
