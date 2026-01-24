"""CLI entry point for mr-diagram-gen."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import __version__
from .change_classifier import ChangeClassifier
from .config import (
    Config,
    create_default_config,
    get_global_config_path,
    get_project_config_path,
    load_config,
    save_config,
)
from .diagram_generator import DiagramGenerator
from .git_analyzer import GitAnalyzer
from .github_client import GitHubClient
from .gitlab_client import GitLabClient
from .image_compiler import ImageCompiler, MockImageCompiler
from .models import MRDescription, Platform

app = typer.Typer(
    name="mr-diagram-gen",
    help="Generate Mermaid diagrams for GitLab MRs and GitHub PRs",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"mr-diagram-gen version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """MR/PR Diagram Generator - Generate architecture diagrams for code reviews."""
    pass


@app.command()
def init() -> None:
    """Initialize configuration files."""
    global_path = get_global_config_path()

    if global_path.exists():
        if not typer.confirm(f"Config already exists at {global_path}. Overwrite?"):
            raise typer.Exit()

    config = create_default_config()
    save_config(config, global_path)
    console.print(f"[green]Created configuration at {global_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Set GITLAB_TOKEN or GITHUB_TOKEN environment variable")
    console.print("2. Ensure Ollama is running with a code model (e.g., codellama:13b)")
    console.print("3. Run 'mr-diagram-gen analyze' in your git repository")


@app.command()
def analyze(
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Local mode - analyze and generate diagrams without creating MR/PR",
    ),
    mock_llm: bool = typer.Option(
        False,
        "--mock-llm",
        help="Use mock LLM responses (for testing without Ollama)",
    ),
    base_branch: Optional[str] = typer.Option(
        None,
        "--base",
        "-b",
        help="Base branch to compare against (default: main/master)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be generated without creating files",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for diagrams (default: .mr-diagrams-preview)",
    ),
) -> None:
    """Analyze current branch and generate diagrams."""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)

    # Initialize git analyzer
    try:
        git_analyzer = GitAnalyzer(config=config)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze branch
        task = progress.add_task("Analyzing git changes...", total=None)
        analysis = git_analyzer.analyze_branch(base_branch)
        progress.update(task, completed=True)

        if not analysis.file_changes:
            console.print("[yellow]No significant changes found to analyze.[/yellow]")
            raise typer.Exit()

        # Display analysis summary
        _display_analysis_summary(analysis)

        # Classify changes
        progress.add_task("Classifying changes...", total=None)
        classifier = ChangeClassifier(config, mock_mode=mock_llm)
        classification = classifier.classify(analysis)

        if not classification.needs_diagram:
            console.print(
                f"\n[yellow]Diagrams not needed: {classification.reason}[/yellow]"
            )
            if not typer.confirm("Generate diagrams anyway?", default=False):
                raise typer.Exit()

        # Display classification
        _display_classification(classification)

        if dry_run:
            console.print("\n[cyan]Dry run - no diagrams generated.[/cyan]")
            raise typer.Exit()

        # Generate diagrams
        progress.add_task("Generating Mermaid diagrams...", total=None)
        generator = DiagramGenerator(config, mock_mode=mock_llm)
        diagrams = generator.generate_all_diagrams(analysis, classification)

        if not diagrams:
            console.print("[red]Failed to generate any diagrams.[/red]")
            raise typer.Exit(1)

        # Compile to images
        progress.add_task("Compiling diagrams to images...", total=None)
        out_path = Path(output_dir) if output_dir else Path(".mr-diagrams-preview")
        compiler = MockImageCompiler(config, out_path) if mock_llm else ImageCompiler(config, out_path)

        if not mock_llm and not compiler.is_available():
            console.print(
                "[yellow]mermaid-cli not found. Using mock compiler.[/yellow]"
            )
            compiler = MockImageCompiler(config, out_path)

        compiled = compiler.compile_all(diagrams)

    # Display results
    console.print(f"\n[green]Generated {len(compiled)} diagram(s)[/green]")

    table = Table(title="Generated Diagrams")
    table.add_column("Type", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("File", style="blue")

    for diagram in compiled:
        table.add_row(
            diagram.diagram_type.value,
            diagram.title,
            str(diagram.image_path) if diagram.image_path else "N/A",
        )

    console.print(table)

    if local:
        console.print(f"\n[cyan]Diagrams saved to: {out_path}[/cyan]")
        console.print("Run 'mr-diagram-gen preview' to view them.")


@app.command()
def push(
    base_branch: Optional[str] = typer.Option(
        None,
        "--base",
        "-b",
        help="Base branch to compare against (default: main/master)",
    ),
    mock_llm: bool = typer.Option(
        False,
        "--mock-llm",
        help="Use mock LLM responses (for testing)",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="MR/PR title (default: auto-generated from branch name)",
    ),
) -> None:
    """Generate diagrams and create/update MR or PR."""
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)

    # Initialize git analyzer
    try:
        git_analyzer = GitAnalyzer(config=config)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Check remote
    remote_info = git_analyzer.detect_remote_platform()
    if remote_info.platform == Platform.UNKNOWN:
        console.print("[red]Could not detect git platform from remote URL.[/red]")
        console.print("Supported platforms: GitLab, GitHub")
        raise typer.Exit(1)

    console.print(f"[cyan]Detected platform: {remote_info.platform.value}[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze branch
        progress.add_task("Analyzing git changes...", total=None)
        analysis = git_analyzer.analyze_branch(base_branch)

        if not analysis.file_changes:
            console.print("[yellow]No changes found.[/yellow]")
            raise typer.Exit()

        # Classify and generate
        progress.add_task("Classifying changes...", total=None)
        classifier = ChangeClassifier(config, mock_mode=mock_llm)
        classification = classifier.classify(analysis)

        progress.add_task("Generating diagrams...", total=None)
        generator = DiagramGenerator(config, mock_mode=mock_llm)
        diagrams = generator.generate_all_diagrams(analysis, classification)

        # Compile images
        progress.add_task("Compiling diagrams...", total=None)
        compiler = ImageCompiler(config) if not mock_llm else MockImageCompiler(config)
        compiled = compiler.compile_all(diagrams)

        # Build MR description
        mr_title = title or f"[{analysis.project_type.value.upper()}] {analysis.branch_name.replace('-', ' ').replace('_', ' ').title()}"

        mr_description = MRDescription(
            title=mr_title,
            body=_build_mr_body(analysis, classification),
            diagrams=compiled,
        )

        # Create/update MR or PR
        progress.add_task(f"Creating {remote_info.platform.value} MR/PR...", total=None)

        if remote_info.platform == Platform.GITLAB:
            client = GitLabClient(config, remote_info)
        else:
            client = GitHubClient(config, remote_info)

        try:
            url = client.create_or_update_pr(
                source_branch=analysis.branch_name,
                target_branch=analysis.base_branch,
                mr_description=mr_description,
            )
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    if url:
        console.print(f"\n[green]MR/PR created/updated successfully![/green]")
        console.print(f"[cyan]{url}[/cyan]")
    else:
        console.print("[red]Failed to create/update MR/PR.[/red]")
        raise typer.Exit(1)


@app.command()
def preview(
    directory: Optional[str] = typer.Option(
        None,
        "--dir",
        "-d",
        help="Directory containing diagrams (default: .mr-diagrams-preview)",
    ),
) -> None:
    """Open generated diagrams in default viewer."""
    dir_path = Path(directory) if directory else Path(".mr-diagrams-preview")

    if not dir_path.exists():
        console.print(f"[red]Directory not found: {dir_path}[/red]")
        console.print("Run 'mr-diagram-gen analyze --local' first to generate diagrams.")
        raise typer.Exit(1)

    files = list(dir_path.glob("*.png")) + list(dir_path.glob("*.svg"))

    if not files:
        console.print(f"[yellow]No diagram images found in {dir_path}[/yellow]")
        raise typer.Exit()

    console.print(f"[cyan]Found {len(files)} diagram(s)[/cyan]")

    for f in files:
        console.print(f"  - {f.name}")
        webbrowser.open(f"file://{f.absolute()}")

    console.print("\n[green]Opened diagrams in default viewer.[/green]")


@app.command("install-hook")
def install_hook(
    pre_push: bool = typer.Option(
        True,
        "--pre-push/--no-pre-push",
        help="Install as pre-push hook",
    ),
) -> None:
    """Install git hook for automatic diagram generation."""
    git_dir = Path.cwd() / ".git"
    if not git_dir.exists():
        console.print("[red]Not a git repository.[/red]")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-push"
    hook_content = """#!/bin/bash
