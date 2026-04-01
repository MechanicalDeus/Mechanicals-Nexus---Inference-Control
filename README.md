# Nexus

![Nexus on GitHub — Inference Control](docs/assets/readme-banner.png)

> **Grep with structural understanding.**

Nexus is an **inference layer** for Python code. It sits between **raw source** and **reasoning systems** (LLMs, humans, scripts): it turns a tree of `.py` files into a **map** of symbols, calls, reads/writes, mutation hints, and confidence — so you can **target** work instead of drowning in flat search hits.

**Nexus does not reduce tokens by compressing text. It reduces tokens by removing the need to read irrelevant code at all.**

---

## Problem

LLMs and developers burn context on **irrelevant files**.

Classic tools (`grep`, `rg`):

- return **lines of text**, not **meaning**  
- scale poorly to “where does this behaviour live?” questions  

→ High cost, low precision.

## Solution

Nexus builds an **inference map** of your project:

- Symbols (functions, classes, methods)  
- Call relationships  
- Mutation / state-touching hints and chains  
- Layering and confidence  

Instead of only raw matches, you get **structured reasoning paths** and **briefings** (`nexus -q`, `nexus-grep`).

## Quick example (PoC)

```bash
nexus-grep . -q "mutation" --max-symbols 10
```

Deeper, still bounded:

```bash
nexus . -q "mutation" --max-symbols 5
```

Example mutation-chain fragment when analysing this repo (your project will differ):

`src.nexus.cli.main → src.nexus.scanner.attach → src.nexus.scanner.scan → src.nexus.scanner._scan_impl → src.nexus.scanner._tag_symbol`

More narrative walkthrough: [`docs/proof-of-concept.md`](docs/proof-of-concept.md).

## Efficiency: one scan, bounded prompts

The expensive part for LLM workflows is **not** the local AST pass — it is **repeated context** you send on every turn. Nexus amortises work: you pay **CPU once** per run to build the graph; then **`--names-only`**, **`nexus-grep`**, and small **`--max-symbols`** keep **prompt size** under a cap instead of shipping huge grep walls.

**Reproducible numbers** (this repo + reference legacy scans) and log-style before/after: **[`docs/token-efficiency.md`](docs/token-efficiency.md)** (German, with English summary).

## Mental model

| Without Nexus        | With Nexus              |
|---------------------|-------------------------|
| Search → read → guess | Understand → target → read |

## Installation

From PyPI (when published):

```bash
pip install nexus-inference
```

From a clone (recommended until release is on your index):

```bash
pip install -e .
# or: pipx install -e .
```

Python **3.10+**. Entry points: `nexus`, `nexus-grep`, `nexus-cursor-rules`.

### Cursor rules (bundled in the package)

The `.mdc` rule ships inside **`nexus-inference`** (`nexus.cursor_rules`). Cursor loads project rules from **`.cursor/rules/`**.

```bash
cd /path/to/your/python/project
nexus-cursor-rules install
# same: python -m nexus.cursor_rules install
# overwrite: nexus-cursor-rules install --force
# show bundled path: nexus-cursor-rules --path
```

Bundled source in this repo: [`src/nexus/cursor_rules/nexus-over-grep.mdc`](src/nexus/cursor_rules/nexus-over-grep.mdc). Extra notes: [`extras/cursor-rules/README.txt`](extras/cursor-rules/README.txt).

## Library

```python
from nexus import attach

g = attach("./your_repo")
print(g.to_json())
```

Use **`--json` / saved exports only when necessary** — they can be **security-sensitive** (see below).

## Usage flow (agents & humans)

1. **`nexus-grep`** — find a small, relevant symbol/file slice.  
2. **Open only those files** in the editor or prompt.  
3. **`nexus -q`** — impact, mutation chains, etc., with a tight `--max-symbols`.  
4. **`nexus . --json`** — full graph export **only** if you need it and can keep it **private**.

Agent-oriented checklist (German): [`AGENTS.md`](AGENTS.md).

## Security: inference maps

Generated maps (JSON graphs, large briefings) can expose **architecture, paths, and sensitive flows**. **Do not commit them.** Read [`SECURITY.md`](SECURITY.md) and use the `.gitignore` patterns in this repo as a template for your projects.

## Positioning

Nexus is **not** a linter, type checker, or profiler. It is a **static, heuristic inference layer** optimised for **context-efficient** navigation — a form of **semantic code indexing for LLM workflows** (and for humans who want the same map).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
