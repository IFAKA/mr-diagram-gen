"""Tests for data models."""

import pytest

from mr_diagram_gen.models import (
    BranchAnalysis,
    ChangeType,
    ClassificationResult,
    DiagramType,
    FileChange,
    GeneratedDiagram,
    Platform,
    ProjectType,
    RemoteInfo,
)


def test_file_change():
    """Test FileChange model."""
    fc = FileChange(
        path="src/components/Button.tsx",
        change_type=ChangeType.ADDED,
        diff_content="+export const Button = () => {}",
        added_lines=10,
        deleted_lines=0,
    )

    assert fc.path == "src/components/Button.tsx"
    assert fc.change_type == ChangeType.ADDED
    assert fc.added_lines == 10


def test_branch_analysis():
    """Test BranchAnalysis model."""
    analysis = BranchAnalysis(
        branch_name="feature/new-button",
        base_branch="main",
        project_type=ProjectType.REACT,
        total_additions=50,
        total_deletions=10,
    )

    assert analysis.branch_name == "feature/new-button"
    assert analysis.project_type == ProjectType.REACT
    assert analysis.total_additions == 50


def test_classification_result():
    """Test ClassificationResult model."""
    result = ClassificationResult(
        needs_diagram=True,
        diagram_types=[DiagramType.FLOWCHART, DiagramType.COMPONENT],
        reason="New feature with multiple components",
        confidence=0.85,
    )

    assert result.needs_diagram is True
    assert len(result.diagram_types) == 2
    assert result.confidence == 0.85


def test_generated_diagram():
    """Test GeneratedDiagram model."""
    diagram = GeneratedDiagram(
        diagram_type=DiagramType.FLOWCHART,
        title="Component Flow",
        mermaid_code="graph TD\n    A --> B",
        description="Shows component interaction",
    )

    assert diagram.diagram_type == DiagramType.FLOWCHART
    assert "graph TD" in diagram.mermaid_code


def test_remote_info():
    """Test RemoteInfo model."""
    info = RemoteInfo(
        platform=Platform.GITHUB,
        owner="user",
        repo="project",
        url="https://github.com/user/project.git",
    )

    assert info.platform == Platform.GITHUB
    assert info.owner == "user"


def test_project_type_values():
    """Test ProjectType enum values."""
    assert ProjectType.REACT.value == "react"
    assert ProjectType.GOLANG.value == "golang"
    assert ProjectType.GENERIC.value == "generic"


def test_diagram_type_values():
    """Test DiagramType enum values."""
    assert DiagramType.FLOWCHART.value == "flowchart"
    assert DiagramType.SEQUENCE.value == "sequence"
    assert DiagramType.ER.value == "er"
