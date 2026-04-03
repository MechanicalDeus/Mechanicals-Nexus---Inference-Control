# Nexus CLI — extended tutorial (current Inference Console)

**Prerequisite:** Read the shorter story in **[tutorial-nexus-cli-and-ui.md](tutorial-nexus-cli-and-ui.md)** (*one map, two surfaces*). This page goes deeper on **CLI commands, perspectives, and PowerShell quoting**, using **up-to-date screenshots** from the Inference Console in **[`ui-screenshots/`](ui-screenshots/)** (April 2026 UI, including the **Darstellung** dark/light selector).

**Core invariant:** One scan builds one **`InferenceGraph`**. Everything visible in the console and everything copied via **Copy …** uses the **same** projection paths as `nexus` / `nexus-opc` (underlying `nexus` argv) / `nexus-grep` / `--perspective`.

---

## 0. Other assets in console tutorial

**Inference Console UI documentation** uses only **`docs/ui-screenshots/`** (current chrome, incl. **Darstellung**). The folder **`console tutorial/`** keeps **non-Qt** extras:

| Files in `console tutorial/` | Role |
|------------------------------|------|
| **`cli-ide-proof.png`** | **CLI in IDE terminal** — illustrates bounded `nexus -q` stdout (same pipeline as the console brief). |
| **`Token cost analysis.png`**, **`Token cost analysis2.png`**, **`cursor-usage-estimation-example.png`**, **`retrieved data.png`**, **`worker using nexus.png`**, … | **Cursor / usage metrics** — see [cursor-metrics-nexus.md](cursor-metrics-nexus.md). |

---

## 1. Install and run

```bash
pip install -e .   # from clone; PyPI path — see README → Installation
pip install -e ".[ui]"   # console only (PyQt6)
nexus-console
# or: python -m nexus.ui
```

**Commands:** `nexus-opc`, `nexus`, `nexus-grep`, `nexus-policy`, `nexus-cursor-rules`, `nexus-console`. PyPI distribution name: **`nexus-inference`** (not a shell command).

---

## 2. Attach repo (scan) — same step as before any CLI output

**CLI:** Each invocation scans before the first byte on stdout.  
**UI:** Set repository root, **Scan / Refresh**. Optionally set **Darstellung** (dark/light).

![Repo path, Scan / Refresh, and theme selector](ui-screenshots/Shot%201.png)

**CLI equivalent:** `nexus . -q "…"` builds the graph in-process first — same role as **Scan / Refresh** for a long-lived session.

---

## 3. Query, slice table, and balanced brief

**CLI:** `generic_query_symbol_slice` + `to_llm_brief` / `format_graph_for_llm` → one text stream.  
**UI:** **Query**, **max sym**, optional **min confidence**, then **Query**. The **table** is the slice order; the **lower pane** is the same brief as `nexus -q …` with identical parameters.

![Slice table and brief after running a query](ui-screenshots/Shot%202.png)

**PowerShell (quote arguments safely):**

```powershell
Set-Location F:\Nexus
$env:PYTHONPATH = "F:\Nexus\src"
python -m nexus . "-q" "mutation flow" "--max-symbols" "12"
python -m nexus src/nexus "-q" "resolver" "--max-symbols" "10" "--names-only"
```

---

## 4. Select a symbol — inspector / trust / perspectives

Select a row: the right-hand **Perspektive** combo (Trust, Focus JSON, Brief, names, compact) maps to the same **`PerspectiveKind`** paths as `nexus --perspective …` — not a second analyzer.

![Inspector with perspectives — view 1](ui-screenshots/Shot%203-1.png)

![Inspector — complementary view](ui-screenshots/Shot%203-2.png)

**CLI parallels:**

```powershell
python -m nexus . "--perspective" "trust_detail" "--center-kind" "symbol_qualified_name" "--center-ref" "pkg.mod.function"
python -m nexus . "--perspective" "llm_brief" "-q" "impact SomeClass" "--max-symbols" "15"
```

---

## 5. Mutation — `trace_mutation` in three buckets

**Mutation** tab: state-key substring, **trace_mutation**. **direct / indirect / transitive** match the graph API.

![Mutation — overview / direct](ui-screenshots/Shot%204-1.png)

![Mutation — additional tab / context](ui-screenshots/Shot%204-2.png)

![Mutation — indirect](ui-screenshots/Shot%204-3.png)

