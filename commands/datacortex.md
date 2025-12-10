# /datacortex

Knowledge graph visualization for your Datacore installation.

## Workflow

### Step 1: Understand Intent

If user invoked `/datacortex` with no clear intent, ask:

"What would you like to do with your knowledge graph?"

1. **Explore** - Open interactive visualization in browser
2. **Stats** - Show graph statistics (nodes, edges, clusters)
3. **Find orphans** - List unlinked documents
4. **Take snapshot** - Create temporal pulse for tracking changes

If intent is clear from context (e.g., "show me the datafund graph", "find orphan notes"), proceed directly to execution.

### Step 2: Space Selection

If action requires a space and user hasn't specified one:

Discover available spaces:
```bash
ls -d ~/Data/[0-9]-*/
```

Ask: "Which space would you like to visualize?"
- All spaces (combined view)
- [list discovered spaces]

If `settings.datacortex.default_space` is set, use that without asking.

### Step 3: Execute

**Explore (open visualization):**
1. Check if datacortex is installed: `which datacortex`
2. If not found, tell user: "Datacortex CLI not installed. Run: `cd ~/Data/1-datafund/2-projects/datacortex && pip install -e .`"
3. Check if server already running: `lsof -i :8765`
4. If not running, start in background: `datacortex serve &`
5. Wait briefly for server startup
6. Open browser: `open http://localhost:8765`
7. Tell user: "Graph visualization opened at http://localhost:8765"

**Stats:**
1. Run: `datacortex stats`
2. Format output as readable table
3. Highlight key metrics: total nodes, edges, clusters, orphan count

**Find orphans:**
1. Run: `datacortex orphans`
2. Display list of unlinked documents
3. Offer: "Would you like me to open any of these in your editor?"

**Take snapshot:**
1. Run: `datacortex pulse generate`
2. Confirm: "Snapshot created for [today's date]. Use `datacortex pulse list` to see all snapshots."

### Step 4: Follow-up

After completing the action, offer relevant next steps:

After **Explore**: "The graph is now open. Would you like to see stats or find orphans?"
After **Stats**: "Would you like to explore the graph visually or find orphan notes?"
After **Orphans**: "Would you like to explore the graph to see how these relate?"
After **Snapshot**: "Would you like to compare with a previous snapshot?"

## Auto-Serve Mode

Check `settings.datacortex.auto_serve` (from settings.yaml or settings.local.yaml):

If `true` and user says `/datacortex` with explore-like intent:
- Skip the menu
- Start server immediately
- Open browser automatically
- Say: "Opening your knowledge graph..."

## Settings Reference

User can configure in `~/.datacore/settings.local.yaml`:

```yaml
datacortex:
  auto_serve: true        # Skip menu, open graph immediately
  default_space: datafund # Don't ask for space selection
  open_browser: true      # Auto-open browser (default)
  port: 8765              # Server port (default)
```

## Error Handling

**Command not found:**
```
Datacortex CLI is not installed.

Install with:
  cd ~/Data/1-datafund/2-projects/datacortex
  pip install -e .

Or run the install script:
  ./install.sh
```

**Port in use:**
```
Port 8765 is already in use.

Either:
1. The server is already running - open http://localhost:8765
2. Another process is using the port - check with: lsof -i :8765
```

**No knowledge database:**
```
Knowledge database not found at ~/.datacore/knowledge.db

Run the zettel processor first to index your notes:
  python ~/.datacore/lib/zettel_processor.py
```

## Your Boundaries

**YOU CAN:**
- Start the datacortex server
- Open browser to visualization
- Run stats, orphans, and pulse commands
- Help user explore their knowledge graph
- Read settings from settings.yaml

**YOU CANNOT:**
- Modify the knowledge database
- Delete or edit notes
- Change graph structure directly

**YOU MUST:**
- Ask for clarification if intent is unclear
- Provide helpful error messages with solutions
- Respect user's settings preferences
