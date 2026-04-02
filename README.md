# Nexus

![Nexus on GitHub — Inference Control](docs/assets/readme-banner.png)

> **Grep with structural understanding.**  
> **Stop reading code. Start querying structure.**

Nexus is an **inference layer** for Python code. It sits between **raw source** and **reasoning systems** (LLMs, humans, scripts): it turns a tree of `.py` files into a **map** of symbols, calls, reads/writes, mutation hints, and confidence — so you can **target** work instead of drowning in flat search hits.

**Core claim:** You can **understand how code fits together** — what exists, who calls whom, what might touch state, where to open next — from a **bounded structural brief**, often **before opening the file**. The expensive part of many workflows is not compression; it is **reading** whole files to build a mental model. Nexus **removes the need to read code first**; it gives you **meaning-shaped structure**, not a wall of text.

**Nexus does not reduce tokens mainly by compressing text. It reduces tokens by removing the need to read irrelevant code at all.**

---

## Problem

LLMs and developers burn context on **irrelevant files** — and on **opening files at all** just to learn what a symbol does, who calls it, or what it mutates.

Classic tools (`grep`, `rg`):

- return **lines of text**, not **meaning**  
- scale poorly to “where does this behavior live?” questions  
- still push you toward **read the file → infer structure** yourself  

→ High cost, low precision. **Understanding** becomes **reading**.

## Solution

Nexus builds an **inference map** of your project — **structure as the primary artifact**, not raw text:

- Symbols (functions, classes, methods)  
- Call relationships  
- Mutation / state-touching hints and chains  
- Layering and confidence  

Instead of only raw matches, you get **structured reasoning paths** and **briefings** (`nexus -q`, `nexus-grep`). A model (or human) can **query that map** and get **`NEXT_OPEN` hints** and symbol cards — **without** having loaded every body.

**In one line:** *Nexus lets models understand code **without reading the whole file first** — by answering in structure, not by dumping source.*

## Quick example (PoC)

```bash
nexus-grep . -q "mutation" --max-symbols 10
```

Safe-by-default wrapper (scope gating + staged caps):

```bash
nexus-policy . -q "state"
```

Deeper, still bounded:

```bash
nexus . -q "mutation" --max-symbols 5
```

**Defaults (query mode, `-q`):** If you omit `--max-symbols`, Nexus caps the heuristic slice at **12** symbols. The brief then adds **`NEXT_OPEN`** (up to three suggested `file:line` slices) and collapses **same simple name** duplicates into one primary block plus a compact **`SAME_NAME`** summary / `same_name_also` line — fewer tokens, less repetition.

**Minimal tokens, still interpretable:**

```bash
nexus . -q "mutation" --names-only --max-symbols 10
```

**Names + confidence/tags/layer/path in one line per symbol** (slightly larger than plain names-only, fewer follow-up questions):

```bash
nexus . -q "mutation" --names-only --annotate --max-symbols 10
```

Example mutation-chain fragment when analysing this repo (your project will differ):

`src.nexus.cli.main → src.nexus.scanner.attach → src.nexus.scanner.scan → src.nexus.scanner._scan_impl → src.nexus.scanner._tag_symbol`

**Tutorial hub:** **[`TUTORIAL.md`](TUTORIAL.md)** (links to the full guide, screenshots, and related docs).

More narrative walkthrough: [`docs/proof-of-concept.md`](docs/proof-of-concept.md).

## Efficiency: one scan, bounded prompts

The expensive part for LLM workflows is **not** the local AST pass — it is **repeated context** you send on every turn. Nexus **amortizes** work: you pay **CPU once** per run to build the graph; then **`--names-only`**, **`nexus-grep`**, and small **`--max-symbols`** keep **prompt size** under a cap instead of shipping huge grep walls.

**Reproducible numbers** (this repo + reference legacy scans), log-style before/after, and an **amortization** section: **[`docs/token-efficiency.md`](docs/token-efficiency.md)**.

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