# MR Diagram Generator pre-push hook

# Check if mr-diagram-gen is installed
if ! command -v mr-diagram-gen &> /dev/null; then
    echo "Warning: mr-diagram-gen not found. Skipping diagram generation."
    exit 0
fi

# Run analysis (non-blocking)
echo "Running MR diagram analysis..."
mr-diagram-gen analyze --local 2>&1 || true

# Always allow push to continue
exit 0
"""

    if hook_path.exists():
        if not typer.confirm(f"Pre-push hook already exists. Overwrite?"):
            raise typer.Exit()

    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)

    console.print(f"[green]Installed pre-push hook at {hook_path}[/green]")


@app.command("install-deps")
def install_deps() -> None:
    """Install external dependencies (mermaid-cli)."""
    import shutil
    import subprocess

    if not shutil.which("npm"):
        console.print("[red]npm not found. Please install Node.js first.[/red]")
        raise typer.Exit(1)

    console.print("[cyan]Installing @mermaid-js/mermaid-cli...[/cyan]")

    try:
        result = subprocess.run(
            ["npm", "install", "-g", "@mermaid-js/mermaid-cli"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print("[green]mermaid-cli installed successfully![/green]")
        else:
            console.print(f"[red]Installation failed: {result.stderr}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Check tool status and configuration."""
    import shutil

    console.print(Panel.fit("MR Diagram Generator Status", style="bold blue"))

    # Check config
    global_config = get_global_config_path()
    project_config = get_project_config_path()

    table = Table(title="Configuration")
    table.add_column("Item", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Path/Value")

    table.add_row(
        "Global config",
        "[green]Found[/green]" if global_config.exists() else "[yellow]Not found[/yellow]",
        str(global_config),
    )
    table.add_row(
        "Project config",
        "[green]Found[/green]" if project_config.exists() else "[dim]Not found[/dim]",
        str(project_config),
    )

    console.print(table)

    # Check dependencies
    table2 = Table(title="Dependencies")
    table2.add_column("Dependency", style="cyan")
    table2.add_column("Status")

    # Check mmdc
    mmdc_found = shutil.which("mmdc") is not None
    table2.add_row(
        "mermaid-cli (mmdc)",
        "[green]Installed[/green]" if mmdc_found else "[yellow]Not installed[/yellow]",
    )

    # Check npm
    npm_found = shutil.which("npm") is not None
    table2.add_row(
        "npm",
        "[green]Found[/green]" if npm_found else "[red]Not found[/red]",
    )

    console.print(table2)

    # Check git
    try:
        git_analyzer = GitAnalyzer()
        remote_info = git_analyzer.detect_remote_platform()

        table3 = Table(title="Git Repository")
        table3.add_column("Item", style="cyan")
        table3.add_column("Value")

        table3.add_row("Current branch", git_analyzer.get_current_branch())
        table3.add_row("Default branch", git_analyzer.get_default_branch())
        table3.add_row("Project type", git_analyzer.detect_project_type().value)
        table3.add_row("Platform", remote_info.platform.value)
        table3.add_row("Remote", f"{remote_info.owner}/{remote_info.repo}")

        console.print(table3)
    except ValueError:
        console.print("[yellow]Not in a git repository[/yellow]")


def _display_analysis_summary(analysis) -> None:
    """Display analysis summary."""
    table = Table(title=f"Branch Analysis: {analysis.branch_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Base branch", analysis.base_branch)
    table.add_row("Project type", analysis.project_type.value)
    table.add_row("Files changed", str(len(analysis.file_changes)))
    table.add_row("Commits", str(len(analysis.commits)))
    table.add_row("Lines added", f"+{analysis.total_additions}")
    table.add_row("Lines deleted", f"-{analysis.total_deletions}")

    console.print(table)


def _display_classification(classification) -> None:
    """Display classification result."""
    console.print(f"\n[cyan]Classification Result:[/cyan]")
    console.print(f"  Needs diagram: {'Yes' if classification.needs_diagram else 'No'}")
    console.print(f"  Confidence: {classification.confidence:.0%}")
    console.print(f"  Reason: {classification.reason}")

    if classification.diagram_types:
        console.print(f"  Diagram types: {', '.join(dt.value for dt in classification.diagram_types)}")


def _build_mr_body(analysis, classification) -> str:
    """Build the MR/PR body text."""
    body = "## Summary\n\n"
    body += f"This MR includes changes across {len(analysis.file_changes)} file(s).\n\n"

    # Add commit summary
    if analysis.commits:
        body += "### Commits\n\n"
        for commit in analysis.commits[:5]:
            body += f"- `{commit.sha}`: {commit.message.split(chr(10))[0]}\n"
        if len(analysis.commits) > 5:
            body += f"- ... and {len(analysis.commits) - 5} more\n"
        body += "\n"

    # Add change summary
    body += "### Changes\n\n"
    body += f"- **Lines added**: +{analysis.total_additions}\n"
    body += f"- **Lines deleted**: -{analysis.total_deletions}\n"
    body += f"- **Project type**: {analysis.project_type.value}\n\n"

    return body


if __name__ == "__main__":
    app()
