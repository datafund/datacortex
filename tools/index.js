// Datacortex Module — MCP Tool Definitions
// Wraps Python query_library.py via subprocess for graph queries.
// Plain JS (ESM) for direct dynamic import by the MCP server.

import { z } from 'zod'
import { execFile } from 'child_process'
import { promisify } from 'util'
import * as path from 'path'
import * as fs from 'fs'

const execFileAsync = promisify(execFile)

// --- Helpers ---

function findQueryLibrary(basePath) {
  const libPath = path.join(basePath, '.datacore', 'lib', 'query_library.py')
  if (fs.existsSync(libPath)) return libPath
  return null
}

async function runQuery(basePath, queryType, extraArgs = {}) {
  const scriptPath = findQueryLibrary(basePath)
  if (!scriptPath) {
    return { error: 'query_library.py not found in .datacore/lib/' }
  }

  const args = [scriptPath, queryType, '--json']

  if (extraArgs.space) {
    args.push('--space', extraArgs.space)
  }
  if (extraArgs.query) {
    args.push('--query', extraArgs.query)
  }
  if (extraArgs.days) {
    args.push('--days', String(extraArgs.days))
  }

  try {
    const { stdout, stderr } = await execFileAsync('python3', args, {
      cwd: basePath,
      timeout: 30000,
      env: { ...process.env, PYTHONPATH: path.join(basePath, '.datacore', 'lib') },
    })
    return JSON.parse(stdout)
  } catch (err) {
    return { error: `Query failed: ${err.message}`, stderr: err.stderr?.slice(0, 500) }
  }
}

// --- Tools ---

export const tools = [
  {
    name: 'search',
    description: 'Full-text search across all indexed Datacore content (files, tasks, notes)',
    inputSchema: z.object({
      query: z.string().describe('Search query (supports FTS5 syntax)'),
      space: z.string().optional().describe('Filter by space name'),
    }),
    handler: async (args, ctx) => {
      return runQuery(ctx.storage.basePath, 'search', {
        query: args.query,
        space: args.space,
      })
    },
  },

  {
    name: 'stats',
    description: 'Get database and graph statistics (table row counts, last sync time)',
    inputSchema: z.object({
      space: z.string().optional().describe('Space name (omit for default)'),
    }),
    handler: async (args, ctx) => {
      return runQuery(ctx.storage.basePath, 'db-stats', {
        space: args.space,
      })
    },
  },

  {
    name: 'backlinks',
    description: 'Find all documents that link to a given file path',
    inputSchema: z.object({
      target: z.string().describe('File path to find backlinks for (relative to Data root)'),
      space: z.string().optional().describe('Space name'),
    }),
    handler: async (args, ctx) => {
      // backlinks is not in query_library CLI, use Python inline
      const scriptPath = findQueryLibrary(ctx.storage.basePath)
      if (!scriptPath) return { error: 'query_library.py not found' }

      const pyCode = `
import sys, json
sys.path.insert(0, '${path.join(ctx.storage.basePath, '.datacore', 'lib')}')
from query_library import get_backlinks
result = get_backlinks('${args.target.replace(/'/g, "\\'")}', ${args.space ? `'${args.space}'` : 'None'})
print(json.dumps(result, default=str))
`
      try {
        const { stdout } = await execFileAsync('python3', ['-c', pyCode], {
          cwd: ctx.storage.basePath,
          timeout: 15000,
        })
        const backlinks = JSON.parse(stdout)
        return { target: args.target, count: backlinks.length, backlinks }
      } catch (err) {
        return { error: `Backlinks query failed: ${err.message}` }
      }
    },
  },

  {
    name: 'orphans',
    description: 'Find unlinked documents (no incoming or outgoing links)',
    inputSchema: z.object({
      space: z.string().optional().describe('Space name'),
    }),
    handler: async (args, ctx) => {
      const scriptPath = findQueryLibrary(ctx.storage.basePath)
      if (!scriptPath) return { error: 'query_library.py not found' }

      const pyCode = `
import sys, json
sys.path.insert(0, '${path.join(ctx.storage.basePath, '.datacore', 'lib')}')
from query_library import get_unresolved_links
result = get_unresolved_links(${args.space ? `'${args.space}'` : 'None'})
print(json.dumps(result, default=str))
`
      try {
        const { stdout } = await execFileAsync('python3', ['-c', pyCode], {
          cwd: ctx.storage.basePath,
          timeout: 15000,
        })
        const unresolved = JSON.parse(stdout)
        return { count: unresolved.length, unresolved_links: unresolved }
      } catch (err) {
        return { error: `Orphans query failed: ${err.message}` }
      }
    },
  },

  {
    name: 'tasks',
    description: 'Query tasks from indexed org files (AI-delegated, actionable, waiting, overdue)',
    inputSchema: z.object({
      type: z.enum(['ai-tasks', 'actionable', 'waiting', 'overdue', 'task-stats'])
        .optional()
        .describe('Query type (default: actionable)'),
      space: z.string().optional().describe('Space name'),
    }),
    handler: async (args, ctx) => {
      const queryType = args.type || 'actionable'
      return runQuery(ctx.storage.basePath, queryType, {
        space: args.space,
      })
    },
  },

  {
    name: 'patterns',
    description: 'Query learning patterns from indexed data (patterns, corrections, preferences)',
    inputSchema: z.object({
      type: z.enum(['patterns', 'corrections']).optional().describe('Query type (default: patterns)'),
      space: z.string().optional().describe('Space name'),
    }),
    handler: async (args, ctx) => {
      const queryType = args.type || 'patterns'
      return runQuery(ctx.storage.basePath, queryType, {
        space: args.space,
      })
    },
  },

  {
    name: 'find_by_skill',
    description: 'Find agents by skill keyword. Searches the agent registry for agents whose skills match the query (substring match).',
    inputSchema: z.object({
      query: z.string().describe('Skill keyword to search for (e.g., "content", "research", "gtd")'),
    }),
    handler: async (args, ctx) => {
      const indexerScript = path.join(ctx.storage.basePath, '.datacore', 'lib', 'agent_skill_indexer.py')
      if (!fs.existsSync(indexerScript)) {
        return { error: 'agent_skill_indexer.py not found in .datacore/lib/' }
      }

      try {
        const { stdout } = await execFileAsync('python3', [
          indexerScript, '--query', args.query, '--verbose', '--json',
        ], {
          cwd: path.join(ctx.storage.basePath, '.datacore', 'lib'),
          timeout: 15000,
          env: { ...process.env, DATACORE_ROOT: ctx.storage.basePath },
        })
        return JSON.parse(stdout)
      } catch (err) {
        // Fall back to non-JSON output
        try {
          const { stdout } = await execFileAsync('python3', [
            indexerScript, '--query', args.query, '--verbose',
          ], {
            cwd: path.join(ctx.storage.basePath, '.datacore', 'lib'),
            timeout: 15000,
            env: { ...process.env, DATACORE_ROOT: ctx.storage.basePath },
          })
          // Parse text output
          const lines = stdout.trim().split('\n')
          return { output: stdout.trim(), matches: lines.length }
        } catch (err2) {
          return { error: `Agent skill search failed: ${err2.message}` }
        }
      }
    },
  },
]
