"""Git repository analysis module."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .config import Config
from .models import (
    BranchAnalysis,
    ChangeType,
    CommitInfo,
    FileChange,
    Platform,
    ProjectType,
    RemoteInfo,
)


class GitAnalyzer:
    """Analyzes git repositories for changes."""

    def __init__(self, repo_path: Path | None = None, config: Config | None = None):
        """Initialize the git analyzer.

        Args:
            repo_path: Path to the git repository. Defaults to current directory.
            config: Configuration object.
        """
        self.repo_path = repo_path or Path.cwd()
        self.config = config or Config()
        try:
            self.repo = Repo(self.repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise ValueError(f"Not a git repository: {self.repo_path}") from e

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        return self.repo.active_branch.name

    def get_default_branch(self) -> str:
        """Get the default branch (main or master)."""
        for branch_name in ["main", "master"]:
            if branch_name in [b.name for b in self.repo.branches]:
                return branch_name
        # Fallback to first branch
        if self.repo.branches:
            return self.repo.branches[0].name
        raise ValueError("No branches found in repository")

    def detect_project_type(self) -> ProjectType:
        """Detect the project type based on configuration files."""
        root = self.repo_path

        # Check for Go
        if (root / "go.mod").exists():
            return ProjectType.GOLANG

        # Check for TypeScript
        if (root / "tsconfig.json").exists():
            return ProjectType.TYPESCRIPT

        # Check for Node.js/React
        package_json = root / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps or "next" in deps:
                    return ProjectType.REACT
                return ProjectType.NODEJS
            except (json.JSONDecodeError, OSError):
                return ProjectType.NODEJS

        return ProjectType.GENERIC

    def detect_remote_platform(self) -> RemoteInfo:
        """Detect the git hosting platform from remote URL."""
        try:
            remote = self.repo.remote("origin")
            url = remote.url
        except ValueError:
            return RemoteInfo(
                platform=Platform.UNKNOWN, owner="", repo="", url=""
            )

        # Parse the remote URL
        # SSH format: git@github.com:owner/repo.git
        # HTTPS format: https://github.com/owner/repo.git

        platform = Platform.UNKNOWN
        owner = ""
        repo_name = ""

        if "gitlab" in url.lower():
            platform = Platform.GITLAB
        elif "github" in url.lower():
            platform = Platform.GITHUB

        # Extract owner and repo
        patterns = [
            r"[:/]([^/]+)/([^/.]+?)(?:\.git)?$",  # Matches both SSH and HTTPS
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo_name = match.group(2)
                break

        return RemoteInfo(platform=platform, owner=owner, repo=repo_name, url=url)

    def _should_skip_file(self, file_path: str) -> bool:
        """Check if a file should be skipped based on configuration."""
        for pattern in self.config.rules.skip_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            if fnmatch.fnmatch(Path(file_path).name, pattern):
                return True
        return False

    def _parse_diff_stats(self, diff_item) -> tuple[int, int]:
        """Parse additions and deletions from a diff item."""
        try:
            diff_text = diff_item.diff.decode("utf-8", errors="replace")
            added = sum(1 for line in diff_text.split("\n") if line.startswith("+") and not line.startswith("+++"))
            deleted = sum(1 for line in diff_text.split("\n") if line.startswith("-") and not line.startswith("---"))
            return added, deleted
        except Exception:
            return 0, 0

    def _extract_functions_from_diff(self, diff_content: str, project_type: ProjectType) -> list[str]:
        """Extract function/method names from diff content."""
        functions = []

        patterns = {
            ProjectType.GOLANG: [
                r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",  # Go functions
            ],
            ProjectType.REACT: [
                r"function\s+(\w+)\s*\(",  # Regular functions
                r"const\s+(\w+)\s*=\s*(?:async\s*)?\(",  # Arrow functions
                r"(?:export\s+)?(?:default\s+)?function\s+(\w+)",  # Export functions
            ],
            ProjectType.NODEJS: [
                r"function\s+(\w+)\s*\(",
                r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
                r"(\w+)\s*:\s*(?:async\s+)?function",
            ],
            ProjectType.TYPESCRIPT: [
                r"function\s+(\w+)\s*[<(]",
                r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
                r"(?:public|private|protected)?\s*(?:async\s+)?(\w+)\s*\(",
            ],
            ProjectType.GENERIC: [
                r"def\s+(\w+)\s*\(",  # Python
                r"function\s+(\w+)\s*\(",  # JavaScript
                r"func\s+(\w+)\s*\(",  # Go
            ],
        }

        for pattern in patterns.get(project_type, patterns[ProjectType.GENERIC]):
            matches = re.findall(pattern, diff_content)
            functions.extend(matches)

        return list(set(functions))

    def _extract_components_from_diff(self, diff_content: str) -> list[str]:
        """Extract React component names from diff content."""
        components = []

        patterns = [
            r"(?:export\s+)?(?:default\s+)?(?:function|const)\s+([A-Z]\w+)",  # Function components
            r"class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?Component",  # Class components
        ]

        for pattern in patterns:
            matches = re.findall(pattern, diff_content)
            components.extend(matches)

        return list(set(components))

    def analyze_branch(self, base_branch: str | None = None) -> BranchAnalysis:
        """Analyze the current branch compared to base branch.

        Args:
            base_branch: Branch to compare against. Defaults to main/master.

        Returns:
            BranchAnalysis object with all change information.
        """
        current_branch = self.get_current_branch()
        if base_branch is None:
            base_branch = self.get_default_branch()

        project_type = self.detect_project_type()

        # Get commits unique to current branch
        commits: list[CommitInfo] = []
        try:
            commit_range = f"{base_branch}..{current_branch}"
            for commit in self.repo.iter_commits(commit_range):
                commits.append(
                    CommitInfo(
                        sha=commit.hexsha[:8],
                        message=commit.message.strip(),
                        author=str(commit.author),
                        files_changed=[item.a_path for item in commit.diff(commit.parents[0] if commit.parents else None)],
                    )
                )
        except Exception:
            # Handle case where branches don't share history
            pass

        # Get file changes
        file_changes: list[FileChange] = []
        total_additions = 0
        total_deletions = 0

        try:
            base_commit = self.repo.commit(base_branch)
            head_commit = self.repo.commit(current_branch)
            diffs = base_commit.diff(head_commit, create_patch=True)

            for diff_item in diffs:
                file_path = diff_item.b_path or diff_item.a_path

                if self._should_skip_file(file_path):
                    continue

                # Determine change type
                if diff_item.new_file:
                    change_type = ChangeType.ADDED
                elif diff_item.deleted_file:
                    change_type = ChangeType.DELETED
                elif diff_item.renamed:
                    change_type = ChangeType.RENAMED
                else:
                    change_type = ChangeType.MODIFIED

                # Get diff content
                try:
                    diff_content = diff_item.diff.decode("utf-8", errors="replace")
                except Exception:
                    diff_content = ""

                added, deleted = self._parse_diff_stats(diff_item)
                total_additions += added
                total_deletions += deleted

                # Extract semantic information
                functions = self._extract_functions_from_diff(diff_content, project_type)
                components = self._extract_components_from_diff(diff_content) if project_type == ProjectType.REACT else []

                file_changes.append(
                    FileChange(
                        path=file_path,
                        change_type=change_type,
                        diff_content=diff_content,
                        added_lines=added,
                        deleted_lines=deleted,
                        functions_changed=functions,
                        components_changed=components,
                    )
                )
        except Exception as e:
            # Log error but continue
            print(f"Warning: Could not analyze diff: {e}")

        return BranchAnalysis(
            branch_name=current_branch,
            base_branch=base_branch,
            commits=commits,
            file_changes=file_changes,
            project_type=project_type,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )

    def get_staged_changes(self) -> list[FileChange]:
        """Get currently staged changes."""
        file_changes: list[FileChange] = []
        project_type = self.detect_project_type()

        try:
            diffs = self.repo.index.diff(self.repo.head.commit)
            for diff_item in diffs:
                file_path = diff_item.b_path or diff_item.a_path

                if self._should_skip_file(file_path):
                    continue

                if diff_item.new_file:
                    change_type = ChangeType.ADDED
                elif diff_item.deleted_file:
                    change_type = ChangeType.DELETED
                else:
                    change_type = ChangeType.MODIFIED

                try:
                    diff_content = diff_item.diff.decode("utf-8", errors="replace")
                except Exception:
                    diff_content = ""

                functions = self._extract_functions_from_diff(diff_content, project_type)

                file_changes.append(
                    FileChange(
                        path=file_path,
                        change_type=change_type,
                        diff_content=diff_content,
                        functions_changed=functions,
                    )
                )
        except Exception:
            pass

        return file_changes

    def has_remote(self) -> bool:
        """Check if the repository has a remote configured."""
        try:
            self.repo.remote("origin")
            return True
        except ValueError:
            return False

    def get_existing_mr_branch(self) -> str | None:
        """Get the branch name if it's already pushed to remote."""
        current_branch = self.get_current_branch()
        try:
            remote = self.repo.remote("origin")
            remote.fetch()
            remote_refs = [ref.name for ref in remote.refs]
            if f"origin/{current_branch}" in remote_refs:
                return current_branch
        except Exception:
            pass
        return None
