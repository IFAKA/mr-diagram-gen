# mr-diagram-gen

Auto-generate architecture diagrams for your merge requests / pull requests.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/IFAKA/mr-diagram-gen/main/setup.sh | bash
```

Or manually:
```bash
pip install git+https://github.com/IFAKA/mr-diagram-gen.git
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/IFAKA/mr-diagram-gen/main/uninstall.sh | bash
```

Or manually:
```bash
pip uninstall mr-diagram-gen && rm -rf ~/.config/mr-diagram
```

Zero traces.

---

## Use It

```bash
cd your-project
mr-diagram-gen analyze --local
```

That's it. Opens your diagrams when done.

---

## Integrate Into Your Workflow

### Option 1: Run manually when you want diagrams
```bash
# Before creating MR/PR, generate diagrams
mr-diagram-gen analyze --local
# Then drag images into your MR/PR description
```

### Option 2: Git hook (auto-run before push)
```bash
mr-diagram-gen install-hook
# Now it runs automatically every time you push
```

### Option 3: Auto-create MR/PR with diagrams
```bash
# Set token once
export GITLAB_TOKEN=xxx  # or GITHUB_TOKEN

# Push and create MR/PR in one command
mr-diagram-gen push
```

### Option 4: CI/CD
```yaml
# .gitlab-ci.yml
diagram:
  script:
    - pip install git+https://github.com/IFAKA/mr-diagram-gen.git
    - mr-diagram-gen analyze --local --mock-llm
  artifacts:
    paths:
      - .mr-diagrams-preview/
```

---

## Commands

| Command | What it does |
|---------|--------------|
| `analyze --local` | Generate diagrams, save locally |
| `analyze --local --mock-llm` | Same but skip Ollama |
| `push` | Generate + create MR/PR |
| `preview` | Open generated diagrams |
| `status` | Check setup |
| `install-hook` | Add git pre-push hook |

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) with `codellama:7b` (the setup script handles this)
- Node.js for PNG rendering (optional, falls back to Mermaid code)

## How it works

1. Detects project type (React, Node, Go, TypeScript, etc)
2. Analyzes git diff vs main branch
3. Asks LLM: "do these changes need diagrams?"
4. If yes, generates Mermaid diagrams
5. Compiles to PNG images

Skips diagrams for: typo fixes, config changes, docs, tests, dependency bumps.

## Config (optional)

```bash
mr-diagram-gen init  # creates ~/.config/mr-diagram/config.yaml
```

```yaml
ollama:
  model: codellama:7b  # or codellama:13b for better quality

rules:
  always_diagram:
    - "src/api/**"  # always generate for API changes
```

## License

MIT
