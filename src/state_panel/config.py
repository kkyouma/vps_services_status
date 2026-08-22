"""Configuration model and parser for state-panel."""

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


def _load_dotenv(env_path: Path = Path(".env")) -> None:
    """Load key-value pairs from .env file into os.environ if not already set."""
    if not env_path.exists():
        return

    with open(env_path, encoding="utf-8") as f:
        for raw_line in f:
            clean_line = raw_line.strip()
            if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                continue
            key, val = clean_line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


def _expand_env_vars(text: str) -> str:
    """Expand ${VAR} or ${VAR:-default} from os.environ."""
    pattern = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}")

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        return os.environ.get(var_name, default_val)

    return pattern.sub(_replace, text)


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
    history_days: int = 30
    output_dir: str = "web/public/data"
    db_path: str = "state_panel.db"


class PanelConfig(BaseModel):
    """Root configuration object."""

    settings: PanelSettings = Field(default_factory=PanelSettings)
    ntfy: NtfyConfig = Field(default_factory=NtfyConfig)
    services: list[ServiceConfig] = Field(default_factory=list)


def load_config(config_path: str | Path | None = None) -> PanelConfig:
    """Load configuration from a YAML file with environment variable expansion.

    If not provided, looks for services.yaml or services.example.yaml.
    """
    _load_dotenv()

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
                content = f.read()

            expanded_content = _expand_env_vars(content)
            raw_data: dict[str, Any] = yaml.safe_load(expanded_content) or {}
            return PanelConfig(**raw_data)

    # Return default empty config if no file found
    return PanelConfig()
