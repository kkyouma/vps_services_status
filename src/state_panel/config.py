"""Configuration model and parser for state-panel."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """Configuration for a single monitored service."""

    id: str
    name: str
    category: str = "VPS Services"
    type: Literal["http", "tcp"] = "http"
    target: str | None = None
    host: str | None = None
    port: int | None = None
    expected_status: int = 200
    timeout: float = 10.0
    headers: dict[str, str] = Field(default_factory=dict)
    description: str | None = None


class NtfyConfig(BaseModel):
    """Configuration for ntfy notifications (Pub/Sub)."""

    enabled: bool = False
    server: str = "https://ntfy.sh"
    topic: str = ""
    token: str | None = None
    priority: int = 4  # 1 (min) to 5 (max)


class PanelSettings(BaseModel):
    """Global panel settings."""

    title: str = "System Status"
    description: str = "Live operational status of services and infrastructure"
    refresh_interval_seconds: int = 60
    history_days: int = 90
    output_dir: str = "web/public/data"
    db_path: str = "state_panel.db"


class PanelConfig(BaseModel):
    """Root configuration object."""

    settings: PanelSettings = Field(default_factory=PanelSettings)
    ntfy: NtfyConfig = Field(default_factory=NtfyConfig)
    services: list[ServiceConfig] = Field(default_factory=list)


def load_config(config_path: str | Path | None = None) -> PanelConfig:
    """Load configuration from a YAML file.

    If not provided, looks for services.yaml or services.example.yaml.
    """
    candidates = (
        [Path(config_path)]
        if config_path
        else [
            Path("services.yaml"),
            Path("services.yml"),
            Path("services.example.yaml"),
        ]
    )

    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                raw_data: dict[str, Any] = yaml.safe_load(f) or {}
            return PanelConfig(**raw_data)

    # Return default empty config if no file found
    return PanelConfig()
