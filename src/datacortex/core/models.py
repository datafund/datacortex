"""Core data models for Datacortex."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of documents in the knowledge graph."""
    ZETTEL = "zettel"
    PAGE = "page"
    JOURNAL = "journal"
    LITERATURE = "literature"
    CLIPPING = "clipping"
    ORG_TASK = "org_task"
    STUB = "stub"
    UNKNOWN = "unknown"


class Node(BaseModel):
    """A document node in the knowledge graph."""
    id: str
    title: str
    path: str
    space: str
    type: NodeType = NodeType.UNKNOWN
    maturity: Optional[str] = None
    is_stub: bool = False
    word_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Computed metrics
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0
    centrality: float = 0.0
    cluster_id: Optional[int] = None


class Edge(BaseModel):
    """A link between two documents."""
    id: str
    source: str
    target: str
    syntax: str = "wiki-link"  # wiki-link, hashtag, hashtag-bracket
    resolved: bool = True
    weight: float = 1.0


class GraphStats(BaseModel):
    """Statistics about the graph."""
    node_count: int = 0
    edge_count: int = 0
    resolved_edges: int = 0
    unresolved_edges: int = 0
    avg_degree: float = 0.0
    max_degree: int = 0
    cluster_count: int = 0
    orphan_count: int = 0
    nodes_by_type: dict[str, int] = Field(default_factory=dict)
    nodes_by_space: dict[str, int] = Field(default_factory=dict)


class Graph(BaseModel):
    """Complete knowledge graph with nodes and edges."""
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    spaces: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    stats: GraphStats = Field(default_factory=GraphStats)


class PulseChanges(BaseModel):
    """Changes between two pulses."""
    nodes_added: list[str] = Field(default_factory=list)
    nodes_removed: list[str] = Field(default_factory=list)
    edges_added: list[str] = Field(default_factory=list)
    edges_removed: list[str] = Field(default_factory=list)
    node_count_delta: int = 0
    edge_count_delta: int = 0


class Pulse(BaseModel):
    """A timestamped snapshot of the graph state."""
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    graph: Graph
    changes: Optional[PulseChanges] = None
    note: Optional[str] = None
