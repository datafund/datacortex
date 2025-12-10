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


@cli.command()
@click.option('--space', '-s', help='Compute for specific space (default: all spaces)')
@click.option('--force', is_flag=True, help='Force recompute all embeddings (ignore cache)')
def embed(space: Optional[str], force: bool):
    """Compute embeddings for documents."""
    import time
    from ..ai.embeddings import compute_embeddings_for_space

    if space:
        spaces_to_process = [space]
    else:
        spaces_to_process = get_available_spaces()

    if not spaces_to_process:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}")
    click.echo(f"  DATACORTEX EMBEDDING COMPUTATION")
    click.echo(f"{'='*50}")
    click.echo(f"  Model: sentence-transformers/all-mpnet-base-v2")
    click.echo(f"  Spaces: {', '.join(spaces_to_process)}")
    click.echo(f"  Mode: {'FORCE RECOMPUTE' if force else 'INCREMENTAL (cache enabled)'}")
    click.echo(f"{'='*50}\n")

    total_start = time.time()
    total_docs = 0

    for space_name in spaces_to_process:
        click.echo(f"Processing space: {space_name}")

        start = time.time()
        embeddings = compute_embeddings_for_space(space_name, force=force)
        elapsed = time.time() - start

        total_docs += len(embeddings)

        click.echo(f"  Completed: {len(embeddings)} documents in {elapsed:.2f}s")
        if embeddings:
            click.echo(f"  Speed: {len(embeddings)/elapsed:.1f} docs/sec\n")
        else:
            click.echo()

    total_elapsed = time.time() - total_start

    click.echo(f"{'='*50}")
    click.echo(f"  SUMMARY")
    click.echo(f"{'='*50}")
    click.echo(f"  Total documents: {total_docs}")
    click.echo(f"  Total time: {total_elapsed:.2f}s")
    if total_docs > 0:
        click.echo(f"  Average speed: {total_docs/total_elapsed:.1f} docs/sec")
    click.echo(f"{'='*50}\n")


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


@cli.command()
@click.option('--space', '-s', help='Generate for specific space (default: all spaces)')
@click.option('--threshold', '-t', default=0.75, help='Similarity threshold (default: 0.75)')
@click.option('--top-n', '-n', default=20, help='Number of top suggestions (default: 20)')
@click.option('--min-words', '-w', default=50, help='Minimum words for orphans (default: 50)')
def digest(space: Optional[str], threshold: float, top_n: int, min_words: int):
    """Generate daily digest of link suggestions."""
    from datetime import datetime
    from ..digest.generator import generate_digest
    from ..digest.formatter import format_digest

    config = load_config()

    if space:
        spaces_to_process = [space]
    else:
        spaces_to_process = get_available_spaces()

    if not spaces_to_process:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}", err=True)
    click.echo(f"  DATACORTEX DAILY DIGEST", err=True)
    click.echo(f"{'='*50}", err=True)
    click.echo(f"  Spaces: {', '.join(spaces_to_process)}", err=True)
    click.echo(f"  Threshold: {threshold}", err=True)
    click.echo(f"  Top N: {top_n}", err=True)
    click.echo(f"{'='*50}\n", err=True)

    # Generate digest
    result = generate_digest(
        spaces=spaces_to_process,
        threshold=threshold,
        top_n=top_n,
        min_orphan_words=min_words
    )

    # Format as compact TSV/markdown
    formatted = format_digest(result)

    # Write to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/datacortex_digest_{timestamp}.txt")
    output_path.write_text(formatted)

    click.echo(f"Digest written to: {output_path}", err=True)
    click.echo(formatted)


@cli.command()
@click.option('--space', '-s', help='Detect gaps for specific space (default: all spaces)')
@click.option('--min-score', '-m', default=0.3, help='Minimum gap score threshold (default: 0.3)')
def gaps(space: Optional[str], min_score: float):
    """Detect knowledge gaps between clusters."""
    from datetime import datetime
    from ..gaps.detector import detect_gaps
    from ..gaps.formatter import format_gaps

    config = load_config()

    if space:
        spaces_to_process = [space]
    else:
        spaces_to_process = get_available_spaces()

    if not spaces_to_process:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}", err=True)
    click.echo(f"  DATACORTEX KNOWLEDGE GAPS", err=True)
    click.echo(f"{'='*50}", err=True)
    click.echo(f"  Spaces: {', '.join(spaces_to_process)}", err=True)
    click.echo(f"  Min Gap Score: {min_score}", err=True)
    click.echo(f"{'='*50}\n", err=True)

    # Detect gaps
    result = detect_gaps(
        spaces=spaces_to_process,
        min_gap_score=min_score
    )

    # Format as compact TSV/markdown
    formatted = format_gaps(result)

    # Write to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/datacortex_gaps_{timestamp}.txt")
    output_path.write_text(formatted)

    click.echo(f"\nGaps analysis written to: {output_path}", err=True)
    click.echo(formatted)


