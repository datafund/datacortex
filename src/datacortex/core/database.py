"""Database connection wrapper for Datacore knowledge database."""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Detect DATA_ROOT from environment, cwd, or relative to this file
def _find_datacore_root() -> Path:
    """Find the datacore root directory."""
    # Check environment variable first
    if 'DATACORE_ROOT' in os.environ:
        return Path(os.environ['DATACORE_ROOT'])

    # Try current working directory and its parents
    cwd = Path.cwd().resolve()
    for path in [cwd] + list(cwd.parents):
        if (path / '.datacore').is_dir() and (path / 'CLAUDE.md').is_file():
            return path

    # Try to find by walking up from this file
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.datacore').is_dir() and (parent / '0-personal').is_dir():
            return parent
        if (parent / '.datacore').is_dir() and (parent / 'CLAUDE.md').is_file():
            return parent

    # Fallback to ~/repos/datacore or ~/Data
    for path in [Path.home() / "repos" / "datacore", Path.home() / "Data"]:
        if path.is_dir() and (path / '.datacore').is_dir():
            return path

    # Last resort
    return Path.home() / "Data"

DATA_ROOT = _find_datacore_root()

# Add datacore lib to path for importing zettel_db
DATACORE_LIB = DATA_ROOT / ".datacore" / "lib"
if str(DATACORE_LIB) not in sys.path:
    sys.path.insert(0, str(DATACORE_LIB))

# Try to import from zettel_db, fall back to direct implementation
try:
    from zettel_db import get_connection as _get_connection, SPACES as _SPACES
    HAS_ZETTEL_DB = True
    # Override SPACES with our detected DATA_ROOT
    SPACES = {
        'personal': {'path': DATA_ROOT / '0-personal'},
        'datafund': {'path': DATA_ROOT / '1-datafund'},
        'datacore': {'path': DATA_ROOT / '2-datacore'},
    }
except ImportError:
    HAS_ZETTEL_DB = False
    SPACES = {
        'personal': {'path': DATA_ROOT / '0-personal'},
        'datafund': {'path': DATA_ROOT / '1-datafund'},
        'datacore': {'path': DATA_ROOT / '2-datacore'},
    }


def get_connection(space: Optional[str] = None) -> sqlite3.Connection:
    """Get database connection for a space.

    Args:
        space: Space name (personal, datafund, datacore) or None for root DB

    Returns:
        SQLite connection with row factory set
    """
    if HAS_ZETTEL_DB:
        return _get_connection(space)

    # Fallback implementation
    if space is None:
        db_path = DATA_ROOT / ".datacore" / "knowledge.db"
    elif space in SPACES:
        db_path = SPACES[space]['path'] / '.datacore' / 'knowledge.db'
    else:
        raise ValueError(f"Unknown space: {space}. Valid: {list(SPACES.keys())}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_available_spaces() -> list[str]:
    """Get list of spaces with existing databases."""
    spaces = []
    for space_name, space_config in SPACES.items():
        db_path = space_config['path'] / '.datacore' / 'knowledge.db'
        if db_path.exists():
            spaces.append(space_name)
    return spaces


def space_exists(space: str) -> bool:
    """Check if a space has a knowledge database."""
    if space not in SPACES:
        return False
    db_path = SPACES[space]['path'] / '.datacore' / 'knowledge.db'
    return db_path.exists()
