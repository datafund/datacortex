"""Pulse snapshot generation and management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import DatacortexConfig, load_config
from ..core.models import Graph, Pulse, PulseChanges
from ..indexer.graph_builder import build_graph


def generate_pulse(
    spaces: Optional[list[str]] = None,
    config: Optional[DatacortexConfig] = None,
    pulse_id: Optional[str] = None,
    note: Optional[str] = None,
) -> Pulse:
    """Generate a pulse snapshot of the current graph state.

    Args:
        spaces: Spaces to include (default: from config)
        config: Configuration (default: load from files)
        pulse_id: Custom pulse ID (default: timestamp)
        note: Optional note for this pulse

    Returns:
        Pulse object with graph snapshot
    """
    if config is None:
        config = load_config()

    if spaces is None:
        spaces = config.spaces

    # Build current graph
    graph = build_graph(spaces=spaces, config=config)

    # Generate pulse ID from timestamp
    if pulse_id is None:
        pulse_id = datetime.now().strftime("%Y-%m-%d-%H%M")

    # Load previous pulse to compute changes
    pulse_dir = Path(config.pulse.directory)
    previous_pulse = load_latest_pulse(pulse_dir)

    changes = None
    if previous_pulse:
        changes = compute_changes(previous_pulse.graph, graph)

    return Pulse(
        id=pulse_id,
        timestamp=datetime.now(),
        graph=graph,
        changes=changes,
        note=note,
    )


def save_pulse(pulse: Pulse, pulse_dir: Path) -> Path:
    """Save pulse to JSON file.

    Args:
        pulse: Pulse to save
        pulse_dir: Directory to save to

    Returns:
        Path to saved file
    """
    pulse_dir.mkdir(parents=True, exist_ok=True)
    pulse_path = pulse_dir / f"{pulse.id}.json"

    data = pulse.model_dump(mode='json')
    with open(pulse_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    return pulse_path


def load_pulse(pulse_path: Path) -> Pulse:
    """Load pulse from JSON file."""
    with open(pulse_path) as f:
        data = json.load(f)
    return Pulse.model_validate(data)


def load_latest_pulse(pulse_dir: Path) -> Optional[Pulse]:
    """Load the most recent pulse from directory."""
    if not pulse_dir.exists():
        return None

    pulse_files = sorted(pulse_dir.glob("*.json"))
    if not pulse_files:
        return None

    return load_pulse(pulse_files[-1])


def list_pulses(pulse_dir: Path) -> list[str]:
    """List available pulse IDs in chronological order."""
    if not pulse_dir.exists():
        return []

    pulses = []
    for f in pulse_dir.glob("*.json"):
        pulses.append(f.stem)

    return sorted(pulses)


def compute_changes(old_graph: Graph, new_graph: Graph) -> PulseChanges:
    """Compute changes between two graphs.

    Args:
        old_graph: Previous graph state
        new_graph: Current graph state

    Returns:
        PulseChanges with added/removed nodes and edges
    """
    old_node_ids = {n.id for n in old_graph.nodes}
    new_node_ids = {n.id for n in new_graph.nodes}

    old_edge_ids = {e.id for e in old_graph.edges}
    new_edge_ids = {e.id for e in new_graph.edges}

    return PulseChanges(
        nodes_added=list(new_node_ids - old_node_ids),
        nodes_removed=list(old_node_ids - new_node_ids),
        edges_added=list(new_edge_ids - old_edge_ids),
        edges_removed=list(old_edge_ids - new_edge_ids),
        node_count_delta=len(new_graph.nodes) - len(old_graph.nodes),
        edge_count_delta=len(new_graph.edges) - len(old_graph.edges),
    )