@cli.command()
@click.option('--space', '-s', help='Analyze specific space (default: all spaces)')
@click.option('--cluster', '-c', type=int, help='Analyze single cluster by ID')
@click.option('--no-samples', is_flag=True, help='Skip content samples')
@click.option('--top', '-t', type=int, help='Only top N clusters by size')
def insights(space: Optional[str], cluster: Optional[int], no_samples: bool, top: Optional[int]):
    """Analyze knowledge clusters and synthesize insights."""
    from datetime import datetime
    from ..insights.analyzer import analyze_clusters, analyze_single_cluster
    from ..insights.formatter import format_insights, format_cluster_summary

    config = load_config()

    if space:
        spaces_to_process = [space]
    else:
        spaces_to_process = get_available_spaces()

    if not spaces_to_process:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}", err=True)
    click.echo(f"  DATACORTEX CLUSTER INSIGHTS", err=True)
    click.echo(f"{'='*50}", err=True)
    click.echo(f"  Spaces: {', '.join(spaces_to_process)}", err=True)

    if cluster is not None:
        click.echo(f"  Mode: Single cluster ({cluster})", err=True)
    else:
        click.echo(f"  Mode: All clusters", err=True)
        if top:
            click.echo(f"  Limit: Top {top} by size", err=True)

    click.echo(f"{'='*50}\n", err=True)

    # Analyze
    if cluster is not None:
        # Single cluster analysis
        analysis = analyze_single_cluster(cluster, spaces_to_process)
        from ..insights.analyzer import InsightsResult
        result = InsightsResult(
            clusters=[analysis],
            total_docs=0,  # Not computed for single cluster
            total_clusters=1,
            generated_at=datetime.now().isoformat()
        )
    else:
        # All clusters
        result = analyze_clusters(spaces_to_process)

        # Apply top N filter
        if top and top < len(result.clusters):
            result.clusters = result.clusters[:top]

    # Format
    include_samples = not no_samples
    formatted = format_insights(result, include_samples=include_samples)

    # Write to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/datacortex_insights_{timestamp}.txt")
    output_path.write_text(formatted)

    click.echo(f"\nInsights written to: {output_path}", err=True)
    click.echo(formatted)


