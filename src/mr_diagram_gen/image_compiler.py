"""Mermaid diagram compilation to images using mermaid-cli (mmdc)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Config
from .models import GeneratedDiagram


class ImageCompiler:
    """Compiles Mermaid diagrams to PNG/SVG images."""

    def __init__(self, config: Config, output_dir: Path | None = None):
        """Initialize the image compiler.

        Args:
            config: Configuration object.
            output_dir: Directory to store compiled images. Defaults to temp dir.
        """
        self.config = config
        self.output_dir = output_dir or Path(tempfile.mkdtemp(prefix="mr-diagrams-"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._mmdc_path: str | None = None

    def _find_mmdc(self) -> str | None:
        """Find the mermaid-cli (mmdc) executable."""
        if self._mmdc_path:
            return self._mmdc_path

        # Check common locations
        paths_to_check = [
            "mmdc",  # In PATH
            "npx mmdc",  # Via npx
            str(Path.home() / "node_modules" / ".bin" / "mmdc"),
            str(Path.cwd() / "node_modules" / ".bin" / "mmdc"),
        ]

        for path in paths_to_check:
            if " " in path:  # npx command
                try:
                    result = subprocess.run(
                        path.split() + ["--version"],
                        capture_output=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        self._mmdc_path = path
                        return path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            else:
                if shutil.which(path):
                    self._mmdc_path = path
                    return path

        return None

    def is_available(self) -> bool:
        """Check if mermaid-cli is available."""
        return self._find_mmdc() is not None

    def install_mmdc(self) -> bool:
        """Attempt to install mermaid-cli via npm."""
        try:
            # Check if npm is available
            if not shutil.which("npm"):
                print("npm not found. Please install Node.js to use mermaid-cli.")
                return False

            print("Installing @mermaid-js/mermaid-cli...")
            result = subprocess.run(
                ["npm", "install", "-g", "@mermaid-js/mermaid-cli"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("mermaid-cli installed successfully.")
                self._mmdc_path = None  # Reset to re-find
                return self.is_available()
            else:
                print(f"Failed to install mermaid-cli: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Installation timed out.")
            return False
        except Exception as e:
            print(f"Error installing mermaid-cli: {e}")
            return False

    def compile_diagram(
        self,
        diagram: GeneratedDiagram,
        output_format: str = "png",
    ) -> Path | None:
        """Compile a single Mermaid diagram to an image.

        Args:
            diagram: GeneratedDiagram with Mermaid code.
            output_format: Output format ('png' or 'svg').

        Returns:
            Path to the compiled image, or None if compilation failed.
        """
        mmdc = self._find_mmdc()
        if not mmdc:
            print("mermaid-cli (mmdc) not found. Run 'mr-diagram-gen install-deps' to install.")
            return None

        # Create a safe filename from the title
        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in diagram.title
        )[:50]
        output_filename = f"{safe_title}.{output_format}"
        output_path = self.output_dir / output_filename

        # Write Mermaid code to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".mmd",
            delete=False
        ) as f:
            f.write(diagram.mermaid_code)
            input_path = Path(f.name)

        try:
            # Build command
            if " " in mmdc:  # npx command
                cmd = mmdc.split()
            else:
                cmd = [mmdc]

            cmd.extend([
                "-i", str(input_path),
                "-o", str(output_path),
                "-b", "transparent",
                "--scale", "2",
            ])

            # Add puppeteer config for headless rendering
            puppeteer_config = {
                "args": ["--no-sandbox", "--disable-setuid-sandbox"]
            }

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and output_path.exists():
                diagram.image_path = output_path
                return output_path
            else:
                print(f"Diagram compilation failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("Diagram compilation timed out.")
            return None
        except Exception as e:
            print(f"Error compiling diagram: {e}")
            return None
        finally:
            # Clean up temp file
            input_path.unlink(missing_ok=True)

    def compile_all(
        self,
        diagrams: list[GeneratedDiagram],
    ) -> list[GeneratedDiagram]:
        """Compile all diagrams to images.

        Args:
            diagrams: List of GeneratedDiagram objects.

        Returns:
            List of diagrams with image_path set (only successful compilations).
        """
        compiled = []
        formats = self.config.diagrams.format

        for diagram in diagrams:
            for fmt in formats:
                path = self.compile_diagram(diagram, fmt)
                if path:
                    compiled.append(diagram)
                    break  # Only need one successful format

        return compiled

    def cleanup(self) -> None:
        """Remove temporary diagram files."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)

    def get_output_dir(self) -> Path:
        """Get the output directory path."""
        return self.output_dir


class MockImageCompiler(ImageCompiler):
    """Mock image compiler for testing without mermaid-cli."""

    def __init__(self, config: Config, output_dir: Path | None = None):
        super().__init__(config, output_dir)

    def is_available(self) -> bool:
        return True

    def compile_diagram(
        self,
        diagram: GeneratedDiagram,
        output_format: str = "png",
    ) -> Path | None:
        """Create a mock image file."""
        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in diagram.title
        )[:50]
        output_filename = f"{safe_title}.{output_format}"
        output_path = self.output_dir / output_filename

        # Create a placeholder file
        output_path.write_text(f"Mock diagram: {diagram.title}\n\n{diagram.mermaid_code}")
        diagram.image_path = output_path
        return output_path
