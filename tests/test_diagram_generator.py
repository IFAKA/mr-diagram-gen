"""Tests for diagram generation."""

import pytest

from mr_diagram_gen.config import Config
from mr_diagram_gen.diagram_generator import DiagramGenerator
from mr_diagram_gen.models import (
    BranchAnalysis,
    ChangeType,
    ClassificationResult,
    DiagramType,
    FileChange,
    ProjectType,
)


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config()


@pytest.fixture
def generator(config):
    """Create a generator in mock mode."""
    return DiagramGenerator(config, mock_mode=True)


def test_generate_flowchart(generator):
    """Test generating a flowchart diagram."""
    analysis = BranchAnalysis(
        branch_name="feature/flow",
        base_branch="main",
        file_changes=[
            FileChange(
                path="src/process.js",
                change_type=ChangeType.ADDED,
                functions_changed=["processData", "validateInput"],
            )
        ],
    )

    diagram = generator.generate_diagram(analysis, DiagramType.FLOWCHART)

    assert diagram is not None
    assert diagram.diagram_type == DiagramType.FLOWCHART
    assert "graph" in diagram.mermaid_code.lower()


def test_generate_sequence(generator):
    """Test generating a sequence diagram."""
    analysis = BranchAnalysis(
        branch_name="feature/api",
        base_branch="main",
        project_type=ProjectType.NODEJS,
        file_changes=[
            FileChange(
                path="src/api/users.js",
                change_type=ChangeType.ADDED,
            )
        ],
    )

    diagram = generator.generate_diagram(analysis, DiagramType.SEQUENCE)

    assert diagram is not None
    assert diagram.diagram_type == DiagramType.SEQUENCE
    assert "sequenceDiagram" in diagram.mermaid_code


def test_generate_component(generator):
    """Test generating a component diagram."""
    analysis = BranchAnalysis(
        branch_name="feature/modules",
        base_branch="main",
        file_changes=[
            FileChange(
                path="src/module/a.js",
                change_type=ChangeType.ADDED,
            ),
            FileChange(
                path="src/module/b.js",
                change_type=ChangeType.ADDED,
            ),
        ],
    )

    diagram = generator.generate_diagram(analysis, DiagramType.COMPONENT)

    assert diagram is not None
    assert diagram.diagram_type == DiagramType.COMPONENT


def test_generate_all_diagrams(generator):
    """Test generating all recommended diagrams."""
    analysis = BranchAnalysis(
        branch_name="feature/new",
        base_branch="main",
        project_type=ProjectType.REACT,
        file_changes=[
            FileChange(
                path="src/components/Widget.tsx",
                change_type=ChangeType.ADDED,
                components_changed=["Widget"],
            )
        ],
    )

    classification = ClassificationResult(
        needs_diagram=True,
        diagram_types=[DiagramType.FLOWCHART, DiagramType.COMPONENT],
    )

    diagrams = generator.generate_all_diagrams(analysis, classification)

    assert len(diagrams) == 2


def test_react_mock_diagram(generator):
    """Test React-specific mock diagram generation."""
    analysis = BranchAnalysis(
        branch_name="feature/components",
        base_branch="main",
        project_type=ProjectType.REACT,
        file_changes=[
            FileChange(
                path="src/components/Button.tsx",
                change_type=ChangeType.ADDED,
                components_changed=["Button", "IconButton"],
            )
        ],
    )

    mermaid = generator._generate_react_mock(analysis)

    assert "graph TD" in mermaid
    assert "App" in mermaid
    assert "Button" in mermaid


def test_golang_mock_diagram(generator):
    """Test Go-specific mock diagram generation."""
    analysis = BranchAnalysis(
        branch_name="feature/handler",
        base_branch="main",
        project_type=ProjectType.GOLANG,
        file_changes=[
            FileChange(
                path="internal/handlers/user.go",
                change_type=ChangeType.ADDED,
            ),
            FileChange(
                path="pkg/database/db.go",
                change_type=ChangeType.MODIFIED,
            ),
        ],
    )

    mermaid = generator._generate_golang_mock(analysis)

    assert "graph LR" in mermaid


def test_clean_mermaid_code(generator):
    """Test cleaning Mermaid code."""
    dirty = """```mermaid
graph TD
    A --> B
```"""

    clean = generator._clean_mermaid_code(dirty)

    assert "```" not in clean
    assert clean.startswith("graph TD")


def test_generate_diagram_title(generator):
    """Test diagram title generation."""
    analysis = BranchAnalysis(
        branch_name="feature/auth",
        base_branch="main",
        file_changes=[
            FileChange(
                path="src/auth/login.js",
                change_type=ChangeType.ADDED,
            )
        ],
    )

    title = generator._generate_diagram_title(analysis, DiagramType.SEQUENCE)

    assert "Sequence" in title
    assert "login" in title


def test_max_diagrams_limit(generator, config):
    """Test that diagram generation respects max_diagrams config."""
    config.diagrams.max_diagrams = 1
    generator = DiagramGenerator(config, mock_mode=True)

    analysis = BranchAnalysis(
        branch_name="feature/many",
        base_branch="main",
    )

    classification = ClassificationResult(
        needs_diagram=True,
        diagram_types=[DiagramType.FLOWCHART, DiagramType.COMPONENT, DiagramType.SEQUENCE],
    )

    diagrams = generator.generate_all_diagrams(analysis, classification)

    assert len(diagrams) <= 1
