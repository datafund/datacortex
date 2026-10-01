#!/usr/bin/env python3
"""Semantic search bridge for the Datacore MCP server (datacore_search, method "semantic").

The server runs this file with one JSON request on stdin:
    {"action": "search", "query": "...", "limit": 20}
and reads one JSON answer on stdout (exit 0 either way):
    {"results": [{"path": "/abs/file.md", "score": 0.83, "snippet": "..."}]}
    {"error": "...", "code": "no_index" | "no_model" | "bad_request" | "failed"}

The search itself is Datacortex's own (datacortex.qa.retriever.search: embed
the query, cosine over cached embeddings, graph expansion, re-rank). This file
only adapts it. Spaces without embeddings are skipped without being touched;
when none has any, the answer is "no_index" (build them with `datacortex embed`).
"""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import sys
from pathlib import Path

# A search request never downloads a model: `datacortex embed` installs it.
# Without this, an uncached model or a slow hub check ran past the server's limit.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SRC = Path(__file__).resolve().parents[1] / "src"
SNIPPET = 300


def _spaces_with_embeddings() -> list[str]:
    """Spaces whose knowledge.db holds at least one embedding. Read-only."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from datacortex.core.database import SPACES  # stdlib only; no model load
    found = []
    for name, cfg in SPACES.items():
        db = Path(cfg["path"]) / ".datacore" / "knowledge.db"
        if not db.is_file():
            continue
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                if conn.execute("SELECT 1 FROM embeddings LIMIT 1").fetchone():
                    found.append(name)
            finally:
                conn.close()
        except sqlite3.Error:
            continue
    return found


def _datacortex_search(query: str, spaces: list[str], top_k: int):
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from datacortex.qa.retriever import search  # loads numpy + sentence-transformers
    return search(query, spaces, top_k=top_k, expand=True)


def answer(request, *, spaces=_spaces_with_embeddings, search=_datacortex_search) -> dict:
    if (not isinstance(request, dict) or request.get("action") != "search"
            or not isinstance(request.get("query"), str) or not request["query"].strip()):
        return {"error": "expected {action: search, query, limit}", "code": "bad_request"}
    limit = request.get("limit", 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        return {"error": "limit must be an integer 1..1000", "code": "bad_request"}
    try:
        names = spaces()
    except Exception:
        return {"error": "could not read the knowledge databases", "code": "failed"}
    if not names:
        return {"error": "no space has Datacortex embeddings", "code": "no_index"}
    try:
        found = search(request["query"], names, limit)
    except (ImportError, OSError):
        return {"error": "embedding model package or its downloaded model is missing", "code": "no_model"}
    except Exception:
        return {"error": "Datacortex search failed", "code": "failed"}
    results = []
    for hit in found.results[:limit]:
        snippet = " ".join(str(hit.content or "").split())[:SNIPPET]
        results.append({"path": str(hit.path), "score": float(hit.relevance), "snippet": snippet})
    return {"results": results}


def main() -> int:
    try:
        request = json.loads(sys.stdin.readline() or "null")
    except ValueError:
        request = None
    # Libraries may print progress; only the answer may reach stdout.
    with contextlib.redirect_stdout(sys.stderr):
        result = answer(request)
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
