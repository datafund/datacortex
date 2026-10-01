"""The Datacore MCP server's semantic search runs through lib/bridge.py.

Canvas finding (2026-10-01): datacore_search with method "semantic" looks for
.datacore/modules/datacortex/lib/bridge.py. The file did not exist, so every
semantic request fell back to keyword search. These tests pin the contract the
server reads: one JSON request on stdin, one JSON answer on stdout, exit 0;
{"results": [{path, score, snippet}]} on success, {"error", "code"} when it
cannot run, with code "no_index" or "no_model" so the caller can say why.
"""
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[1] / "lib" / "bridge.py"


def _ask(root: Path, request: dict) -> dict:
    out = subprocess.run([sys.executable, "-E", "-s", str(BRIDGE)], input=json.dumps(request) + "\n",
                         capture_output=True, text=True, timeout=60,
                         env={"DATACORE_ROOT": str(root), "PATH": "/usr/bin:/bin", "HOME": str(root)})
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _space(root: Path, embeddings: int = 0) -> None:
    db = root / "0-personal/.datacore/knowledge.db"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE files (id TEXT, title TEXT, path TEXT, type TEXT, updated_at TEXT, word_count INT)")
    if embeddings:
        conn.execute("CREATE TABLE embeddings (file_id TEXT PRIMARY KEY, embedding BLOB NOT NULL, "
                     "model TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
        for i in range(embeddings):
            conn.execute("INSERT INTO embeddings VALUES (?, x'00', 'm', 'h', 't')", (f"f{i}",))
    conn.commit()
    conn.close()


def _load():
    spec = importlib.util.spec_from_file_location("datacortex_bridge", BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_bridge_the_server_looks_for_exists():
    assert BRIDGE.is_file(), f"datacore-mcp looks for {BRIDGE}; without it semantic search never runs"


def test_no_index_is_reported_as_no_index(tmp_path):
    (tmp_path / ".datacore").mkdir()
    _space(tmp_path, embeddings=0)
    answer = _ask(tmp_path, {"action": "search", "query": "anything", "limit": 5})
    assert answer.get("code") == "no_index", answer
    assert "results" not in answer


def test_a_bad_request_is_refused_not_crashed(tmp_path):
    (tmp_path / ".datacore").mkdir()
    answer = _ask(tmp_path, {"action": "delete", "query": "x"})
    assert answer.get("error") and answer.get("code") == "bad_request", answer


def test_results_have_the_shape_the_server_accepts(tmp_path):
    bridge = _load()

    class Hit:
        def __init__(self, path, relevance, content):
            self.path, self.relevance, self.content = path, relevance, content

    class Found:
        results = [Hit("/d/a.md", 0.91, "first   line\n\nsecond line " + "x" * 600), Hit("/d/b.md", 0.5, "")]

    answer = bridge.answer({"action": "search", "query": "q", "limit": 1},
                           spaces=lambda: ["personal"], search=lambda q, s, k: Found())
    assert answer == {"results": [{"path": "/d/a.md", "score": 0.91,
                                   "snippet": answer["results"][0]["snippet"]}]}
    snippet = answer["results"][0]["snippet"]
    assert snippet.startswith("first line second line") and len(snippet) <= 300


def test_a_missing_model_is_reported_as_no_model():
    bridge = _load()

    def search(q, s, k):
        raise ImportError("No module named 'sentence_transformers'")

    answer = bridge.answer({"action": "search", "query": "q", "limit": 3},
                           spaces=lambda: ["personal"], search=search)
    assert answer.get("code") == "no_model", answer


def test_a_model_that_is_not_downloaded_is_reported_as_no_model():
    """Offline by default: a search request never downloads a model; an
    uncached model surfaces as OSError from the loader."""
    bridge = _load()

    def search(q, s, k):
        raise OSError("model not in the local cache")

    answer = bridge.answer({"action": "search", "query": "q", "limit": 3},
                           spaces=lambda: ["personal"], search=search)
    assert answer.get("code") == "no_model", answer


def test_a_search_request_never_goes_online():
    import os
    _load()
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
