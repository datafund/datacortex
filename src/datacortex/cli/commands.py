"""CLI commands for Datacortex."""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from ..core.config import load_config
from ..core.database import get_available_spaces


@click.group()
@click.version_option()
def cli():
    """Datacortex - Knowledge graph visualization for Datacore."""
    pass


@cli.command()
@click.option('--spaces', '-s', help='Comma-separated list of spaces to include')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--pretty', is_flag=True, help='Pretty print JSON')
def generate(spaces: Optional[str], output: Optional[str], pretty: bool):
    """Generate graph data as JSON."""
    from ..indexer.graph_builder import build_graph

    config = load_config()

    if spaces:
        space_list = [s.strip() for s in spaces.split(',')]
    else:
        space_list = config.spaces

    click.echo(f"Building graph from spaces: {', '.join(space_list)}", err=True)

    graph = build_graph(spaces=space_list, config=config)

    # Convert to D3-compatible format
    data = {
        "nodes": [node.model_dump(mode='json') for node in graph.nodes],
        "links": [edge.model_dump(mode='json') for edge in graph.edges],
        "spaces": graph.spaces,
        "generated_at": graph.generated_at.isoformat(),
        "stats": graph.stats.model_dump(),
    }

    indent = 2 if pretty else None
    json_str = json.dumps(data, indent=indent, default=str)

    if output:
        Path(output).write_text(json_str)
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(json_str)


@cli.command()
@click.option('--spaces', '-s', help='Comma-separated list of spaces to include')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def stats(spaces: Optional[str], as_json: bool):
    """Show graph statistics."""
    from ..indexer.graph_builder import build_graph

    config = load_config()

    if spaces:
        space_list = [s.strip() for s in spaces.split(',')]
    else:
        space_list = config.spaces

    graph = build_graph(spaces=space_list, config=config)
    s = graph.stats

    if as_json:
        click.echo(json.dumps(s.model_dump(), indent=2))
        return

    click.echo(f"\n{'='*50}")
    click.echo(f"  DATACORTEX GRAPH STATISTICS")
    click.echo(f"{'='*50}")
    click.echo(f"  Spaces: {', '.join(graph.spaces)}")
    click.echo(f"  Generated: {graph.generated_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"{'='*50}\n")

    click.echo(f"  Nodes: {s.node_count:,}")
    click.echo(f"  Edges: {s.edge_count:,}")
    click.echo(f"    - Resolved: {s.resolved_edges:,}")
    click.echo(f"    - Unresolved: {s.unresolved_edges:,}")
    click.echo(f"  Avg Degree: {s.avg_degree:.2f}")
    click.echo(f"  Max Degree: {s.max_degree}")
    click.echo(f"  Orphans: {s.orphan_count}")

    click.echo(f"\n  By Type:")
    for type_name, count in sorted(s.nodes_by_type.items(), key=lambda x: -x[1]):
        click.echo(f"    {type_name}: {count:,}")

    click.echo(f"\n  By Space:")
    for space_name, count in sorted(s.nodes_by_space.items(), key=lambda x: -x[1]):
        click.echo(f"    {space_name}: {count:,}")

    click.echo()


@cli.command()
@click.option('--spaces', '-s', help='Comma-separated list of spaces to include')
@click.option('--min-words', default=0, help='Minimum word count for orphans')
def orphans(spaces: Optional[str], min_words: int):
    """Find unconnected documents (orphans)."""
    from ..indexer.graph_builder import build_graph

    config = load_config()

    if spaces:
        space_list = [s.strip() for s in spaces.split(',')]
    else:
        space_list = config.spaces

    graph = build_graph(spaces=space_list, config=config)

    orphan_nodes = [n for n in graph.nodes if n.degree == 0 and n.word_count >= min_words]
    orphan_nodes.sort(key=lambda n: -n.word_count)

    if not orphan_nodes:
        click.echo("No orphan documents found.")
        return

    click.echo(f"\nFound {len(orphan_nodes)} orphan documents:\n")

    for node in orphan_nodes[:50]:  # Limit output
        click.echo(f"  [{node.type.value}] {node.title}")
        click.echo(f"    Path: {node.path}")
        click.echo(f"    Words: {node.word_count}")
        click.echo()

    if len(orphan_nodes) > 50:
        click.echo(f"  ... and {len(orphan_nodes) - 50} more")


@cli.command()
def spaces():
    """List available spaces with databases."""
    available = get_available_spaces()

    if not available:
        click.echo("No spaces with knowledge databases found.")
        click.echo("Run 'python zettel_db.py init --space SPACE' to initialize.")
        return

    click.echo("\nAvailable spaces:\n")
    for space in available:
        click.echo(f"  - {space}")
    click.echo()


@cli.group()
def pulse():
    """Pulse snapshot commands."""
    pass


@pulse.command('generate')
@click.option('--spaces', '-s', help='Comma-separated list of spaces to include')
@click.option('--note', '-n', help='Note for this pulse')
def pulse_generate(spaces: Optional[str], note: Optional[str]):
    """Generate a new pulse snapshot."""
    from ..pulse.generator import generate_pulse, save_pulse

    config = load_config()

    if spaces:
        space_list = [s.strip() for s in spaces.split(',')]
    else:
        space_list = config.spaces

    click.echo(f"Generating pulse for spaces: {', '.join(space_list)}", err=True)

    pulse_obj = generate_pulse(spaces=space_list, config=config, note=note)

    pulse_dir = Path(config.pulse.directory)
    pulse_path = save_pulse(pulse_obj, pulse_dir)

    click.echo(f"Pulse saved: {pulse_path}")
    click.echo(f"  ID: {pulse_obj.id}")
    click.echo(f"  Nodes: {pulse_obj.graph.stats.node_count}")
    click.echo(f"  Edges: {pulse_obj.graph.stats.edge_count}")


@pulse.command('list')
def pulse_list():
    """List available pulses."""
    from ..pulse.generator import list_pulses

    config = load_config()
    pulse_dir = Path(config.pulse.directory)

    pulses = list_pulses(pulse_dir)

    if not pulses:
        click.echo("No pulses found.")
        return

    click.echo(f"\nFound {len(pulses)} pulses:\n")
    for pulse_id in pulses[-20:]:  # Show last 20
        click.echo(f"  - {pulse_id}")

    if len(pulses) > 20:
        click.echo(f"\n  ... and {len(pulses) - 20} older pulses")


@cli.command()
@click.option('--host', default='127.0.0.1', help='Server host')
@click.option('--port', default=8765, help='Server port')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
@click.option('--open', 'open_browser', is_flag=True, help='Open browser')
def serve(host: str, port: int, reload: bool, open_browser: bool):
    """Start the web server."""
    import uvicorn

    if open_browser:
        import webbrowser
        webbrowser.open(f"http://{host}:{port}")

    click.echo(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        "datacortex.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == '__main__':
    cli()
