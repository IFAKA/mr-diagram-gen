"""Configuration management for mr-diagram-gen."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    """Ollama configuration."""

    model: str = "codellama:13b"
    base_url: str = "http://localhost:11434"


class GitLabConfig(BaseModel):
    """GitLab configuration."""

    url: str = "https://gitlab.com"
    token: str | None = Field(default=None)

    def get_token(self) -> str | None:
        """Get token from config or environment."""
        return self.token or os.environ.get("GITLAB_TOKEN")


class GitHubConfig(BaseModel):
    """GitHub configuration."""

    token: str | None = Field(default=None)
    image_storage: str = "gist"  # 'gist' or 'comment'

    def get_token(self) -> str | None:
        """Get token from config or environment."""
        return self.token or os.environ.get("GITHUB_TOKEN")


class DiagramsConfig(BaseModel):
    """Diagrams output configuration."""

    output_dir: str = ".mr-diagrams"
    format: list[str] = Field(default_factory=lambda: ["png"])
    max_diagrams: int = 3


class RulesConfig(BaseModel):
    """Rules for diagram generation."""

    skip_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.md",
            "*.txt",
            "package-lock.json",
            "go.sum",
            "yarn.lock",
            "pnpm-lock.yaml",
            "*.lock",
        ]
    )
    always_diagram: list[str] = Field(default_factory=list)


class LanguageConfig(BaseModel):
    """Language-specific configuration."""

    diagrams: list[str] = Field(default_factory=list)
    focus_patterns: list[str] = Field(default_factory=list)


class LanguagesConfig(BaseModel):
    """All language configurations."""

    react: LanguageConfig = Field(
        default_factory=lambda: LanguageConfig(
            diagrams=["component-tree", "state-flow", "hook-deps"],
            focus_patterns=["src/components/**", "src/hooks/**", "src/pages/**"],
        )
    )
    nodejs: LanguageConfig = Field(
        default_factory=lambda: LanguageConfig(
            diagrams=["api-routes", "middleware-chain", "module-deps"],
            focus_patterns=["routes/**", "controllers/**", "services/**"],
        )
    )
    golang: LanguageConfig = Field(
        default_factory=lambda: LanguageConfig(
            diagrams=["package-deps", "interface-impl", "handler-flow"],
            focus_patterns=["internal/**", "pkg/**", "cmd/**"],
        )
    )
    typescript: LanguageConfig = Field(
        default_factory=lambda: LanguageConfig(
            diagrams=["component-tree", "type-hierarchy", "module-deps"],
            focus_patterns=["src/**/*.ts", "src/**/*.tsx"],
        )
    )


class Config(BaseModel):
    """Main configuration model."""

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    gitlab: GitLabConfig = Field(default_factory=GitLabConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    diagrams: DiagramsConfig = Field(default_factory=DiagramsConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    languages: LanguagesConfig = Field(default_factory=LanguagesConfig)


def get_global_config_path() -> Path:
    """Get the global configuration file path."""
    config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(config_home) / "mr-diagram" / "config.yaml"


def get_project_config_path(project_dir: Path | None = None) -> Path:
    """Get the project-specific configuration file path."""
    if project_dir is None:
        project_dir = Path.cwd()
    return project_dir / ".mr-diagram.yaml"


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two configuration dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def load_config(project_dir: Path | None = None) -> Config:
    """Load configuration from global and project files."""
    global_config = load_yaml_config(get_global_config_path())
    project_config = load_yaml_config(get_project_config_path(project_dir))
    merged = merge_configs(global_config, project_config)
    return Config(**merged) if merged else Config()


def save_config(config: Config, path: Path) -> None:
    """Save configuration to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


def create_default_config() -> Config:
    """Create and return a default configuration."""
    return Config()
