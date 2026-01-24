"""Tests for git analysis."""

import os
import tempfile
from pathlib import Path

import pytest
from git import Repo

from mr_diagram_gen.config import Config
from mr_diagram_gen.git_analyzer import GitAnalyzer
from mr_diagram_gen.models import ChangeType, Platform, ProjectType


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)

        # Configure git user for commits
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create initial commit on main
        readme = repo_path / "README.md"
        readme.write_text("# Test Project\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Rename default branch to main
        repo.heads[0].rename("main")

        yield repo_path, repo


def test_get_current_branch(temp_git_repo):
    """Test getting current branch name."""
    repo_path, repo = temp_git_repo
    analyzer = GitAnalyzer(repo_path)

    assert analyzer.get_current_branch() == "main"


def test_get_default_branch(temp_git_repo):
    """Test getting default branch."""
    repo_path, repo = temp_git_repo
    analyzer = GitAnalyzer(repo_path)

    assert analyzer.get_default_branch() == "main"


def test_detect_project_type_generic(temp_git_repo):
    """Test project type detection for generic project."""
    repo_path, _ = temp_git_repo
    analyzer = GitAnalyzer(repo_path)

    assert analyzer.detect_project_type() == ProjectType.GENERIC


def test_detect_project_type_nodejs(temp_git_repo):
    """Test project type detection for Node.js project."""
    repo_path, _ = temp_git_repo

    package_json = repo_path / "package.json"
    package_json.write_text('{"name": "test", "dependencies": {}}')

    analyzer = GitAnalyzer(repo_path)
    assert analyzer.detect_project_type() == ProjectType.NODEJS


def test_detect_project_type_react(temp_git_repo):
    """Test project type detection for React project."""
    repo_path, _ = temp_git_repo

    package_json = repo_path / "package.json"
    package_json.write_text('{"name": "test", "dependencies": {"react": "^18.0.0"}}')

    analyzer = GitAnalyzer(repo_path)
    assert analyzer.detect_project_type() == ProjectType.REACT


def test_detect_project_type_golang(temp_git_repo):
    """Test project type detection for Go project."""
    repo_path, _ = temp_git_repo

    go_mod = repo_path / "go.mod"
    go_mod.write_text("module example.com/test\n\ngo 1.21\n")

    analyzer = GitAnalyzer(repo_path)
    assert analyzer.detect_project_type() == ProjectType.GOLANG


def test_detect_project_type_typescript(temp_git_repo):
    """Test project type detection for TypeScript project."""
    repo_path, _ = temp_git_repo

    tsconfig = repo_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {}}')

    analyzer = GitAnalyzer(repo_path)
    assert analyzer.detect_project_type() == ProjectType.TYPESCRIPT


def test_analyze_branch_with_changes(temp_git_repo):
    """Test branch analysis with file changes."""
    repo_path, repo = temp_git_repo

    # Create a feature branch
    feature_branch = repo.create_head("feature/test")
    feature_branch.checkout()

    # Add a new file
    new_file = repo_path / "src" / "feature.js"
    new_file.parent.mkdir(exist_ok=True)
    new_file.write_text("export function newFeature() { return 'hello'; }")
    repo.index.add(["src/feature.js"])
    repo.index.commit("Add new feature")

    analyzer = GitAnalyzer(repo_path)
    analysis = analyzer.analyze_branch("main")

    assert analysis.branch_name == "feature/test"
    assert analysis.base_branch == "main"
    assert len(analysis.file_changes) > 0
    assert any(fc.path == "src/feature.js" for fc in analysis.file_changes)


def test_skip_patterns(temp_git_repo):
    """Test that skip patterns are respected."""
    repo_path, repo = temp_git_repo
    config = Config()
    config.rules.skip_patterns = ["*.md"]

    # Create feature branch
    feature_branch = repo.create_head("feature/docs")
    feature_branch.checkout()

    # Add markdown file
    docs = repo_path / "docs.md"
    docs.write_text("# Documentation\n\nSome docs.")
    repo.index.add(["docs.md"])
    repo.index.commit("Add docs")

    analyzer = GitAnalyzer(repo_path, config=config)
    analysis = analyzer.analyze_branch("main")

    # Markdown file should be skipped
    assert not any(fc.path == "docs.md" for fc in analysis.file_changes)


def test_detect_remote_platform_no_remote(temp_git_repo):
    """Test platform detection with no remote."""
    repo_path, _ = temp_git_repo
    analyzer = GitAnalyzer(repo_path)

    remote_info = analyzer.detect_remote_platform()
    assert remote_info.platform == Platform.UNKNOWN


def test_has_remote_false(temp_git_repo):
    """Test has_remote when no remote exists."""
    repo_path, _ = temp_git_repo
    analyzer = GitAnalyzer(repo_path)

    assert analyzer.has_remote() is False


def test_invalid_repo_path():
    """Test initialization with invalid path."""
    with pytest.raises(ValueError, match="Not a git repository"):
        GitAnalyzer(Path("/tmp/not-a-repo-12345"))


def test_extract_functions_from_diff():
    """Test function extraction from diff content."""
    repo_path = Path.cwd()

    # Only run if we're in a git repo
    try:
        analyzer = GitAnalyzer(repo_path)
    except ValueError:
        pytest.skip("Not in a git repository")

    diff_content = """
+function handleClick() {
+  console.log('clicked');
+}
+
+const processData = async (data) => {
+  return data.map(x => x * 2);
+}
"""

    functions = analyzer._extract_functions_from_diff(diff_content, ProjectType.NODEJS)

    assert "handleClick" in functions or "processData" in functions


def test_extract_components_from_diff():
    """Test React component extraction from diff content."""
    repo_path = Path.cwd()

    try:
        analyzer = GitAnalyzer(repo_path)
    except ValueError:
        pytest.skip("Not in a git repository")

    diff_content = """
+export function Button({ onClick }) {
+  return <button onClick={onClick}>Click me</button>;
+}
+
+const Card = () => {
+  return <div className="card">Content</div>;
+};
"""

    components = analyzer._extract_components_from_diff(diff_content)

    assert "Button" in components or "Card" in components
