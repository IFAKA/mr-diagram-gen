"""Tests for change classification."""

import pytest

from mr_diagram_gen.change_classifier import ChangeClassifier
from mr_diagram_gen.config import Config
from mr_diagram_gen.models import (
    BranchAnalysis,
    ChangeType,
    DiagramType,
    FileChange,
    ProjectType,
)


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config()


@pytest.fixture
def classifier(config):
    """Create a classifier in mock mode."""
    return ChangeClassifier(config, mock_mode=True)


def test_trivial_change_detection(classifier):
    """Test that trivial changes are detected."""
    analysis = BranchAnalysis(
        branch_name="fix/typo",
        base_branch="main",
        file_changes=[
            FileChange(
                path="README.md",
                change_type=ChangeType.MODIFIED,
            )
        ],
        total_additions=2,
        total_deletions=2,
    )

    result = classifier.classify(analysis)
    assert result.needs_diagram is False
    assert "Trivial" in result.reason


def test_no_changes(classifier):
    """Test classification with no file changes."""
    analysis = BranchAnalysis(
        branch_name="empty",
        base_branch="main",
        file_changes=[],
    )

    result = classifier.classify(analysis)
    assert result.needs_diagram is False


def test_significant_changes(classifier):
    """Test classification with significant changes."""
    analysis = BranchAnalysis(
        branch_name="feature/new-api",
        base_branch="main",
        project_type=ProjectType.NODEJS,
        file_changes=[
            FileChange(
                path="src/api/users.js",
                change_type=ChangeType.ADDED,
                functions_changed=["createUser", "getUser", "updateUser"],
            ),
            FileChange(
                path="src/services/userService.js",
                change_type=ChangeType.ADDED,
            ),
            FileChange(
                path="src/models/User.js",
                change_type=ChangeType.ADDED,
            ),
        ],
        total_additions=150,
        total_deletions=0,
    )

    result = classifier.classify(analysis)
    assert result.needs_diagram is True
    assert len(result.diagram_types) > 0


def test_always_diagram_pattern(config, classifier):
    """Test that always_diagram patterns trigger diagrams."""
    config.rules.always_diagram = ["src/api/**"]
    classifier = ChangeClassifier(config, mock_mode=True)

    analysis = BranchAnalysis(
        branch_name="update/api",
        base_branch="main",
        file_changes=[
            FileChange(
                path="src/api/endpoint.js",
                change_type=ChangeType.MODIFIED,
            )
        ],
        total_additions=5,
        total_deletions=3,
    )

    result = classifier.classify(analysis)
    assert result.needs_diagram is True
    assert "always_diagram" in result.reason


def test_suggest_diagram_types_react(classifier):
    """Test diagram type suggestions for React projects."""
    analysis = BranchAnalysis(
        branch_name="feature/button",
        base_branch="main",
        project_type=ProjectType.REACT,
        file_changes=[
            FileChange(
                path="src/components/Button.tsx",
                change_type=ChangeType.ADDED,
                components_changed=["Button"],
            )
        ],
        total_additions=50,
    )

    types = classifier._suggest_diagram_types(analysis)
    assert DiagramType.COMPONENT in types or DiagramType.FLOWCHART in types


def test_suggest_diagram_types_golang(classifier):
    """Test diagram type suggestions for Go projects."""
    analysis = BranchAnalysis(
        branch_name="feature/handler",
        base_branch="main",
        project_type=ProjectType.GOLANG,
        file_changes=[
            FileChange(
                path="internal/handlers/user.go",
                change_type=ChangeType.ADDED,
            )
        ],
        total_additions=80,
    )

    types = classifier._suggest_diagram_types(analysis)
    assert len(types) > 0
