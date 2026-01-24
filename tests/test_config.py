"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from mr_diagram_gen.config import (
    Config,
    create_default_config,
    load_yaml_config,
    merge_configs,
    save_config,
)


def test_create_default_config():
    """Test creating default configuration."""
    config = create_default_config()
    assert config.ollama.model == "codellama:13b"
    assert config.ollama.base_url == "http://localhost:11434"
    assert config.gitlab.url == "https://gitlab.com"
    assert "png" in config.diagrams.format
    assert config.diagrams.max_diagrams == 3


def test_merge_configs():
    """Test merging configuration dictionaries."""
    base = {
        "ollama": {"model": "codellama:13b", "base_url": "http://localhost:11434"},
        "diagrams": {"max_diagrams": 3},
    }
    override = {
        "ollama": {"model": "deepseek-coder:6.7b"},
        "diagrams": {"format": ["svg"]},
    }
    result = merge_configs(base, override)

    assert result["ollama"]["model"] == "deepseek-coder:6.7b"
    assert result["ollama"]["base_url"] == "http://localhost:11434"
    assert result["diagrams"]["max_diagrams"] == 3
    assert result["diagrams"]["format"] == ["svg"]


def test_save_and_load_config():
    """Test saving and loading configuration."""
    config = create_default_config()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        save_config(config, config_path)

        assert config_path.exists()

        loaded = load_yaml_config(config_path)
        assert loaded["ollama"]["model"] == "codellama:13b"


def test_load_nonexistent_config():
    """Test loading a non-existent config file."""
    result = load_yaml_config(Path("/nonexistent/path/config.yaml"))
    assert result == {}
