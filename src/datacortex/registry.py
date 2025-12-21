"""Agent Registry for DIP-0016 Agent Discovery.

This module provides functions to load and query the agent registry,
enabling semantic agent discovery based on skills and capabilities.

Usage:
    from datacortex.registry import load_registry, find_agents_by_skill, get_agent_metadata

    # Load the full registry
    registry = load_registry()

    # Find agents with a specific skill
    agents = find_agents_by_skill("content-generation")

    # Get metadata for a specific agent
    metadata = get_agent_metadata("gtd-content-writer")
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml

# Default paths
DATACORE_ROOT = Path(os.environ.get("DATACORE_ROOT", Path.home() / "Data"))
REGISTRY_PATH = DATACORE_ROOT / ".datacore" / "registry" / "agents.yaml"


def load_registry() -> Dict[str, Any]:
    """Load the full agent registry.

    Returns:
        Dict containing the full registry with 'agents' and 'module_agents' sections
    """
    if not REGISTRY_PATH.exists():
        return {"agents": {}, "module_agents": {}, "knowledge_locations": {}}

    with open(REGISTRY_PATH, 'r') as f:
        return yaml.safe_load(f) or {}


def get_all_agents() -> Dict[str, Dict[str, Any]]:
    """Get all registered agents (both core and module agents).

    Returns:
        Dict mapping agent_id to agent metadata
    """
    registry = load_registry()
    all_agents = {}

    # Add core agents
    for agent_id, metadata in registry.get("agents", {}).items():
        all_agents[agent_id] = metadata

    # Add module agents
    for agent_id, metadata in registry.get("module_agents", {}).items():
        all_agents[agent_id] = metadata

    return all_agents


def get_agent_metadata(agent_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific agent.

    Args:
        agent_id: The agent identifier (e.g., "gtd-content-writer")

    Returns:
        Agent metadata dict or None if not found
    """
    all_agents = get_all_agents()
    return all_agents.get(agent_id)


def find_agents_by_skill(skill: str, exact: bool = False) -> List[Dict[str, Any]]:
    """Find agents that have a specific skill.

    Args:
        skill: The skill to search for (e.g., "content-generation")
        exact: If True, require exact match. If False, allow partial match.

    Returns:
        List of agent metadata dicts that match
    """
    all_agents = get_all_agents()
    results = []

    skill_lower = skill.lower()

    for agent_id, metadata in all_agents.items():
        agent_skills = metadata.get("skills", [])

        if exact:
            if skill in agent_skills:
                results.append({"id": agent_id, **metadata})
        else:
            # Partial match
            for agent_skill in agent_skills:
                if skill_lower in agent_skill.lower():
                    results.append({"id": agent_id, **metadata})
                    break

    return results


def find_agents_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Find agents triggered by a specific org-mode tag.

    Args:
        tag: The tag to search for (e.g., ":AI:content:")

    Returns:
        List of agent metadata dicts that are triggered by this tag
    """
    all_agents = get_all_agents()
    results = []

    for agent_id, metadata in all_agents.items():
        triggers = metadata.get("triggers", {})
        tags = triggers.get("tags", [])

        if tag in tags:
            results.append({"id": agent_id, **metadata})

    return results


def find_agents_by_command(command: str) -> List[Dict[str, Any]]:
    """Find agents triggered by a specific slash command.

    Args:
        command: The command to search for (e.g., "/audit-agents")

    Returns:
        List of agent metadata dicts that are triggered by this command
    """
    all_agents = get_all_agents()
    results = []

    for agent_id, metadata in all_agents.items():
        triggers = metadata.get("triggers", {})
        commands = triggers.get("commands", [])

        if command in commands:
            results.append({"id": agent_id, **metadata})

    return results


def get_agent_spawn_graph() -> Dict[str, List[str]]:
    """Get the spawn relationship graph between agents.

    Returns:
        Dict mapping agent_id to list of agents it can spawn
    """
    all_agents = get_all_agents()
    graph = {}

    for agent_id, metadata in all_agents.items():
        spawns = metadata.get("spawns", [])
        if spawns:
            graph[agent_id] = spawns

    return graph


def detect_spawn_cycles() -> List[List[str]]:
    """Detect circular spawn dependencies.

    Returns:
        List of cycles, each cycle is a list of agent IDs forming the cycle
    """
    graph = get_agent_spawn_graph()
    all_agents = set(graph.keys())

    # Add all spawned agents to the set
    for spawns in graph.values():
        all_agents.update(spawns)

    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: List[str]) -> None:
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            dfs(neighbor, path)

        path.pop()
        rec_stack.remove(node)

    for agent in all_agents:
        if agent not in visited:
            dfs(agent, [])

    return cycles


def get_knowledge_locations() -> Dict[str, Dict[str, Any]]:
    """Get semantic knowledge locations for common retrieval patterns.

    Returns:
        Dict mapping location name to paths and queries
    """
    registry = load_registry()
    return registry.get("knowledge_locations", {})


def format_agent_summary(agent_id: str, metadata: Dict[str, Any]) -> str:
    """Format agent metadata as a readable summary.

    Args:
        agent_id: The agent identifier
        metadata: The agent metadata dict

    Returns:
        Formatted string summary
    """
    lines = [
        f"Agent: {agent_id}",
        f"  Description: {metadata.get('description', 'No description')}",
        f"  Version: {metadata.get('version', '0.0.0')}",
        f"  Source: {metadata.get('source', 'unknown')}",
    ]

    skills = metadata.get("skills", [])
    if skills:
        lines.append(f"  Skills: {', '.join(skills)}")

    triggers = metadata.get("triggers", {})
    tags = triggers.get("tags", [])
    commands = triggers.get("commands", [])

    if tags:
        lines.append(f"  Trigger Tags: {', '.join(tags)}")
    if commands:
        lines.append(f"  Trigger Commands: {', '.join(commands)}")

    spawns = metadata.get("spawns", [])
    if spawns:
        lines.append(f"  Spawns: {', '.join(spawns)}")

    called_by = metadata.get("can_be_called_by", [])
    if called_by:
        lines.append(f"  Called By: {', '.join(called_by)}")

    return '\n'.join(lines)


if __name__ == "__main__":
    # CLI interface for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: registry.py <command> [args]")
        print("Commands:")
        print("  list                - List all agents")
        print("  show <agent_id>     - Show agent details")
        print("  find <skill>        - Find agents by skill")
        print("  cycles              - Detect spawn cycles")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        agents = get_all_agents()
        print(f"\nRegistered Agents ({len(agents)}):\n")
        for agent_id, metadata in sorted(agents.items()):
            desc = metadata.get("description", "No description")[:60]
            print(f"  {agent_id}: {desc}")

    elif cmd == "show" and len(sys.argv) >= 3:
        agent_id = sys.argv[2]
        metadata = get_agent_metadata(agent_id)
        if metadata:
            print(f"\n{format_agent_summary(agent_id, metadata)}\n")
        else:
            print(f"Agent not found: {agent_id}")

    elif cmd == "find" and len(sys.argv) >= 3:
        skill = sys.argv[2]
        agents = find_agents_by_skill(skill)
        print(f"\nAgents with skill '{skill}' ({len(agents)}):\n")
        for agent in agents:
            print(f"  {agent['id']}: {agent.get('description', 'No description')[:60]}")

    elif cmd == "cycles":
        cycles = detect_spawn_cycles()
        if cycles:
            print(f"\nFound {len(cycles)} spawn cycles:\n")
            for cycle in cycles:
                print(f"  {' -> '.join(cycle)}")
        else:
            print("\nNo spawn cycles detected.")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
