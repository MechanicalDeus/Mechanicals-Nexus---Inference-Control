# Token efficiency and measurement — why cost amortizes

A **local** full-repo scan builds a graph in memory **once per process**. After that, each agent turn can rely on **bounded** Nexus output (`--names-only`, `nexus-grep`, small `--max-symbols`) instead of pasting huge grep dumps or whole files into the model. Below: **reproducible numbers** from this repository plus **reference scans** from larger legacy codebases.

**Why slice at all?** The **full** inference map (especially a **`--json` export**) for a real codebase is often **orders of magnitude larger** than the Nexus package on disk — and **vastly** larger than what belongs in **one** model context. Symbols × edges × paths add up fast. **Query mode**, **`--max-symbols`**, **same-name folding**, and **`--names-only`** exist so you ship **a card hand**, not the **whole deck**.

---

## 1. Core economics

| Phase | Where cost shows up | Nexus behavior |
|--------|---------------------|----------------|
| **Index / scan** | CPU time on your machine, **no** LLM tokens | `attach()` / `nexus` / `nexus-grep` read the tree **once** (per run) and keep the graph in memory. |
| **Each agent turn** | **Context = tokens** (everything that goes into the prompt) | You cap volume with **`--max-symbols`**, **`--names-only`**, and **`nexus-grep`** (slice → then **read_file** only where it matters). |

**One-line takeaway:** Ingesting a large repo happens **locally and once per run**; the **expensive** part is **repeated** model context — and that is where Nexus keeps output **bounded** instead of shipping half the tree as text every step.

### 1.1 Amortization: totals alone miss the point

Teams often diff **only** “tokens out **with** Nexus” vs “tokens out **without** Nexus.” That **aggregates** spend but **does not say what the tokens bought**.

| What you are comparing | What it hides |
|------------------------|----------------|
| **Total prompt tokens per task** | Same total can mean very different **mixes**: e.g. mostly **search/navigation** vs mostly **reasoning + targeted reads**. |

**What Nexus guarantees (for orientation / retrieval):**  
For the **discovery** step, the model is **not** using context to **search** in the sense of **absorbing huge unstructured grep walls** or **file-after-file exploration** just to learn **where** things live and **how** they connect. That work is done by **Nexus on the CPU**; the model receives a **bounded structural slice** (brief, names, `NEXT_OPEN`, …).

The model **still** spends tokens on **other** things: chain-of-thought, final answers, **read_file** on paths you chose, patches, tool chatter, system prompts. **Nexus does not zero those out** — it **removes search-shaped spend** from the prompt for that phase.

So **amortization** here is not only “fewer tokens” — it is **reallocation**:

- **Without Nexus (naive agent):** a large share of context often goes to **finding** structure (raw hits, long file dumps).
- **With Nexus:** that share moves to **local scan + small structured output**; tokens shift toward **using** the map (reasoning, edits, narrow reads).

When you measure, add a **purpose tag** if you can (even rough): *orientation / search*, *reasoning*, *source read*, *output* — so “before/after” reflects **what** changed, not only the scalar total.

**Cursor dashboard snapshots:** real agent sessions are summarized in **[`usage-metrics.md`](usage-metrics.md)** — including a **measurement map** and an explicit **fair vs unfair** table. The **~7×–15×** style gaps in the gallery **confound** **build-without-Nexus** sessions with **analysis-with-Nexus** sessions; the **TTRPG Studio** pair is the **controlled analysis** benchmark (**N=1**).

---

## 2. Reproducible measurement: **Nexus** (this repository)

Environment: PowerShell, repo checkout root, `PYTHONPATH` pointing at `…/src` or an installed `nexus`.

### 2.1 Graph size (one scan, typical header)

```bash
python -m nexus . -q "mutation" --max-symbols 10
```

Excerpt from the output (metadata only):

```text
REPO: F:\Nexus
QUERY (filtered): mutation
Files: 34  Symbols: 162  Edges: 191
Showing 10 symbol(s).
```

These are the **dimensions of the index built once** (on the order of tens of files, ~hundreds of symbols and edges) — **not** the size of the LLM prompt.

**Query default cap:** If you omit `--max-symbols`, the heuristic `-q` slice defaults to **12** symbols (not 15). The brief also includes **`NEXT_OPEN`** (suggested file:line ranges) and **same-name folding** (one primary block per simple name, plus a compact **`SAME_NAME`** block / `same_name_also` when the slice contained duplicates).

