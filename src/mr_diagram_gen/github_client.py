"""GitHub API client for PR operations."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from github import Github, GithubException

from .config import Config
from .models import GeneratedDiagram, MRDescription, RemoteInfo


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, config: Config, remote_info: RemoteInfo):
        """Initialize the GitHub client.

        Args:
            config: Configuration object.
            remote_info: Remote repository information.
        """
        self.config = config
        self.remote_info = remote_info
        self._client: Github | None = None
        self._repo: Any | None = None

    def _get_client(self) -> Github:
        """Get or create the GitHub client."""
        if self._client is None:
            token = self.config.github.get_token()
            if not token:
                raise ValueError(
                    "GitHub token not found. Set GITHUB_TOKEN environment variable "
                    "or configure in ~/.config/mr-diagram/config.yaml"
                )
            self._client = Github(token)
        return self._client

    def _get_repo(self) -> Any:
        """Get the GitHub repository."""
        if self._repo is None:
            client = self._get_client()
            repo_path = f"{self.remote_info.owner}/{self.remote_info.repo}"
            self._repo = client.get_repo(repo_path)
        return self._repo

    def upload_image_to_gist(self, image_path: Path, description: str = "") -> str | None:
        """Upload an image to a GitHub Gist.

        Args:
            image_path: Path to the image file.
            description: Description for the gist.

        Returns:
            Raw URL of the uploaded image, or None if upload failed.
        """
        try:
            client = self._get_client()
            user = client.get_user()

            # Read and base64 encode the image
            with open(image_path, "rb") as f:
                content = base64.b64encode(f.read()).decode()

            # Create a gist with the image
            gist = user.create_gist(
                public=False,
                files={
                    image_path.name: github.InputFileContent(content)
                },
                description=description or f"MR Diagram: {image_path.stem}",
            )

            # Return the raw URL
            return gist.files[image_path.name].raw_url

        except GithubException as e:
            print(f"Failed to upload image to gist: {e}")
            return None
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None

    def upload_image_as_comment_attachment(
        self,
        image_path: Path,
        pr_number: int,
    ) -> str | None:
        """Upload image by creating a comment with the image.

        Note: GitHub doesn't have a direct attachment API, so we use
        an alternative approach - embedding base64 or using external hosting.

        Args:
            image_path: Path to the image file.
            pr_number: PR number to attach to.

        Returns:
            URL or reference to the image.
        """
        # For now, we'll use the Mermaid code directly in GitHub
        # since GitHub renders Mermaid natively in markdown
        return None

    def upload_diagrams(
        self,
        diagrams: list[GeneratedDiagram],
    ) -> list[str]:
        """Upload diagram images (or return empty if using native Mermaid).

        Args:
            diagrams: List of diagrams.

        Returns:
            List of image URLs (empty if using native Mermaid).
        """
        if self.config.github.image_storage == "gist":
            urls = []
            for diagram in diagrams:
                if diagram.image_path and diagram.image_path.exists():
                    url = self.upload_image_to_gist(
                        diagram.image_path,
                        diagram.description,
                    )
                    if url:
                        urls.append(url)
            return urls

        # For 'comment' mode, we'll embed Mermaid directly
        return []

    def find_existing_pr(self, source_branch: str, target_branch: str) -> Any | None:
        """Find an existing PR for the given branches.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.

        Returns:
            PR object if found, None otherwise.
        """
        try:
            repo = self._get_repo()
            pulls = repo.get_pulls(
                state="open",
                head=f"{self.remote_info.owner}:{source_branch}",
                base=target_branch,
            )
            for pr in pulls:
                return pr
            return None
        except GithubException:
            return None

    def create_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
    ) -> str | None:
        """Create a new pull request.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.
            title: PR title.
            description: PR description (markdown).

        Returns:
            URL of the created PR, or None if creation failed.
        """
        try:
            repo = self._get_repo()
            pr = repo.create_pull(
                title=title,
                body=description,
                head=source_branch,
                base=target_branch,
            )
            return pr.html_url
        except GithubException as e:
            print(f"Failed to create PR: {e}")
            return None

    def update_pr(
        self,
        pr_number: int,
        description: str | None = None,
        title: str | None = None,
    ) -> bool:
        """Update an existing pull request.

        Args:
            pr_number: PR number.
            description: New description (optional).
            title: New title (optional).

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            repo = self._get_repo()
            pr = repo.get_pull(pr_number)

            if description is not None:
                pr.edit(body=description)
            if title is not None:
                pr.edit(title=title)

            return True
        except GithubException as e:
            print(f"Failed to update PR: {e}")
            return False

    def _build_description_with_diagrams(
        self,
        mr_description: MRDescription,
        image_urls: list[str],
    ) -> str:
        """Build PR description with embedded diagrams.

        Args:
            mr_description: MR description object.
            image_urls: List of uploaded image URLs.

        Returns:
            Formatted markdown description.
        """
        description = mr_description.body

        if mr_description.diagrams:
            description += "\n\n## Architecture Diagrams\n\n"

            for i, diagram in enumerate(mr_description.diagrams):
                description += f"### {diagram.title}\n\n"

                # GitHub supports native Mermaid rendering
                if not image_urls or i >= len(image_urls):
                    # Use native Mermaid
                    description += f"```mermaid\n{diagram.mermaid_code}\n```\n\n"
                else:
                    # Use uploaded image
                    description += f"![{diagram.title}]({image_urls[i]})\n\n"

                if diagram.description:
                    description += f"_{diagram.description}_\n\n"

        return description

    def create_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        mr_description: MRDescription,
    ) -> str | None:
        """Create a new PR or update existing one.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.
            mr_description: MR description with diagrams.

        Returns:
            URL of the PR, or None if operation failed.
        """
        # Upload images if configured
        image_urls = self.upload_diagrams(mr_description.diagrams)

        # Build description with diagrams
        description = self._build_description_with_diagrams(mr_description, image_urls)

        # Check for existing PR
        existing_pr = self.find_existing_pr(source_branch, target_branch)

        if existing_pr:
            success = self.update_pr(existing_pr.number, description=description)
            if success:
                return existing_pr.html_url
            return None
        else:
            return self.create_pr(
                source_branch=source_branch,
                target_branch=target_branch,
                title=mr_description.title,
                description=description,
            )

    def test_connection(self) -> bool:
        """Test the GitHub connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            client = self._get_client()
            user = client.get_user()
            _ = user.login  # Trigger authentication
            return True
        except Exception as e:
            print(f"GitHub connection failed: {e}")
            return False
