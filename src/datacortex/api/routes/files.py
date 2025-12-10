"""File tree and editor API endpoints."""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


def get_datacore_root() -> Path:
    """Get the Datacore root directory."""
    root = os.environ.get("DATACORE_ROOT", os.path.expanduser("~/Data"))
    return Path(root)


class FileNode(BaseModel):
    """File tree node."""
    name: str
    path: str
    type: str  # "file" or "directory"
    children: Optional[list["FileNode"]] = None


class FileContent(BaseModel):
    """File content response."""
    path: str
    content: str
    modified: float


class FileSaveRequest(BaseModel):
    """File save request."""
    content: str


def build_tree(path: Path, root: Path, max_depth: int = 3, current_depth: int = 0) -> Optional[FileNode]:
    """Build file tree recursively."""
    if current_depth > max_depth:
        return None

    rel_path = str(path.relative_to(root))
    name = path.name or str(root)

    # Skip hidden files/dirs and common non-content dirs
    if name.startswith(".") and name not in [".datacore"]:
        return None
    if name in ["node_modules", "__pycache__", ".venv", "venv", ".git"]:
        return None

    if path.is_file():
        # Only show markdown, org, and text files
        if path.suffix.lower() in [".md", ".org", ".txt", ".yaml", ".yml", ".json"]:
            return FileNode(name=name, path=rel_path, type="file")
        return None

    if path.is_dir():
        children = []
        try:
            for child in sorted(path.iterdir()):
                child_node = build_tree(child, root, max_depth, current_depth + 1)
                if child_node:
                    children.append(child_node)
        except PermissionError:
            pass

        # Only include directories that have children
        if children or current_depth == 0:
            return FileNode(name=name, path=rel_path, type="directory", children=children)

    return None


@router.get("/tree")
async def get_file_tree(depth: int = Query(default=4, ge=1, le=6)):
    """Get file tree structure."""
    root = get_datacore_root()
    if not root.exists():
        raise HTTPException(status_code=404, detail="Datacore root not found")

    tree = build_tree(root, root, max_depth=depth)
    return tree


@router.get("/search")
async def search_files(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Search for files by name or content."""
    root = get_datacore_root()
    results = []

    q_lower = q.lower()

    for path in root.rglob("*"):
        if len(results) >= limit:
            break

        # Skip non-content files
        if path.is_dir():
            continue
        if path.suffix.lower() not in [".md", ".org", ".txt"]:
            continue

        # Skip hidden and system paths
        rel_path = str(path.relative_to(root))
        if any(part.startswith(".") for part in path.parts if part not in [".datacore"]):
            continue
        if any(skip in rel_path for skip in ["node_modules", "__pycache__", ".venv", ".git"]):
            continue

        # Match filename
        if q_lower in path.name.lower():
            results.append({
                "path": rel_path,
                "name": path.name,
                "match_type": "filename"
            })
            continue

        # Match content (first 100 chars of match)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if q_lower in content.lower():
                # Find match position for preview
                idx = content.lower().find(q_lower)
                start = max(0, idx - 40)
                end = min(len(content), idx + len(q) + 60)
                preview = content[start:end].replace("\n", " ").strip()
                if start > 0:
                    preview = "..." + preview
                if end < len(content):
                    preview = preview + "..."

                results.append({
                    "path": rel_path,
                    "name": path.name,
                    "match_type": "content",
                    "preview": preview
                })
        except Exception:
            pass

    return {"query": q, "results": results, "total": len(results)}


@router.get("/content/{path:path}")
async def get_file_content(path: str):
    """Get file content."""
    root = get_datacore_root()
    file_path = root / path

    # Security: ensure path is within root
    try:
        file_path.resolve().relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    try:
        content = file_path.read_text(encoding="utf-8")
        stat = file_path.stat()
        return FileContent(path=path, content=content, modified=stat.st_mtime)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/content/{path:path}")
async def save_file_content(path: str, request: FileSaveRequest):
    """Save file content."""
    root = get_datacore_root()
    file_path = root / path

    # Security: ensure path is within root
    try:
        file_path.resolve().relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Only allow editing existing files for safety
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Only allow certain file types
    if file_path.suffix.lower() not in [".md", ".org", ".txt", ".yaml", ".yml"]:
        raise HTTPException(status_code=403, detail="File type not editable")

    try:
        file_path.write_text(request.content, encoding="utf-8")
        stat = file_path.stat()
        return {"status": "saved", "path": path, "modified": stat.st_mtime}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/links/{path:path}")
async def get_file_links(path: str):
    """Get wiki-links from and to a file."""
    import re

    root = get_datacore_root()
    file_path = root / path

    # Security check
    try:
        file_path.resolve().relative_to(root.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Extract outgoing links
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    wiki_links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)

    outgoing = []
    for link in wiki_links:
        # Try to resolve link to file
        link_name = link.strip()
        outgoing.append({"title": link_name, "resolved": None})

        # Simple resolution: look for file with matching name
        for candidate in root.rglob(f"*{link_name}*"):
            if candidate.is_file() and candidate.suffix in [".md", ".org"]:
                outgoing[-1]["resolved"] = str(candidate.relative_to(root))
                break

    # Find incoming links (files that link to this one)
    file_stem = file_path.stem
    incoming = []

    for other_file in root.rglob("*.md"):
        if other_file == file_path:
            continue
        try:
            other_content = other_file.read_text(encoding="utf-8", errors="ignore")
            if f"[[{file_stem}]]" in other_content or f"[[{file_stem}|" in other_content:
                incoming.append({
                    "path": str(other_file.relative_to(root)),
                    "name": other_file.name
                })
        except Exception:
            pass

    return {
        "path": path,
        "outgoing": outgoing,
        "incoming": incoming
    }
