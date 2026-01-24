# mr-diagram-gen

Auto-generate architecture diagrams for your merge requests / pull requests.

Analyzes your code changes, decides if diagrams would help reviewers understand them, and generates Mermaid diagrams compiled to images.

## Install

```bash
pip install mr-diagram-gen
```

Or install from source:
```bash
git clone https://github.com/IFAKA/mr-diagram-gen.git
cd mr-diagram-gen
pip install .
```

### Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running locally with a code model
- Node.js (for diagram rendering)

```bash
# Install Ollama (macOS)
brew install ollama

# Pull a code model
ollama pull codellama:13b

# Install mermaid diagram renderer
npm install -g @mermaid-js/mermaid-cli
# or just run: mr-diagram-gen install-deps
```

## Uninstall

```bash
# Remove the package
pip uninstall mr-diagram-gen

# Remove config (optional)
rm -rf ~/.config/mr-diagram

# Remove mermaid-cli (optional)
npm uninstall -g @mermaid-js/mermaid-cli
```

Zero traces left.

## Usage

```bash
# In any git repo, on a feature branch:
mr-diagram-gen analyze --local
```

That's it. It will:
1. Detect your project type (React, Node, Go, TypeScript, etc)
2. Analyze what changed vs the main branch
3. Ask the LLM if diagrams would help
4. Generate Mermaid diagrams
5. Compile them to PNG images
6. Save to `.mr-diagrams-preview/`

### Commands

| Command | What it does |
|---------|--------------|
| `analyze --local` | Generate diagrams locally (no MR/PR) |
| `analyze --local --mock-llm` | Same but skip Ollama (for testing) |
| `push` | Generate + create/update GitLab MR or GitHub PR |
| `preview` | Open generated diagrams |
| `status` | Check if everything's set up |
| `init` | Create config file |
| `install-deps` | Install mermaid-cli |
| `install-hook` | Add git pre-push hook |

### Flags

| Flag | What it does |
|------|--------------|
| `--local` | Don't create MR/PR, just generate locally |
| `--mock-llm` | Use fake LLM responses (no Ollama needed) |
| `--dry-run` | Show what would happen without doing it |
| `--base <branch>` | Compare against specific branch |

## How it decides

Diagrams are generated for:
- New features with multiple components
- API changes
- Database/schema changes
- Refactoring
- New modules

Diagrams are skipped for:
- Typo fixes
- Config changes
- Docs updates
- Test-only changes
- Dependency bumps

## Config

Optional. Create `~/.config/mr-diagram/config.yaml` or `.mr-diagram.yaml` in your project:

```yaml
ollama:
  model: codellama:13b  # or codellama:7b for faster

diagrams:
  max_diagrams: 3
  format: [png]

rules:
  skip_patterns:
    - "*.md"
    - "package-lock.json"
  always_diagram:
    - "src/api/**"
```

## Try it

```bash
# Create a test project
./scripts/create-test-repo.sh /tmp/test-project

# Run analysis
cd /tmp/test-project
mr-diagram-gen analyze --local

# View diagrams
mr-diagram-gen preview
```

## Supported

| Project | Detection |
|---------|-----------|
| React | `package.json` with react |
| Node.js | `package.json` |
| Go | `go.mod` |
| TypeScript | `tsconfig.json` |
| Other | Falls back to file analysis |

| Platform | Support |
|----------|---------|
| GitLab | Full (MR + image upload) |
| GitHub | Full (PR + native Mermaid) |

## License

MIT
