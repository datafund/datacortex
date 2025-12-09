"""Pulse API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.config import load_config
from ...pulse.generator import (
    compute_changes,
    generate_pulse,
    list_pulses,
    load_pulse,
    save_pulse,
)

router = APIRouter()


@router.get("")
@router.get("/")
async def get_pulses():
    """List all available pulses with metadata."""
    config = load_config()
    pulse_dir = Path(config.pulse.directory)

    pulse_ids = list_pulses(pulse_dir)

    pulses = []
    for pulse_id in pulse_ids:
        pulse_path = pulse_dir / f"{pulse_id}.json"
        try:
            pulse = load_pulse(pulse_path)
            pulses.append({
                "id": pulse.id,
                "timestamp": pulse.timestamp.isoformat(),
                "node_count": pulse.graph.stats.node_count,
                "edge_count": pulse.graph.stats.edge_count,
                "note": pulse.note,
            })
        except Exception:
            # Skip corrupted pulses
            continue

    return {"pulses": pulses}


@router.get("/{pulse_id}")
async def get_pulse(pulse_id: str):
    """Get graph data for a specific pulse."""
    config = load_config()
    pulse_dir = Path(config.pulse.directory)
    pulse_path = pulse_dir / f"{pulse_id}.json"

    if not pulse_path.exists():
        raise HTTPException(status_code=404, detail="Pulse not found")

    pulse = load_pulse(pulse_path)

    return {
        "id": pulse.id,
        "timestamp": pulse.timestamp.isoformat(),
        "nodes": [n.model_dump(mode='json') for n in pulse.graph.nodes],
        "links": [e.model_dump(mode='json') for e in pulse.graph.edges],
        "stats": pulse.graph.stats.model_dump(),
        "changes": pulse.changes.model_dump() if pulse.changes else None,
        "note": pulse.note,
    }


@router.get("/diff/{pulse_a}/{pulse_b}")
async def get_pulse_diff(pulse_a: str, pulse_b: str):
    """Get changes between two pulses."""
    config = load_config()
    pulse_dir = Path(config.pulse.directory)

    path_a = pulse_dir / f"{pulse_a}.json"
    path_b = pulse_dir / f"{pulse_b}.json"

    if not path_a.exists():
        raise HTTPException(status_code=404, detail=f"Pulse {pulse_a} not found")
    if not path_b.exists():
        raise HTTPException(status_code=404, detail=f"Pulse {pulse_b} not found")

    pulse_obj_a = load_pulse(path_a)
    pulse_obj_b = load_pulse(path_b)

    changes = compute_changes(pulse_obj_a.graph, pulse_obj_b.graph)

    return {
        "from_pulse": pulse_a,
        "to_pulse": pulse_b,
        "changes": changes.model_dump(),
    }


@router.post("/generate")
async def generate_new_pulse(
    note: Optional[str] = Query(None, description="Note for this pulse"),
):
    """Generate a new pulse snapshot."""
    config = load_config()

    pulse = generate_pulse(config=config, note=note)

    pulse_dir = Path(config.pulse.directory)
    pulse_path = save_pulse(pulse, pulse_dir)

    return {
        "status": "generated",
        "id": pulse.id,
        "path": str(pulse_path),
        "stats": pulse.graph.stats.model_dump(),
        "changes": pulse.changes.model_dump() if pulse.changes else None,
    }
