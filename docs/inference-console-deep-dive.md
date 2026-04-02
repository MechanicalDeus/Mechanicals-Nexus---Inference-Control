# Nexus Inference Console — deep dive

This document complements the **[quick tutorial](inference-console-tutorial.md)** and the **[unified CLI + UI tutorial](tutorial-nexus-cli-and-ui.md)**. It explains *why* the console is shaped the way it is and how it stays aligned with the CLI and library.

---

## Role in the Nexus stack

Nexus builds an **inference map** (`InferenceGraph`): symbols, files, edges, mutation hints, confidence, layers. The **CLI** renders that map as text (`nexus`, `nexus-grep`, `nexus-policy`). The **Inference Console** renders the **same map** through a different **projection** (table, text, small graph).

**Invariant:** Nexus core semantics. **Variable:** how you look at it and what you copy into a prompt.

```text
Source → scan → InferenceGraph → projections → human or LLM
```

The console is **not** a second analyzer. It does not maintain its own graph semantics; it calls `attach()` / `generic_query_symbol_slice` / `to_llm_brief` / `trace_mutation` / `agent_qualified_names` like the tools you already use.

### Invariant: what you see vs what the LLM gets

| Layer | Role |
|-------|------|
| **InferenceGraph** | Single in-memory map after `attach` / scan — **the** semantic result. |
| **Projections** | Table, graph layout, brief string, JSON slice — **views** of that map. |
| **Clipboard / CLI stdout** | **Byte-identical** to the corresponding API for the same parameters. |

So “what we see” in the UI (e.g. the brief panel) and “what the LLM sees” after **Copy Brief** are not two pipelines. They are the **same** `to_llm_brief` output; the UI only **renders** it on screen *and* offers to copy it. Likewise **Copy Minimal** ↔ `agent_qualified_names`, **Copy JSON** ↔ bounded `build_json_slice` on the current slice.

**Caveat:** the LLM only gets what you paste. If you paste **Copy Brief**, it gets the brief; if you paste **Copy Minimal**, it gets only names. The *source* for each mode is still the same graph and the same Nexus functions — no hidden second inference pass in the console.

---

## `ConsoleSession` (orchestration)

`nexus.ui.session.ConsoleSession` holds:

- at most one **`InferenceGraph`** reference after **Scan / Refresh**  
- **`current_slice`**: last result of `generic_query_symbol_slice`  
- **`last_query`** plus the same **max_symbols / min_confidence** you used for the slice, so **Copy Brief** matches the table  

PyQt **signals** (`repoChanged`, `sliceUpdated`, `symbolSelected`, `statusMessage`) push results into widgets. **MainWindow** does not import `nexus.output.*` directly — only the session does.

---

## Projection modules (`nexus.ui.projections`)

Qt-free helpers keep logic testable:

| Module            | Purpose |
|-------------------|---------|
| `slice_table.py`  | Table rows from `list[SymbolRecord]` |
| `symbol_detail.py`| Plain-text trust panel from one symbol |
| `json_slice.py`   | **Bounded** JSON: slice symbols + edges whose **both** endpoints are in the slice ID set (not the full repo graph) |
| `focus_graph.py`  | One-hop neighbors: `called_by` + `calls` edges only |

---

## Tabs ↔ Nexus APIs

| Tab          | Backend |
|--------------|---------|
| **Slice**    | `generic_query_symbol_slice`, `to_llm_brief`, `agent_qualified_names` |
| **Mutation** | `InferenceGraph.trace_mutation` |
| **Focus Graph** | `calls` / `called_by` / `edges` — **no** custom traversal |

---

## Exports and token discipline

- **Copy Minimal** uses `agent_qualified_names`. For **special query modes** the API returns `None`; the UI tells you to use **Copy Brief** instead (same rule as the CLI).  
- **Copy Brief** is the full textual brief for the current query and caps.  
- **Copy JSON** is for tools/agents; treat it like any structured export (see **SECURITY.md** — do not commit raw full-graph dumps to public repos).

Default scan mode is **fresh** (no silent persistent cache). Cached modes in the library are opt-in and sensitive; the console does not hide a cache path from you.

---

## Code map

```text
src/nexus/ui/
  app.py              # entry: nexus-console
  session.py          # ConsoleSession
  main_window.py      # tabs, wiring
  projections/        # table, detail, json_slice, focus_graph
  widgets/focus_graph_view.py
```

Tests: `tests/test_ui_projections.py` (projections; PyQt optional for import smoke).

---

## Screenshots (same set as the tutorial)

| File | Idea |
|------|------|
| [1.png](../console%20tutorial/1.png) | Console ready, repo attached |
| [2.png](../console%20tutorial/2.png) | Query → slice + brief |
| [3.png](../console%20tutorial/3.png) | Trust / detail |
| [4.png](../console%20tutorial/4.png) | Mutation trace |
| [5b-focus-graph-clean.png](../console%20tutorial/5b-focus-graph-clean.png) | Focus graph (clean) |
| [5.png](../console%20tutorial/5.png) | Focus graph (busy) |
| [bottom textbox(brief).png](../console%20tutorial/bottom%20textbox%28brief%29.png) | Exports + brief context |
| [full text brief.png](../console%20tutorial/full%20text%20brief.png) | **Copy Brief** pasted in an editor — proof of LLM-facing text |

---

## Proof: clipboard = prompt context

The tutorial’s final screenshot shows the **full** **Copy Brief** payload in an external editor (~18k characters in the example). That string is **not** reinterpreted by the console: it is the same `format_graph_for_llm` / `to_llm_brief` pipeline as the CLI. Use it to document *exactly* what you ship to a chat model or to a file-based prompt workflow.

**Alt-style caption:** *Balanced brief for query `runtime resolver` pasted from Nexus Inference Console — repo stats, NEXT_OPEN, entry points, mutation/state symbols (example: TTRPG Studio).*
