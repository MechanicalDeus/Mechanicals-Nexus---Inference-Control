# Nexus — summary and concept pitch

This document summarizes **purpose, value, and positioning** of Nexus — as an **overview** for decisions and as a **pitch** for teams using LLM agents or structured code analysis.

---

## Pitch (~60 seconds)

**Problem:** Feeding large Python codebases into an LLM with **broad grep or `rg`** yields many lines, little structure, and burns **tokens** — without guaranteeing the right files.

**Solution:** **Nexus** builds an **inference map** from source: symbols (functions, classes, methods), **call edges**, heuristic **read/write traces** and **mutation paths**, plus **confidence** and **layers** (e.g. core vs. support). Instead of raw hit lists, agents and humans get **compact, sorted briefs** or **targeted name lists**.

**Tiering:** Start with **`nexus-grep`** or **`nexus --names-only`** (thin output), then **read specific files**, **`nexus -q`** with small `--max-symbols` for chains/impact, **`--json`** only when the full graph is needed.

**One line:** Nexus is **grep with structural priors** — built to keep **LLM context lean and relevant**.

---

## What Nexus does

### Target picture

Nexus fills a gap in agent workflows: **orientation and impact analysis** in Python repos without blindly searching half the tree. Output is tuned for **machine readability and token budget** (`AGENTS.md`, bundled Cursor rule via `nexus.cursor_rules` / `nexus-cursor-rules install`).

### Core idea

1. **Static analysis:** AST-based ingest of `.py` files under a root path.
2. **In-memory graph:** `InferenceGraph` with `SymbolRecord` nodes and `Edge` edges (mainly `calls`).
3. **Heuristics:** Direct/indirect/**transitive** write traces along call chains (fixpoint), **semantic tags** (e.g. `mutator`, `delegate`, `ambiguous-call`), **confidence** in [0, 1], **layer** from path/name.
4. **Query layer:** Free-text `-q` with keyword filters for mutation vs. flow; **special modes** (impact, mutation chain, why, …) for deeper but still formatted answers.
5. **Second tool `nexus-grep`:** Nexus slice (relevant symbols/files) first, then **grep only inside that slice** — not the whole repo.

### Pipeline (short)

- **Entry:** `attach(path)` / `scan(path)` → full graph for chosen options (`include_tests`, `transitive_depth`, …).
- **CLI `nexus`:** JSON export or **LLM brief** (`to_llm_brief`), optional **`--names-only`** for minimal tokens and **`--annotate`** for one-line names with **confidence / tags / layer / file:line**; query briefs add **`NEXT_OPEN`** and **same-name folding** to cut repetition.
- **CLI `nexus-grep`:** No special queries; **small symbol set → search in few files**.

### Measurable efficiency

Explained with numbers (reproducible in the Nexus repo, plus reference snapshots from larger projects): **`docs/token-efficiency.md`** — focus: **one local scan** vs. **bounded prompt size** per agent turn.

### Who is it for?

- **LLM-assisted development** (Cursor, Codex, custom pipelines) that cares about **context budget**.
- **Reviews and refactors** where **“who calls whom”** and **“where is state touched”** should surface quickly.
- **Onboarding** into unfamiliar Python projects without an immediate full-graph export.

### What Nexus is not

- Not a **linter**, **type checker**, or **profiler**.
- No **runtime guarantees** — inference and heuristics can be **wrong or incomplete**; **confidence** and tags surface uncertainty.
- **`follow_imports`** exists in the model; the main story stays **intra-repo** and **static**.

---

## Value (for decision-makers)

| Aspect | Benefit |
|--------|---------|
| **Cost** | Fewer irrelevant tokens → lower model cost and faster answers. |
| **Quality** | Structured maps reduce hallucinations about “somewhere in the repo”. |
| **Workflow** | Clear tiering: thin → read → deeper when needed — fits human and agent work. |
| **Integration** | Library (`attach`) + CLI + installable Cursor rule; no mandatory cloud service. |

---

## Next steps

1. **Install:** `pipx install -e <nexus-checkout>` or `PYTHONPATH=<checkout>/src` and `python -m nexus …` (details: `README.md`, `AGENTS.md`).
2. **Rule in target repo:** `nexus-cursor-rules install` at project root (package rule → `.cursor/rules/`).
3. **First use:** `nexus-grep . -q "<concrete code terms>" --max-symbols 20` in the target project, then open files selectively.

---

## Closing

Nexus is a **focused tool** for **structured Python maps** and **token-aware** agent workflows. The pitch: **less noise, more edge** — map first, text second, not the other way around.

*Document version: summary / pitch in the Nexus repository.*