### 2.2 Saving context: `--names-only` (instead of a wide text grep)

Same filter, qualified names only:

```bash
python -m nexus . -q "mutation" --max-symbols 10 --names-only
```

**Measured:** about **11 lines**, **~480 characters** total — a practical **orientation** step for the model.

**Annotated names-only** (one compact line per primary symbol: `qualified_name | confidence | tags | layer | file:line`):

```bash
python -m nexus . -q "mutation" --max-symbols 10 --names-only --annotate
```

Use this when plain names-only saves tokens but models (or humans) still need **uncertainty and layer** without opening the full brief. Duplicates with the same simple name are still folded; the footer **`SAME_NAME`** lines list alternates when present.

### 2.3 Naive counterfactual: “everything that looks like a definition”

As a **proxy** for “agent pastes a wide grep into the prompt”: all lines containing the word `def` under `src/` and `tests/` (PowerShell `Select-String`).

**Measured:** **208 hit lines**, **~10,200 characters** of raw line text (no paths/metadata).

**Interpretation (careful):** This is **not** semantically the same as `mutation` — but it shows **order of magnitude**: broad text hit lists **scale with repo growth**; **`--names-only` with a fixed `--max-symbols`** stays **small**.

### 2.4 Full short brief vs. name list

| Mode | Order of magnitude (Nexus repo, `mutation`, 10 symbols) |
|------|-----------------------------------------------------------|
| `--names-only` | ~0.5 KB, ~11 lines |
| Full text brief (reads, calls, chains, …) | ~12 KB, ~130 lines |

**Implication:** Start **thin**, then **read_file** on 1–3 paths; pull the **full brief** only when the question needs it — otherwise you pay many structured tokens per symbol.

### 2.5 Reproducible “token budget” telemetry (`--metrics-json`)

For **diffing** runs against a target (CI, before/after refactors, or policy caps), `nexus` can emit **one JSON object per invocation** on **stderr** (prefix `[NEXUS_METRICS]`, stdout unchanged — pipe-safe):

```bash
python -m nexus . -q "mutation" --max-symbols 10 --metrics-json 2>metrics_line.txt
# or: NEXUS_METRICS_JSON=1
```

Fields include **`output_chars`**, **`output_lines`**, **`est_tokens_chars_div_4`** (rough heuristic: characters÷4), **`slice_cap_effective`**, optional **`symbols_in_heuristic_slice`** / **`slice_fill_ratio`**, graph dimensions, and when the stdout text contains them, **`context_handoff`** (`next_open_suggestions`, `same_name_fold`).

**Model-aligned token counts (optional):** install **`pip install 'nexus-inference[metrics]'`** (pulls **`tiktoken`**). Then metrics may include **`output_tokens_tiktoken`** plus a small **`tokenizer`** object (`backend`, and either **`encoding`** or **`model`**). Choose the encoding explicitly so comparisons stay stable:

- **`NEXUS_TIKTOKEN_ENCODING`** — default **`cl100k_base`** if unset (good enough for many GPT-4/4o-style models for **relative** diffs).
- **`NEXUS_TIKTOKEN_MODEL`** — e.g. **`gpt-4o`** → `tiktoken.encoding_for_model(...)` (closer to “what OpenAI counts” for that family).

**Slice source weight (optional):** `NEXUS_METRICS_SLICE_SOURCE_TOKENS=1` adds **`slice_source_tokens_total`**: tiktoken count over **raw source lines** of symbols in the slice (file reads, capped via `NEXUS_METRICS_SLICE_SOURCE_MAX_SYMBOLS`, default 40, max 500). With `NEXUS_METRICS_SLICE_SOURCE_DETAIL=1`, also per-symbol **`slice_source_tokens_by_symbol`**. Derived fields when possible: **`slice_symbols_total`**, **`compression_ratio`** (output tokens ÷ slice-source tokens), **`density_source_over_output`** (inverse), **`avg_source_tokens_per_symbol`**. If the CLI passed **`--max-symbols`**, **`max_symbols_cli_explicit`** is set; **`slice_cap_effective`** is always the cap used (including default **12** when `-q` is set but `--max-symbols` omitted).

This is **not** the same as “tokens in the brief text”; it estimates **how much source text** the slice points at — useful for compression / tuning, not for billing.

