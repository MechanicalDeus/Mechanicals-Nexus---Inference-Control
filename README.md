# Nexus

![Nexus on GitHub — Inference Control](docs/assets/readme-banner.png)

> **Grep with structural understanding.**  
> **Stop reading code. Start querying structure.**

Nexus is an **inference layer** for Python code. It sits between **raw source** and **reasoning systems** (LLMs, humans, scripts): it turns a tree of `.py` files into a **map** of symbols, calls, reads/writes, mutation hints, and confidence — so you can **target** work instead of drowning in flat search hits.

**Core claim:** The **CPU scans the repo once** (AST + inference) and keeps a **map**. The **LLM does not open files** to “find” structure — it **asks Nexus** (again on the CPU) with a **query** and gets back a **bounded, topographic slice**: symbols, calls, writes, `NEXT_OPEN` regions — an **IR-shaped view** of the requested area, not a dump of every file body. To go deeper or follow a different thread, the model **changes the query**; Nexus already encoded **who calls whom** and **what might touch state**, so you are not manually **filtering dependencies** or **grep-hopping** the tree. **Retrieval is structural and local**, not “read everything in the editor.”

**Nexus does not reduce tokens mainly by compressing text. It reduces tokens by removing the need to ship whole-file context before you understand shape.**

---

## Problem

LLMs and developers burn context when the **model is forced to behave like a file browser**: open file, read wall of text, guess structure, repeat. The model **searches for content** by **absorbing text**, instead of **asking an index** for the **shape** of a region.

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

Instead of only raw matches, you get **structured reasoning paths** and **briefings** (`nexus -q`, `nexus-grep`). A model (or human) **queries the map on the CPU** and receives the **next relevant region** as structured output — **not** by opening each file in the IDE. Dependencies and call edges are **already resolved in the graph**; refining understanding means **a new query / slice**, not re-filtering the repo by hand.

**In one line:** *The LLM doesn’t open files to explore — it queries Nexus; the CPU returns a topographic structural slice of the area you asked for.*

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

The expensive part for LLM workflows is **not** the local AST pass — it is **repeated full-file context** in the prompt. Nexus **amortizes** on the **CPU**: one scan builds the graph; each **follow-up** is a **cheap structural query** (new `-q`, tighter caps) instead of pasting more files. The **model’s loop** becomes *ask Nexus → interpret slice → ask again*, not *open next file → read everything*.

**Amortization nuance:** Comparing only **total** tokens with vs without Nexus **does not show what those tokens paid for**. With Nexus, one thing is **structural** for the orientation phase: the model is **not** spending that context on **search-shaped** work (huge grep walls, exploratory full-file churn) — that part runs **locally**. Totals still include reasoning, edits, and targeted reads; see **[`docs/token-efficiency.md`](docs/token-efficiency.md)** §1.1.

**Reproducible numbers** (this repo + reference legacy scans), log-style before/after, and full **amortization** discussion: **[`docs/token-efficiency.md`](docs/token-efficiency.md)**.

## Mental model

| Without Nexus        | With Nexus              |
|---------------------|-------------------------|
| Model opens files → reads text → guesses structure | **CPU** scans once → **model queries map** → gets **structural slice** → opens source **only when needed** |
| Search → read → guess | **Query structure** → narrow region → read targeted code |

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

**Agent + Cursor (explanation anchor):** **[`docs/nexus-agent-cursor.md`](docs/nexus-agent-cursor.md)** — how the agent loop uses Nexus, what appears in the terminal, rules, and limits.

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

Nexus is **not** a linter, type checker, or profiler. It is a **static, heuristic inference layer** optimised for **context-efficient** navigation — a form of **semantic code indexing for LLM workflows** (and for humans who want the same map). The pitch is not “another AST tool”; it is **the LLM querying structure on your machine** instead of **opening files to discover** it — **meaning-shaped slices** before bulk text.

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
