"""GitLab API client for MR operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gitlab
from gitlab.exceptions import GitlabError

from .config import Config
from .models import GeneratedDiagram, MRDescription, RemoteInfo


class GitLabClient:
    """Client for GitLab API operations."""

    def __init__(self, config: Config, remote_info: RemoteInfo):
        """Initialize the GitLab client.

        Args:
            config: Configuration object.
            remote_info: Remote repository information.
        """
        self.config = config
        self.remote_info = remote_info
        self._client: gitlab.Gitlab | None = None
        self._project: Any | None = None

    def _get_client(self) -> gitlab.Gitlab:
        """Get or create the GitLab client."""
        if self._client is None:
            token = self.config.gitlab.get_token()
            if not token:
                raise ValueError(
                    "GitLab token not found. Set GITLAB_TOKEN environment variable "
                    "or configure in ~/.config/mr-diagram/config.yaml"
                )
            self._client = gitlab.Gitlab(
                url=self.config.gitlab.url,
                private_token=token,
            )
        return self._client

    def _get_project(self) -> Any:
        """Get the GitLab project."""
        if self._project is None:
            client = self._get_client()
            project_path = f"{self.remote_info.owner}/{self.remote_info.repo}"
            self._project = client.projects.get(project_path)
        return self._project

    def upload_image(self, image_path: Path) -> str | None:
        """Upload an image to GitLab as a project attachment.

        Args:
            image_path: Path to the image file.

        Returns:
            URL of the uploaded image, or None if upload failed.
        """
        try:
            project = self._get_project()
            with open(image_path, "rb") as f:
                upload = project.upload(image_path.name, f)
            return upload["url"]
        except GitlabError as e:
            print(f"Failed to upload image: {e}")
            return None
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None

    def upload_diagrams(
        self,
        diagrams: list[GeneratedDiagram],
    ) -> list[str]:
        """Upload all diagram images to GitLab.

        Args:
            diagrams: List of diagrams with image_path set.

        Returns:
            List of uploaded image URLs.
        """
        urls = []
        for diagram in diagrams:
            if diagram.image_path and diagram.image_path.exists():
                url = self.upload_image(diagram.image_path)
                if url:
                    urls.append(url)
        return urls

    def find_existing_mr(self, source_branch: str, target_branch: str) -> Any | None:
        """Find an existing MR for the given branches.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.

        Returns:
            MR object if found, None otherwise.
        """
        try:
            project = self._get_project()
            mrs = project.mergerequests.list(
                source_branch=source_branch,
                target_branch=target_branch,
                state="opened",
            )
            return mrs[0] if mrs else None
        except GitlabError:
            return None

    def create_mr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
    ) -> str | None:
        """Create a new merge request.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.
            title: MR title.
            description: MR description (markdown).

        Returns:
            URL of the created MR, or None if creation failed.
        """
        try:
            project = self._get_project()
            mr = project.mergerequests.create({
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            })
            return mr.web_url
        except GitlabError as e:
            print(f"Failed to create MR: {e}")
            return None

    def update_mr(
        self,
        mr_iid: int,
        description: str | None = None,
        title: str | None = None,
    ) -> bool:
        """Update an existing merge request.

        Args:
            mr_iid: MR internal ID.
            description: New description (optional).
            title: New title (optional).

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            project = self._get_project()
            mr = project.mergerequests.get(mr_iid)

            if description is not None:
                mr.description = description
            if title is not None:
                mr.title = title

            mr.save()
            return True
        except GitlabError as e:
            print(f"Failed to update MR: {e}")
            return False

    def create_or_update_mr(
        self,
        source_branch: str,
        target_branch: str,
        mr_description: MRDescription,
    ) -> str | None:
        """Create a new MR or update existing one.

        Args:
            source_branch: Source branch name.
            target_branch: Target branch name.
            mr_description: MR description with diagrams.

        Returns:
            URL of the MR, or None if operation failed.
        """
        # Upload images first
        image_urls = self.upload_diagrams(mr_description.diagrams)

        # Build description with embedded images
        description = mr_description.body

        if image_urls:
            description += "\n\n## Architecture Diagrams\n\n"
            for i, (url, diagram) in enumerate(zip(image_urls, mr_description.diagrams)):
                description += f"### {diagram.title}\n\n"
                description += f"![{diagram.title}]({url})\n\n"
                if diagram.description:
                    description += f"_{diagram.description}_\n\n"

        # Check for existing MR
        existing_mr = self.find_existing_mr(source_branch, target_branch)

        if existing_mr:
            success = self.update_mr(existing_mr.iid, description=description)
            if success:
                return existing_mr.web_url
            return None
        else:
            return self.create_mr(
                source_branch=source_branch,
                target_branch=target_branch,
                title=mr_description.title,
                description=description,
            )

    def test_connection(self) -> bool:
        """Test the GitLab connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            client = self._get_client()
            client.auth()
            return True
        except Exception as e:
            print(f"GitLab connection failed: {e}")
            return False
