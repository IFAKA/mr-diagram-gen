"""Change classification using Ollama LLM."""

from __future__ import annotations

import json
import re
from typing import Any

import ollama

from .config import Config
from .models import BranchAnalysis, ClassificationResult, DiagramType, FileChange, ProjectType


# Mock responses for testing without Ollama
MOCK_RESPONSES = {
    "classify": {
        "needs_diagram": True,
        "diagram_types": ["flowchart", "component"],
        "reason": "Changes involve multiple components and new functionality",
        "confidence": 0.8,
    },
    "no_diagram": {
        "needs_diagram": False,
        "diagram_types": [],
        "reason": "Simple configuration or documentation changes",
        "confidence": 0.9,
    },
}


class ChangeClassifier:
    """Classifies code changes to determine if diagrams are needed."""

    def __init__(self, config: Config, mock_mode: bool = False):
        """Initialize the classifier.

        Args:
            config: Configuration object.
            mock_mode: If True, use mock responses instead of calling Ollama.
        """
        self.config = config
        self.mock_mode = mock_mode
        self.client = None if mock_mode else ollama.Client(host=config.ollama.base_url)

    def _build_classification_prompt(self, analysis: BranchAnalysis) -> str:
        """Build the prompt for change classification."""
        # Summarize changes
        files_summary = []
        for fc in analysis.file_changes[:20]:  # Limit to 20 files
            change_desc = f"- {fc.path} ({fc.change_type.value})"
            if fc.functions_changed:
                change_desc += f" [functions: {', '.join(fc.functions_changed[:5])}]"
            if fc.components_changed:
                change_desc += f" [components: {', '.join(fc.components_changed[:5])}]"
            files_summary.append(change_desc)

        commits_summary = [f"- {c.sha}: {c.message[:100]}" for c in analysis.commits[:10]]

        prompt = f"""Analyze the following code changes and determine if architectural diagrams would help reviewers understand the changes.

Project Type: {analysis.project_type.value}
Branch: {analysis.branch_name} (comparing to {analysis.base_branch})
Total: +{analysis.total_additions} / -{analysis.total_deletions} lines

Files Changed:
{chr(10).join(files_summary) if files_summary else "No significant files changed"}

Recent Commits:
{chr(10).join(commits_summary) if commits_summary else "No commits"}

Based on these changes, respond with a JSON object:
{{
    "needs_diagram": true/false,
    "diagram_types": ["flowchart", "sequence", "component", "er", "class", "state"],
    "reason": "Brief explanation of why diagrams are/aren't needed",
    "confidence": 0.0-1.0
}}

Consider:
- Diagrams are NEEDED for: new features with multiple components, API changes, database/schema changes, refactoring, new modules, complex algorithms
- Diagrams are NOT needed for: bug fixes, config changes, docs updates, test additions only, dependency bumps, simple single-file changes

Respond with ONLY the JSON object, no other text."""

        return prompt

    def _parse_classification_response(self, response: str) -> ClassificationResult:
        """Parse the LLM response into a ClassificationResult."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            diagram_types = []
            for dt in data.get("diagram_types", []):
                try:
                    diagram_types.append(DiagramType(dt))
                except ValueError:
                    continue

            return ClassificationResult(
                needs_diagram=data.get("needs_diagram", False),
                diagram_types=diagram_types,
                reason=data.get("reason", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Default to no diagram on parse error
            return ClassificationResult(
                needs_diagram=False,
                diagram_types=[],
                reason=f"Could not parse LLM response: {e}",
                confidence=0.0,
            )

    def _is_trivial_change(self, analysis: BranchAnalysis) -> bool:
        """Check if changes are trivial and don't need LLM classification."""
        # No files changed
        if not analysis.file_changes:
            return True

        # Only documentation or config files
        trivial_extensions = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".lock"}
        all_trivial = all(
            any(fc.path.endswith(ext) for ext in trivial_extensions)
            for fc in analysis.file_changes
        )
        if all_trivial:
            return True

        # Very small changes (less than 10 lines total)
        if analysis.total_additions + analysis.total_deletions < 10:
            return True

        return False

    def classify(self, analysis: BranchAnalysis) -> ClassificationResult:
        """Classify changes to determine if diagrams are needed.

        Args:
            analysis: BranchAnalysis object with change information.

        Returns:
            ClassificationResult indicating if diagrams are needed.
        """
        # Check for always_diagram patterns FIRST (these override trivial detection)
        for fc in analysis.file_changes:
            for pattern in self.config.rules.always_diagram:
                if self._match_pattern(fc.path, pattern):
                    return ClassificationResult(
                        needs_diagram=True,
                        diagram_types=self._suggest_diagram_types(analysis),
                        reason=f"File matches always_diagram pattern: {pattern}",
                        confidence=0.9,
                    )

        # Quick check for trivial changes
        if self._is_trivial_change(analysis):
            return ClassificationResult(
                needs_diagram=False,
                diagram_types=[],
                reason="Trivial changes detected (docs, config, or very small)",
                confidence=0.95,
            )

        if self.mock_mode:
            # Use mock response based on change size
            if analysis.total_additions + analysis.total_deletions > 50:
                mock_data = MOCK_RESPONSES["classify"]
            else:
                mock_data = MOCK_RESPONSES["no_diagram"]

            return ClassificationResult(
                needs_diagram=mock_data["needs_diagram"],
                diagram_types=[DiagramType(dt) for dt in mock_data["diagram_types"]],
                reason=mock_data["reason"],
                confidence=mock_data["confidence"],
            )

        # Call Ollama for classification
        prompt = self._build_classification_prompt(analysis)
        try:
            response = self.client.generate(
                model=self.config.ollama.model,
                prompt=prompt,
                options={"temperature": 0.3},
            )
            return self._parse_classification_response(response["response"])
        except Exception as e:
            return ClassificationResult(
                needs_diagram=False,
                diagram_types=[],
                reason=f"LLM classification failed: {e}",
                confidence=0.0,
            )

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _suggest_diagram_types(self, analysis: BranchAnalysis) -> list[DiagramType]:
        """Suggest diagram types based on project type and changes."""
        suggestions = []

        if analysis.project_type == ProjectType.REACT:
            if any(fc.components_changed for fc in analysis.file_changes):
                suggestions.append(DiagramType.COMPONENT)
            suggestions.append(DiagramType.FLOWCHART)

        elif analysis.project_type == ProjectType.GOLANG:
            suggestions.append(DiagramType.COMPONENT)  # Package deps
            if any("handler" in fc.path.lower() for fc in analysis.file_changes):
                suggestions.append(DiagramType.SEQUENCE)

        elif analysis.project_type == ProjectType.NODEJS:
            if any("route" in fc.path.lower() or "api" in fc.path.lower() for fc in analysis.file_changes):
                suggestions.append(DiagramType.SEQUENCE)
            suggestions.append(DiagramType.FLOWCHART)

        else:
            suggestions.append(DiagramType.FLOWCHART)

        return suggestions[:3]  # Limit to 3 diagram types
