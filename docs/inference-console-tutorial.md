# Nexus Inference Console — quick tutorial

**Screenshots** below use **`docs/ui-screenshots/`** (current UI, incl. **Darstellung** dark/light). For CLI-terminal and Cursor/metrics images still under **`console tutorial/`**, see **[extended tutorial §0](tutorial-nexus-cli-extended.md#0-other-assets-in-console-tutorial)**.

**Also read:** the repo’s **[full CLI + UI tutorial](tutorial-nexus-cli-and-ui.md)** (same story as here) and the **[extended CLI tutorial](tutorial-nexus-cli-extended.md)** (deeper command reference + all new shots).

The **Nexus Inference Console** is a small PyQt UI on top of the same engine as `nexus` / `nexus-grep`: one **inference map** per scan, then **projections** (table, brief, mutation trace, focus graph) and **clipboard exports** for LLM workflows.

## Same facts for humans and for the LLM

Nexus builds a single **`InferenceGraph`** per scan. Everything you see in the console — table, detail pane, brief text — and everything you **copy** (**Copy Brief**, **Copy Minimal**, **Copy JSON**) comes from **that same graph** through the **same functions** the CLI uses (`generic_query_symbol_slice`, `to_llm_brief`, `agent_qualified_names`, `trace_mutation`, …).

So:

- **Invariant:** the underlying inference (symbols, edges, mutation hints, confidence) is **one** truth.  
- **Variable:** *how* it is shown (pixels vs terminal vs clipboard) — not *a different* analysis.

If you run the **same** repo, **same** query, and **same** `max_symbols` / `min confidence` in the CLI and click **Copy Brief** in the console, the **brief text matches** what `nexus -q …` would print. The UI does not “reinterpret” the map for the model.

## Install and run

```bash
python -m pip install "nexus-inference[ui] @ git+https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control.git"
nexus-console
# or: python -m nexus.ui
```

From a clone: `pip install -e ".[ui]"`. Without `[ui]`, PyQt6 is missing and the entry point prints an install hint. See **[README → Installation](../README.md#installation)**.

---

## 1. Attach a repository

Pick your Python project root (where your package and `.py` files live), then **Scan / Refresh**.

![Empty console after choosing a repo](ui-screenshots/Shot%201.png)

*UI labels are in German: **Ordner…** = browse folder, **Scan / Refresh** = rebuild the map, **Darstellung** = theme.*

---

## 2. Run a query (slice + balanced brief)

Enter a heuristic query (same idea as `nexus-grep` / `nexus -q`), set **max sym** (e.g. 12), optionally **min confidence**, then **Query**.

Example query: `runtime resolver` on a large app gives a **prioritized slice** and a **balanced brief** (`to_llm_brief`) — stats, symbol cards, `NEXT_OPEN` hints.

![Slice table and brief after querying](ui-screenshots/Shot%202.png)

---

## 3. Trust panel — why this symbol is in the slice

Select a row. The right-hand pane shows **raw Nexus fields** for that symbol: confidence, layer, reads/writes/calls, tags, mutation paths, etc. No extra semantics are invented here.

![Selected symbol — inspector / trust (1)](ui-screenshots/Shot%203-1.png)

![Selected symbol — inspector (2)](ui-screenshots/Shot%203-2.png)

---

## 4. Mutation tab — `trace_mutation`

Switch to **Mutation**, enter a **state key substring** (matched against write-hint strings), then run **trace_mutation**. You get three buckets: **direct**, **indirect**, and **transitive** writers.

![Mutation trace (example)](ui-screenshots/Shot%204-1.png)

---

## 5. Focus graph — one hop only

Open **Focus Graph**, then select a symbol again on the **Slice** tab. You see **callers** (green), the **selected symbol** (blue), and **callees** (brown) — fixed layout, no free graph explorer.

The “clean” four-node example is ideal for screenshots:

![Focus graph — compact 1-hop view](ui-screenshots/Shot%205-1.png)

A busier view (many callees) is still valid but harder to read at a glance:

![Focus graph — many direct callees](ui-screenshots/Shot%205-2.png)

---

## 6. What actually goes to the LLM

The three buttons under the slice copy **different projections** of the **same** underlying graph (bounded slice, not the whole repo):

| Button        | Typical use                         |
|---------------|-------------------------------------|
| **Copy Minimal** | Qualified names only — smallest paste |
| **Copy Brief**   | Full `to_llm_brief` text for the current query/settings |
| **Copy JSON**    | Slice symbols + edges **only inside** the slice ID set |

![Detail + export buttons (brief area visible)](ui-screenshots/Shot%206.png)

---

## 7. Paste “Copy Brief” — this is what the LLM sees

Click **Copy Brief**, then paste into any editor or chat. The text is the same **`to_llm_brief`** output as from the CLI for that repo, query, and `max_symbols` / `min confidence` settings: repo line, stats, `NEXT_OPEN`, symbol sections (reads/writes/calls, tags, mutation hints), etc.

![Full balanced brief pasted into an editor (TTRPG Studio example)](ui-screenshots/Shot%207.png)

This closes the loop: **inference map → bounded projection → exact context string** you can drop into a model.

---

## Checklist

1. Attach repo → Scan / Refresh  
2. Query → inspect table + brief  
3. Select row → trust panel  
4. Mutation substring → three lists  
5. Focus graph → 1-hop picture  
6. Copy Minimal / Brief / JSON  
7. Paste **Copy Brief** where your LLM lives — same bytes as the console brief  

For architecture, session layer, and safety notes, see **[Inference Console deep dive](inference-console-deep-dive.md)**.