![Mutation — transitive](ui-screenshots/Shot%204-4.png)

**CLI / perspective:**

```powershell
python -m nexus . "--perspective" "mutation_trace" "--mutation-key" "your_state_key_substring"
```

---

## 6. Focus graph — one hop over edges

Only direct **callers** / **callees** of the selection; fixed layout, no second graph engine.

![Focus graph — clean 1-hop view](ui-screenshots/Shot%205-1.png)

![Focus graph — busier / more edges](ui-screenshots/Shot%205-2.png)

![Focus graph — variant](ui-screenshots/Shot%205-3.png)

**CLI:**

```powershell
python -m nexus . "--perspective" "focus_graph" "--center-kind" "symbol_qualified_name" "--center-ref" "pkg.mod.symbol"
```

---

## 7. Exports — minimal, brief, JSON

The buttons under the slice copy **bounded** projections of the same graph (not full-repo `--json`).

![Export row and brief context](ui-screenshots/Shot%206.png)

![Brief / context area — variant](ui-screenshots/Shot%206-2.png)

![Export / editor context — variant](ui-screenshots/Shot%206-3.png)

| Button | Typical CLI counterpart |
|--------|-------------------------|
| **Copy Minimal** | `--names-only` (qualified names) |
| **Copy Brief** | `nexus -q …` stdout / `llm_brief` |
| **Copy JSON** | bounded slice JSON projection (not full graph) |

---

## 8. What the LLM sees — brief in an external editor

**Copy Brief** → paste: same bytes as `nexus -q …` for the same repo, query, and caps.

![Full balanced brief pasted in an editor (example)](ui-screenshots/Shot%207.png)

---

## 9. CLI cheat sheet (extended)

| Goal | Example |
|------|---------|
| Compact agent slice | `nexus . --agent-mode -q "mutation"` |
| Names only | `nexus . -q "…" --names-only --max-symbols 20` |
| Names + meta | `nexus . -q "…" --names-only --annotate --max-symbols 20` |
| Heuristic slice (explicit) | `nexus . --perspective heuristic_slice -q "flow" --max-symbols 12` |
| Brief incl. special modes | `nexus . --perspective llm_brief -q "impact Class" --max-symbols 15` |
| Slice as JSON | `nexus . --perspective query_slice_json -q "mutation" --max-symbols 20` |
| Policy / safe defaults | `nexus-policy . -q "state"` |
| Thin search | `nexus-grep . -q "…" --max-symbols 25` |
| Metrics line | `NEXUS_METRICS_JSON=1` or `--metrics-json` |

**Rules:** Do not combine `--perspective` with `--json`, `--names-only`, `--query-slice-json`, `--trace-mutation`, `--focus-graph` — see **[cli-perspective.md](cli-perspective.md)**.

**Full graph (rare, sensitive):** `nexus . --json` — read **[SECURITY.md](../SECURITY.md)**.

---

## 10. Library (optional)

```python
from nexus import attach

g = attach("./your_repo")
# g.to_llm_brief(query="mutation", max_symbols=12)
# g.trace_mutation("substring")
```

---

## Further reading

| Doc | Content |
|-----|---------|
| [tutorial-nexus-cli-and-ui.md](tutorial-nexus-cli-and-ui.md) | Story: CLI + UI (updated screenshots) |
| [inference-console-tutorial.md](inference-console-tutorial.md) | Short console checklist |
| [inference-console-deep-dive.md](inference-console-deep-dive.md) | Session, projections, security |
| [cli-perspective.md](cli-perspective.md) | Perspective matrix |
| [tutorial-nexus-opc-isa.md](tutorial-nexus-opc-isa.md) | `nexus-opc` opcode ISA for agents |
| [nexus-agent-cursor.md](nexus-agent-cursor.md) | Agent loop in Cursor |

---

## Checklist (CLI-focused)

1. Run `nexus -q` / `--perspective` with a small `--max-symbols`.  
2. Run the same query in the console — compare table + brief to the terminal.  
3. Mirror **Trust** and **Focus** with `--perspective trust_detail` / `focus_graph`.  
4. Compare the **Mutation** tab to `mutation_trace`.  
5. Compare **Copy Brief** to `nexus -q` stdout (same inputs).  
6. On PowerShell, always pass `-q` and long flags as **separate** quoted arguments.

**Structural inference** — terminal, console, or clipboard, **one** pipeline.