@cli.command()
@click.option('--space', '-s', help='Analyze specific space (default: all spaces)')
@click.option('--top', '-t', default=15, help='Number of opportunities per category (default: 15)')
def opportunities(space: Optional[str], top: int):
    """Find low-hanging fruit research opportunities."""
    from datetime import datetime
    from ..indexer.graph_builder import build_graph

    config = load_config()

    if space:
        spaces_to_process = [space]
    else:
        spaces_to_process = get_available_spaces()

    if not spaces_to_process:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}", err=True)
    click.echo(f"  DATACORTEX OPPORTUNITIES", err=True)
    click.echo(f"{'='*50}", err=True)
    click.echo(f"  Spaces: {', '.join(spaces_to_process)}", err=True)
    click.echo(f"  Top per category: {top}", err=True)
    click.echo(f"{'='*50}\n", err=True)

    # Build graph
    graph = build_graph(spaces=spaces_to_process, config=config)

    output_lines = []
    output_lines.append(f"# OPPORTUNITIES generated={datetime.now().isoformat()}")
    output_lines.append(f"spaces: {', '.join(spaces_to_process)}")
    output_lines.append("")

    # 1. HIGH-VALUE STUBS: stubs with high centrality (many references)
    stubs = [n for n in graph.nodes if n.is_stub and n.degree > 0]
    stubs.sort(key=lambda n: (-n.degree, n.title))

    output_lines.append("## HIGH_VALUE_STUBS")
    output_lines.append("# Stub notes with many references but no content")
    output_lines.append("# title | references | centrality | tags")
    output_lines.append("")

    for node in stubs[:top]:
        tags = ', '.join(node.tags[:5]) if node.tags else 'none'
        output_lines.append(f"{node.title} | {node.degree} refs | {node.centrality:.3f} | {tags}")

    output_lines.append("")

    # 2. ORPHANS WITH CONTENT: documents with real content but no connections
    orphans = [n for n in graph.nodes if n.degree == 0 and n.word_count >= 100 and not n.is_stub]
    orphans.sort(key=lambda n: (-n.word_count, n.title))

    output_lines.append("## INTEGRATION_CANDIDATES")
    output_lines.append("# Documents with content but no links (orphans worth connecting)")
    output_lines.append("# title | words | type | path")
    output_lines.append("")

    for node in orphans[:top]:
        output_lines.append(f"{node.title} | {node.word_count}w | {node.type.value} | {node.path}")

    output_lines.append("")

    # 3. LOW-DEGREE HIGH-CONTENT: substantial docs with few connections
    underlinked = [n for n in graph.nodes if 1 <= n.degree <= 2 and n.word_count >= 300 and not n.is_stub]
    underlinked.sort(key=lambda n: (-n.word_count, n.degree))

    output_lines.append("## UNDERLINKED_CONTENT")
    output_lines.append("# Substantial documents (300+ words) with only 1-2 links")
    output_lines.append("# title | words | links | type")
    output_lines.append("")

    for node in underlinked[:top]:
        output_lines.append(f"{node.title} | {node.word_count}w | {node.degree} links | {node.type.value}")

    output_lines.append("")

    # 4. CLUSTER INFO: count clusters and suggest gaps analysis
    clusters = {}
    for node in graph.nodes:
        if node.cluster_id is not None:
            if node.cluster_id not in clusters:
                clusters[node.cluster_id] = []
            clusters[node.cluster_id].append(node)

    # Find clusters with many stubs (indicates topics needing research)
    stub_heavy_clusters = []
    for cluster_id, nodes in clusters.items():
        stub_count = sum(1 for n in nodes if n.is_stub)
        total = len(nodes)
        if total >= 5 and stub_count >= 3:
            stub_ratio = stub_count / total
            stub_heavy_clusters.append((cluster_id, total, stub_count, stub_ratio))

    stub_heavy_clusters.sort(key=lambda x: (-x[2], -x[3]))

    output_lines.append("## STUB_HEAVY_CLUSTERS")
    output_lines.append("# Clusters with many stubs (topic areas needing research)")
    output_lines.append("# cluster_id | total_nodes | stub_count | stub_ratio | sample_titles")
    output_lines.append("")

    for cluster_id, total, stub_count, stub_ratio in stub_heavy_clusters[:top]:
        cluster_nodes = clusters[cluster_id]
        sample_titles = [n.title for n in cluster_nodes[:3]]
        output_lines.append(f"Cluster {cluster_id} | {total} nodes | {stub_count} stubs | {stub_ratio:.0%} | {'; '.join(sample_titles)}")

    output_lines.append("")

    # Summary stats
    output_lines.append("## SUMMARY")
    output_lines.append(f"high_value_stubs: {len(stubs)}")
    output_lines.append(f"integration_candidates: {len(orphans)}")
    output_lines.append(f"underlinked_content: {len(underlinked)}")
    output_lines.append(f"stub_heavy_clusters: {len(stub_heavy_clusters)}")

    formatted = '\n'.join(output_lines)

    # Write to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/datacortex_opportunities_{timestamp}.txt")
    output_path.write_text(formatted)

    click.echo(f"\nOpportunities written to: {output_path}", err=True)
    click.echo(formatted)


@cli.command()
@click.argument('query')
@click.option('--space', '-s', multiple=True, help='Spaces to search (can specify multiple)')
@click.option('--top', '-t', default=5, help='Number of results (default: 5)')
@click.option('--no-expand', is_flag=True, help='Skip graph expansion')
def search(query: str, space: tuple[str], top: int, no_expand: bool):
    """Search knowledge base using RAG retrieval."""
    from datetime import datetime
    from ..qa.retriever import search as do_search
    from ..qa.formatter import format_search_results

    config = load_config()

    # Determine spaces
    if space:
        spaces_to_search = list(space)
    else:
        spaces_to_search = get_available_spaces()

    if not spaces_to_search:
        click.echo("No spaces with knowledge databases found.")
        return

    click.echo(f"\n{'='*50}", err=True)
    click.echo(f"  DATACORTEX SEARCH", err=True)
    click.echo(f"{'='*50}", err=True)
    click.echo(f'  Query: "{query}"', err=True)
    click.echo(f"  Spaces: {', '.join(spaces_to_search)}", err=True)
    click.echo(f"  Top: {top}", err=True)
    click.echo(f"  Expand: {not no_expand}", err=True)
    click.echo(f"{'='*50}\n", err=True)

    # Search
    results = do_search(
        query=query,
        spaces=spaces_to_search,
        top_k=top,
        expand=not no_expand
    )

    # Format
    formatted = format_search_results(results)

    # Write to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/datacortex_search_{timestamp}.txt")
    output_path.write_text(formatted)

    click.echo(f"Search results written to: {output_path}", err=True)
    click.echo(f"\n{output_path}")


if __name__ == '__main__':
    cli()
