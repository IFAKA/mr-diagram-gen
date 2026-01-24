"""Mermaid diagram generation using Ollama LLM and templates."""

from __future__ import annotations

import json
import re
from pathlib import Path

import ollama
from jinja2 import Environment, FileSystemLoader

from .config import Config
from .models import (
    BranchAnalysis,
    ChangeType,
    ClassificationResult,
    DiagramType,
    GeneratedDiagram,
    ProjectType,
)


# Mock Mermaid diagrams for testing
MOCK_DIAGRAMS = {
    DiagramType.FLOWCHART: """graph TD
    A[Start] --> B{Check Changes}
    B -->|New Feature| C[Generate Diagram]
    B -->|Bug Fix| D[Skip Diagram]
    C --> E[Compile to Image]
    E --> F[Upload to MR]
    D --> G[End]
    F --> G""",
    DiagramType.SEQUENCE: """sequenceDiagram
    participant U as User
    participant A as API
    participant S as Service
    participant D as Database
    U->>+A: Request
    A->>+S: Process
    S->>+D: Query
    D-->>-S: Result
    S-->>-A: Response
    A-->>-U: Data""",
    DiagramType.COMPONENT: """graph LR
    subgraph Frontend
        A[App] --> B[Components]
        B --> C[Pages]
    end
    subgraph Backend
        D[API] --> E[Services]
        E --> F[Database]
    end
    C --> D""",
}