Tokenizer choice must match **your** deployment model for **absolute** budgets; for **A/B on one setup**, any fixed encoder is enough. This does **not** replace IDE session dashboards (reasoning + tools + cache); see §1.1 and [`usage-metrics.md`](usage-metrics.md).

**Relevant universe (optional, extra cost):** `NEXUS_METRICS_RELEVANT_UNIVERSE=1` adds **`relevant_symbols_total`** — count of symbols that the **same** heuristic slice would return with a very large internal cap (same ranking as `-q`, effectively “all that would ever enter the slice before truncation”). If **`slice_symbols_total`** is present, **`slice_relevant_coverage_ratio`** = slice ÷ relevant (how much of the heuristic universe fits under the current cap).

**Batch benchmarks:** from the Nexus checkout, run [`extras/nexus_benchmark.py`](../extras/nexus_benchmark.py) to execute `nexus … --metrics-json` over multiple `--repo` / `--repos-list` and `--query` / `--queries-file`, with optional `--relevant-universe`, `--slice-source`, `--tiktoken-encoding`, `--out-json` / `--out-csv`.

**Perspektive `agent_compact` + Felder:** Mit `--perspective agent_compact` bleibt dieselbe Slice-Heuristik wie bei Agent-Namenlisten; die **Ausgabegröße** steuert **`--compact-fields`** (`minimal` / `standard` / `full` oder explizite Liste). Der Shortcut **`--agent-mode`** setzt `agent_compact` + `minimal` + `--max-symbols 10` (überschreibbar). In den Metriken erscheinen dann u. a. **`compact_fields`** und bei `--agent-mode` **`agent_mode`: true** — für A/B und Regressionen. Vollständiger Bericht: **[Patchnotes → 2026-04-03](patchnotes/2026-04-03-agent-output-und-metriken.md)**; Format-Überblick: **[`docs/patchnotes/README.md`](patchnotes/README.md)**.

---

## 3. Reference: larger production trees (smoke / exploration runs)