Python **3.10+**. Entry points: `nexus`, `nexus-grep`, `nexus-policy`, `nexus-cursor-rules`, `nexus-console`.

### Nexus Inference Console (optional GUI)

Same inference engine as the CLI: attach a repo, run a query, inspect a **bounded slice**, **trust metadata**, **mutation trace**, and a **one-hop focus graph**; copy **minimal names**, **balanced brief**, or **slice JSON** for LLMs. The console does **not** run a second analyzer — **Copy Brief** is the same `to_llm_brief` text you would get from `nexus -q` with the same query and caps ([tutorial](docs/inference-console-tutorial.md#same-facts-for-humans-and-for-the-llm)).

```bash
pip install -e ".[ui]"
nexus-console
```

- **[`TUTORIAL.md`](TUTORIAL.md)** (start here) → **[full walkthrough](docs/tutorial-nexus-cli-and-ui.md)**  
- **[Console quick steps](docs/inference-console-tutorial.md)** · **[Deep dive](docs/inference-console-deep-dive.md)**

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

Agent-oriented checklist: [`AGENTS.md`](AGENTS.md). Executive summary: [`NEXUS-REPORT.md`](NEXUS-REPORT.md).

## Safety features (what keeps output bounded)

Nexus is designed to be **token-efficient**, but also to reduce “oops” moments in agent workflows:

- **Bounded slices**: query mode defaults to a small heuristic cap (12 symbols if `--max-symbols` is omitted).
- **Names-only modes**: `--names-only` (and `--annotate`) produce one line per symbol instead of verbose briefs.
- **Same-name folding**: duplicates are collapsed into a primary block plus a compact `SAME_NAME` summary.
- **Safe wrapper (`nexus-policy`)**: applies **scope gating** + **risk-based caps** + **staged retrieval** and enforces a hard output bound (chars + lines). Stage 3 is **explicit only** (never automatic).
- **Control headers**: optional bounded `[NEXUS_CONFIG]` header (`--control-header` / `NEXUS_CONTROL_HEADER=1`) on stderr for observability without dumping map content.
- **Governance files**: `.nexusdeny` / `.nexusignore` / `.nexus-skip` prevent sensitive subtrees from being discovered or inferred (details in `SECURITY.md`).

## Security: inference maps

Generated maps (JSON graphs, large briefings) can expose **architecture, paths, and sensitive flows**. **Do not commit them.** Read [`SECURITY.md`](SECURITY.md) (including **`.nexusdeny` / `.nexusignore`**) and use the `.gitignore` patterns in this repo as a template for your projects.

**Take:** better targeting for LLMs also raises the stakes for *what* gets opened — see the short **“Take: agents and governance (small oops)”** section in [`SECURITY.md`](SECURITY.md#take-agents-and-governance-small-oops) and the screenshot there.

## Positioning

Nexus is **not** a linter, type checker, or profiler. It is a **static, heuristic inference layer** optimised for **context-efficient** navigation — a form of **semantic code indexing for LLM workflows** (and for humans who want the same map). The pitch is not “another AST tool”; it is **understanding before reading** — **meaning over text** for the first hop.

## Tutorial

Guided walkthrough: **CLI** (including in your IDE terminal), optional **Inference Console**, screenshots, and why **CLI / GUI / pasted brief** share the **same** inference map.

| | |
|--|--|
| **Entry point** | **[`TUTORIAL.md`](TUTORIAL.md)** |
| **Full guide** | **[`docs/tutorial-nexus-cli-and-ui.md`](docs/tutorial-nexus-cli-and-ui.md)** |
| **CLI in the IDE** (local, bounded output) | [Section in full guide](docs/tutorial-nexus-cli-and-ui.md#cli-in-the-ide-local-fast-bounded-output) |
| **Console** quick steps | [`docs/inference-console-tutorial.md`](docs/inference-console-tutorial.md) |
| **Architecture** (session, exports) | [`docs/inference-console-deep-dive.md`](docs/inference-console-deep-dive.md) |
| **Screenshot assets** | [`console tutorial/`](console tutorial/) |

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