class DiagramGenerator:
    """Generates Mermaid diagrams for code changes."""

    def __init__(self, config: Config, mock_mode: bool = False):
        """Initialize the diagram generator.

        Args:
            config: Configuration object.
            mock_mode: If True, use mock diagrams instead of calling Ollama.
        """
        self.config = config
        self.mock_mode = mock_mode
        self.client = None if mock_mode else ollama.Client(host=config.ollama.base_url)

        # Set up Jinja2 templates
        template_dir = Path(__file__).parent / "templates"
        if template_dir.exists():
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = None

    def _build_generation_prompt(
        self,
        analysis: BranchAnalysis,
        diagram_type: DiagramType,
    ) -> str:
        """Build the prompt for diagram generation."""
        # Prepare file changes summary
        files_info = []
        for fc in analysis.file_changes[:15]:
            info = {
                "path": fc.path,
                "type": fc.change_type.value,
                "functions": fc.functions_changed[:5],
                "components": fc.components_changed[:5],
            }
            files_info.append(info)

        # Include relevant diff snippets (limited)
        diff_snippets = []
        for fc in analysis.file_changes[:5]:
            if fc.diff_content and len(fc.diff_content) < 2000:
                diff_snippets.append(f"# {fc.path}\n{fc.diff_content[:1000]}")

        prompt = f"""Generate a Mermaid {diagram_type.value} diagram that visualizes the following code changes.

Project Type: {analysis.project_type.value}
Branch: {analysis.branch_name}

Files Changed:
{json.dumps(files_info, indent=2)}

Diff Snippets:
{chr(10).join(diff_snippets) if diff_snippets else "No detailed diff available"}

Requirements:
1. Create a {diagram_type.value} diagram that helps reviewers understand the architectural impact
2. Mark NEW or MODIFIED elements clearly
3. Keep the diagram focused and readable (max 15-20 nodes)
4. Use descriptive but concise labels

For the diagram type:
- flowchart: Show process flow or decision logic
- sequence: Show interactions between components/services
- component: Show module/package dependencies
- er: Show entity relationships (database)
- class: Show class hierarchies and relationships
- state: Show state transitions

Respond with ONLY the Mermaid code, starting with the diagram type declaration (graph, sequenceDiagram, erDiagram, etc.).
Do not include markdown code fences or any explanation."""

        return prompt

    def _clean_mermaid_code(self, code: str) -> str:
        """Clean and validate Mermaid code."""
        # Remove markdown code fences if present
        code = re.sub(r"```mermaid\s*", "", code)
        code = re.sub(r"```\s*$", "", code)
        code = code.strip()

        # Basic validation - check for valid diagram type declaration
        valid_starts = [
            "graph ", "graph\n",
            "flowchart ", "flowchart\n",
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "pie ",
            "gantt",
            "journey",
        ]

        if not any(code.startswith(start) for start in valid_starts):
            # Try to fix common issues
            if "graph" in code.lower() or "flowchart" in code.lower():
                lines = code.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().lower().startswith(("graph", "flowchart")):
                        code = "\n".join(lines[i:])
                        break

        return code

    def _generate_diagram_title(
        self,
        analysis: BranchAnalysis,
        diagram_type: DiagramType,
    ) -> str:
        """Generate a descriptive title for the diagram."""
        type_names = {
            DiagramType.FLOWCHART: "Flow",
            DiagramType.SEQUENCE: "Sequence",
            DiagramType.COMPONENT: "Component",
            DiagramType.ER: "Entity Relationship",
            DiagramType.CLASS: "Class",
            DiagramType.STATE: "State",
        }

        # Try to extract meaningful info from changes
        main_files = [
            Path(fc.path).stem
            for fc in analysis.file_changes[:3]
            if fc.change_type in (ChangeType.ADDED, ChangeType.MODIFIED)
        ]

        if main_files:
            return f"{type_names.get(diagram_type, 'Architecture')} Diagram: {', '.join(main_files)}"

        return f"{type_names.get(diagram_type, 'Architecture')} Diagram - {analysis.branch_name}"

    def generate_diagram(
        self,
        analysis: BranchAnalysis,
        diagram_type: DiagramType,
    ) -> GeneratedDiagram | None:
        """Generate a single Mermaid diagram.

        Args:
            analysis: BranchAnalysis with change information.
            diagram_type: Type of diagram to generate.

        Returns:
            GeneratedDiagram object or None if generation failed.
        """
        if self.mock_mode:
            mermaid_code = MOCK_DIAGRAMS.get(
                diagram_type,
                MOCK_DIAGRAMS[DiagramType.FLOWCHART]
            )
            # Customize mock based on project
            if analysis.project_type == ProjectType.REACT:
                mermaid_code = self._generate_react_mock(analysis)
            elif analysis.project_type == ProjectType.GOLANG:
                mermaid_code = self._generate_golang_mock(analysis)
        else:
            prompt = self._build_generation_prompt(analysis, diagram_type)
            try:
                response = self.client.generate(
                    model=self.config.ollama.model,
                    prompt=prompt,
                    options={"temperature": 0.7},
                )
                mermaid_code = self._clean_mermaid_code(response["response"])
            except Exception as e:
                print(f"Warning: Diagram generation failed: {e}")
                return None

        if not mermaid_code:
            return None

        return GeneratedDiagram(
            diagram_type=diagram_type,
            title=self._generate_diagram_title(analysis, diagram_type),
            mermaid_code=mermaid_code,
            description=f"Visualizes {diagram_type.value} for changes in {analysis.branch_name}",
        )

    def generate_all_diagrams(
        self,
        analysis: BranchAnalysis,
        classification: ClassificationResult,
    ) -> list[GeneratedDiagram]:
        """Generate all recommended diagrams.

        Args:
            analysis: BranchAnalysis with change information.
            classification: ClassificationResult with diagram type recommendations.

        Returns:
            List of generated diagrams.
        """
        diagrams = []

        # Limit number of diagrams
        diagram_types = classification.diagram_types[:self.config.diagrams.max_diagrams]

        for diagram_type in diagram_types:
            diagram = self.generate_diagram(analysis, diagram_type)
            if diagram:
                diagrams.append(diagram)

        return diagrams

    def _generate_react_mock(self, analysis: BranchAnalysis) -> str:
        """Generate a mock React component tree diagram."""
        # Extract components from changes
        components = []
        for fc in analysis.file_changes:
            if fc.components_changed:
                for comp in fc.components_changed:
                    status = "NEW" if fc.change_type == ChangeType.ADDED else "MODIFIED"
                    components.append((comp, status))
            elif fc.change_type == ChangeType.ADDED and "component" in fc.path.lower():
                name = Path(fc.path).stem
                components.append((name, "NEW"))

        if not components:
            components = [("App", ""), ("Component", "MODIFIED")]

        lines = ["graph TD"]
        lines.append("    App[App]")

        for i, (comp, status) in enumerate(components[:8]):
            label = f"{comp} - {status}" if status else comp
            lines.append(f"    App --> {comp}[{label}]")

        return "\n".join(lines)

    def _generate_golang_mock(self, analysis: BranchAnalysis) -> str:
        """Generate a mock Go package dependency diagram."""
        # Extract package info from file paths
        packages = set()
        for fc in analysis.file_changes:
            parts = Path(fc.path).parts
            if len(parts) >= 2:
                pkg = "/".join(parts[:2])
                status = "NEW" if fc.change_type == ChangeType.ADDED else "MODIFIED"
                packages.add((pkg, status))

        if not packages:
            packages = {("cmd/main", ""), ("internal/handler", "MODIFIED")}

        lines = ["graph LR"]
        pkg_list = list(packages)[:8]

        for i, (pkg, status) in enumerate(pkg_list):
            safe_name = pkg.replace("/", "_").replace("-", "_")
            label = f"{pkg} - {status}" if status else pkg
            lines.append(f"    {safe_name}[{label}]")

            # Add some connections
            if i > 0:
                prev_pkg = pkg_list[i-1][0].replace("/", "_").replace("-", "_")
                lines.append(f"    {prev_pkg} --> {safe_name}")

        return "\n".join(lines)
