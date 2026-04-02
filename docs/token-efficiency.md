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

---

## 3. Reference: larger production trees (smoke / exploration runs)

Nexus was used for **structure and mutation orientation** in **two** larger Python projects (including an **Aether VPN** backend and **TTRPG Studio** areas) — **without** publishing raw graph exports (see `SECURITY.md`).

### 3.1 Typical index size (Aether VPN, representative snapshot)

From an internal evaluation (legacy FastAPI / service tree):

| Metric | Order of magnitude |
|--------|-------------------|
| `.py` files scanned | **82** |
| Symbols | **496** |
| Graph edges | **392** |

**Message:** The **one-time** scan produces a graph of this size — that is **CPU work**, not token budget. What reaches the LLM is controlled by **brief length** and **names-only**.

### 3.2 TTRPG Studio

No published raw JSON; the same **tiering** applies: with **hundreds of symbols**, wide grep or full-text context often grows faster than **capped** Nexus output with a hard `--max-symbols`.

**Smoke scan (local checkout, representative):** one run on `F:\TTRPG Studio` reported on the order of **153** `.py` files indexed, **~2100** symbols, **~2900** call edges — again **CPU/local graph size**, not prompt size. Use `-q` + `--max-symbols` / `--names-only` / `--annotate` so what reaches the LLM stays bounded.

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