**Measuring stick (canonical):** **Disk** and **`.py` footprint** for **Nexus**, **Aether VPN**, and **TTRPG Studio** (measured **2026-04-03**, methodology, table) live in **[`case-study-cross-repo-orientation.md` § Measuring stick](case-study-cross-repo-orientation.md#measuring-stick-measured-sizes-2026-04-03)**. §§3.1–3.2 below **hang off** those numbers; they do not define a second ruler.

Nexus was used for **structure and mutation orientation** in **two** larger Python projects (including an **Aether VPN** backend and **TTRPG Studio** areas) — **without** publishing raw graph exports (see `SECURITY.md`).

### 3.1 Typical index size (Aether VPN backend snapshot — scan scope, not full repo)

From an internal evaluation of a **Python service tree** (FastAPI-style layout). These numbers describe **what the scanner ingested under that root**, **not** the **total on-disk size** of the whole product repository (which can include large non-Python trees, clients, assets, etc.).

| Metric | Order of magnitude |
|--------|-------------------|
| `.py` files scanned | **82** |
| Symbols | **496** |
| Graph edges | **392** |

**Same checkout, filesystem (2026-04-03, `F:\Aether VPN`, Windows):** **~605 MB** total on disk (all files, recursive); **82** `*.py` files and **~507 KB** `.py` bytes using the same path-segment excludes as **[`case-study-cross-repo-orientation.md`](case-study-cross-repo-orientation.md)** (`.git`, `venv`, `.venv`, `__pycache__`, `node_modules`, `dist`, `build`). **Total clone ≫ `.py` text** — assets, clients, vendor trees, etc.

**Message:** The **one-time** scan produces a graph of this size — that is **CPU work**, not token budget. What reaches the LLM is controlled by **brief length** and **names-only**. **Do not** use this subsection to claim “the Aether VPN repo is ~7 MB” or to build a **cross-repo disk-size league table** without explicit counting rules.

### 3.2 TTRPG Studio

No published raw JSON; the same **tiering** applies: with **hundreds of symbols**, wide grep or full-text context often grows faster than **capped** Nexus output with a hard `--max-symbols`.

**Filesystem (2026-04-03, `F:\TTRPG Studio`, Windows):** **~7.1 GB** total on disk (all files, recursive); **4524** `*.py` files and **~65 MB** `.py` bytes with the same path-segment excludes as the **[cross-repo case study](case-study-cross-repo-orientation.md)**. That **`.py` mass** is the right order of magnitude for “naive ingest all Python source” horror stories — **not** the same as **graph size** for a given scan root.

**Smoke scan (local checkout, representative):** one run on `F:\TTRPG Studio` reported on the order of **153** `.py` files indexed, **~2100** symbols, **~2900** call edges — a **narrower scan scope** (e.g. a single package subtree), **not** “all **4524** `.py` files” above. Again: **CPU/local graph size**, not prompt size. Use `-q` + `--max-symbols` / `--names-only` / `--annotate` so what reaches the LLM stays bounded.

---

## 4. Log-style example: what the agent “sees”

**A — wide (many hit lines):**

```text
# Style: 208 lines of "def ..." — excerpt only
def main(...):
def attach(...):
def scan(...):
def _scan_impl(...):
# ... hundreds more lines, no edges, no confidence
```

**B — Nexus, orientation (fixed cap):**

```text
REPO: …
Files: 34  Symbols: 162  Edges: 191
src.nexus.cli_grep.main
src.nexus.scanner._scan_impl
src.nexus.cli.main
# … up to max. 10 names
```

**C — Nexus, focused brief (only when needed):**  
full block with reads/calls/mutation_chain — **more expensive**, but still **one** coherent structure instead of random grep fragments.

---

## 5. Amortization (back-of-the-envelope)

- **One-time:** scan time \(T_{\text{scan}}\) (seconds to a few minutes, depending on machine and repo). **0 LLM tokens.**
- **Per agent turn:** If you send **~0.5k characters** (name list) instead of **~10k characters** (“grep wall”), you save on the order of **~9.5k characters per turn** — in tokens, often **thousands fewer tokens per loop**, depending on tokenizer and model.
- After **a few** such turns, the scan has **paid for itself** in context cost, without committing sensitive graph exports.

This is **not** a guarantee for every task — bad queries can make Nexus outputs empty or bloated, just like grep. The **decision engine** in the Cursor rule (`nexus-over-grep.mdc`) exists for that: thin first, read, then escalate.

**Link to §1.1:** Scalar savings are only half the story. The **reliable** win is **not** funding **search** with LLM context for that step — see **§1.1** (totals vs purpose).

### Amortization — intuition

Think of the graph build as **fixed local overhead** and each prompt as **recurring variable cost**. Nexus moves spending from “variable” (huge unstructured text every turn) to “fixed + capped” (one scan, then bounded briefings). The break-even number of turns is small whenever you would otherwise paste large search results repeatedly. Prefer to describe wins as **“search tokens → CPU”** plus optional **total** delta, not **total alone**.

---

## 6. Reproduce it yourself

```bash
# Header + bounded brief (omit --max-symbols to use default cap of 12 in query mode)
python -m nexus <path-to-repo> -q "mutation" --max-symbols 15

# Minimal-token orientation
python -m nexus <path-to-repo> -q "mutation" --names-only --max-symbols 25

# Names + confidence/tags/layer/file:line (still compact)
python -m nexus <path-to-repo> -q "mutation" --names-only --annotate --max-symbols 15

# Slice → grep only a few files
nexus-grep <path-to-repo> -q "YourConcreteSymbol" --max-symbols 20
```

For honest **before/after** metrics in your setup: compare **character counts** (or tokens) of prompts with and without Nexus for the **same** task — and, if possible, **label** chunks by **purpose** (orientation vs read vs answer) so you see **what** moved off the model (see **§1.1**).

**See also:** [Cursor usage metrics and Nexus — why the dashboard looks “broken”](cursor-metrics-nexus.md) — dashboard “0” / Included vs. local scan, what is (not) being measured.

---

## 7. Empirical session totals (screenshots)

For **before/after style** evidence from real Cursor agent sessions (totals and **Cache Read** breakdowns), see **[`usage-metrics.md`](usage-metrics.md)** — figures under [`docs/assets/usage-metrics/`](assets/usage-metrics/) (committed **SVG placeholders**; optional **PNG** replacements), methodology and caveats in that page (including a **self-scan** of the Nexus repo with Nexus, §“Self-scan”).

**Why the win grows with repo size (architecture, not hype):** **[`nexus-scaling-law.md`](nexus-scaling-law.md)** — informal “scaling law” (amortized scan + bounded queries vs unstructured search in **N**).
