"""Configuration management for Datacortex."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from .database import DATA_ROOT


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "127.0.0.1"
    port: int = 8765


class PulseConfig(BaseModel):
    """Pulse generation configuration."""
    directory: str = "pulses"
    schedule: str = "manual"  # daily, weekly, manual


class GraphConfig(BaseModel):
    """Graph generation configuration."""
    include_stubs: bool = True
    include_unresolved: bool = True
    min_degree: int = 0
    compute_centrality: bool = True
    compute_clusters: bool = True


class VisualizationConfig(BaseModel):
    """Visualization defaults."""
    node_size_metric: str = "degree"  # degree, centrality
    color_by: str = "type"  # type, space, cluster


class DatacortexConfig(BaseModel):
    """Main configuration for Datacortex."""
    datacore_root: Path = Field(default_factory=lambda: DATA_ROOT)
    spaces: list[str] = Field(default_factory=lambda: ["personal", "datafund"])
    server: ServerConfig = Field(default_factory=ServerConfig)
    pulse: PulseConfig = Field(default_factory=PulseConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    class Config:
        arbitrary_types_allowed = True


def load_config(config_dir: Optional[Path] = None) -> DatacortexConfig:
    """Load configuration from YAML files.

    Loads base config from datacortex.yaml, then overlays
    datacortex.local.yaml if it exists.
    """
    if config_dir is None:
        # Default to config/ directory relative to package
        config_dir = Path(__file__).parent.parent.parent.parent / "config"

    config_data = {}

    # Load base config
    base_config = config_dir / "datacortex.yaml"
    if base_config.exists():
        with open(base_config) as f:
            config_data = yaml.safe_load(f) or {}

    # Overlay local config
    local_config = config_dir / "datacortex.local.yaml"
    if local_config.exists():
        with open(local_config) as f:
            local_data = yaml.safe_load(f) or {}
            config_data = deep_merge(config_data, local_data)

    # Expand ~ in datacore_root
    if "datacore_root" in config_data:
        config_data["datacore_root"] = Path(config_data["datacore_root"]).expanduser()

    return DatacortexConfig(**config_data)


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
