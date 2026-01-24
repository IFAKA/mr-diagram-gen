"""Data models for mr-diagram-gen."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ProjectType(Enum):
    """Supported project types."""

    REACT = "react"
    NODEJS = "nodejs"
    GOLANG = "golang"
    TYPESCRIPT = "typescript"
    GENERIC = "generic"


class DiagramType(Enum):
    """Supported diagram types."""

    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    COMPONENT = "component"
    ER = "er"
    CLASS = "class"
    STATE = "state"


class ChangeType(Enum):
    """Types of file changes."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class Platform(Enum):
    """Git hosting platforms."""

    GITLAB = "gitlab"
    GITHUB = "github"
    UNKNOWN = "unknown"


@dataclass
class FileChange:
    """Represents a changed file in a git diff."""

    path: str
    change_type: ChangeType
    diff_content: str = ""
    added_lines: int = 0
    deleted_lines: int = 0
    functions_changed: list[str] = field(default_factory=list)
    classes_changed: list[str] = field(default_factory=list)
    components_changed: list[str] = field(default_factory=list)


@dataclass
class CommitInfo:
    """Information about a commit."""

    sha: str
    message: str
    author: str
    files_changed: list[str] = field(default_factory=list)


@dataclass
class BranchAnalysis:
    """Analysis of changes in a branch."""

    branch_name: str
    base_branch: str
    commits: list[CommitInfo] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    project_type: ProjectType = ProjectType.GENERIC
    total_additions: int = 0
    total_deletions: int = 0


@dataclass
class ClassificationResult:
    """Result of change classification by LLM."""

    needs_diagram: bool
    diagram_types: list[DiagramType] = field(default_factory=list)
    reason: str = ""
    confidence: float = 0.0


@dataclass
class GeneratedDiagram:
    """A generated Mermaid diagram."""

    diagram_type: DiagramType
    title: str
    mermaid_code: str
    description: str = ""
    image_path: Path | None = None


@dataclass
class MRDescription:
    """Merge/Pull Request description with diagrams."""

    title: str
    body: str
    diagrams: list[GeneratedDiagram] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass
class RemoteInfo:
    """Information about the git remote."""

    platform: Platform
    owner: str
    repo: str
    url: str
