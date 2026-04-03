# Case study: Cross-repo orientation without opening source files

This document records a **concrete agent session** (Cursor + Nexus) that compared **two unrelated local Python checkouts** using **only structural queries** — no `read_file` / editor opens of source, README, docs, or concept notes in either target repository.

It is **illustrative (N=1)**, not a controlled benchmark. It complements the **TTRPG Studio A/B** in [`usage-metrics.md`](usage-metrics.md) by highlighting a different axis: **what “understanding” costs when you refuse naive full-tree text retrieval.**

---

## Task

**Compare** two repositories **conceptually**:

| Repository | Role in the study |
|------------|-------------------|
| **Aether VPN** (local checkout) | Backend-heavy tree: API routers, WebSocket, encyclopedia/chronicle/sandbox surfaces, sync tooling. |
| **TTRPG Studio** (local checkout) | Desktop-oriented tree: application services, resolver engine, PyQt workspaces, transcription/plugins. |

**Constraint:** Derive context from **structure** (Nexus map queries) only — **do not** read README, `/docs`, or concept folders in those repos.

---

## Method

From a Nexus development checkout:

- `python -m nexus.cli_opc map …`
- `python -m nexus.cli_opc locate …`
- `python -m nexus.cli_opc grep …`

…over each repo root (PowerShell-safe quoting for `-q`). **No** agent tool used to open files inside **Aether VPN** or **TTRPG Studio**.

**Note:** Nexus still **parses** `.py` files on disk during inference — the point is that the **LLM never received raw file bodies** for exploration; it received **bounded map slices** (symbols, calls, writes, paths).

---

## What the map showed (high level)

- **Aether (Python slice):** FastAPI-style **`aether_backend.api.*`** (encyclopedia, chronicle, sandbox, files, hooks), **`websocket_endpoint`** + chat logs, **`EncySyncManager`**, formula/method execution paths. VPN-specific strings did **not** dominate the Python map (product naming vs. visible code focus).
- **TTRPG Studio:** Central **`app.services.application`**, **`ResolverEngine`**, **`HostWorkspace` / `ClientWorkspace`**, Whisper/transcription services, plugin/webview UI — a **monolithic desktop** architecture vs. Aether’s **server + separate client folder** layout.

**Outcome:** A coherent **architectural comparison** (shared TTRPG-adjacent domain ideas; different deployment shape) without pasting repository text into the model context.

---

## Scale contrast (why “not nice optimization”)

Rough **on-disk Python** footprint (`.py` files; paths like `venv` / `.venv` excluded in the count used for the narrative):

| Checkout | Approx. `.py` files | Approx. `.py` bytes |
|----------|---------------------|---------------------|
| Aether VPN | ~90+ | ~0.7 MB |
| TTRPG Studio | thousands | ~tens of MB of `.py` alone |

**Naive mental model:** If the model had to **ingest all source as prompt text** to orient, token cost scales **roughly with raw bytes** (order-of-magnitude **÷3–5 characters per token** for code) — i.e. **millions** of tokens for the larger tree, **before** reasoning — and is **not** repeatable as a single context window.

**Nexus path:** Each query returns a **small structured slice**; the session’s **total** Cursor-reported tokens (~**110k** in one captured row, with **Cache Read** dominating) covered **orientation + synthesis + rules + history** — not “70 MB of code in the prompt.”

Interpretation: the win is not merely “compression” of text — it is a **representation shift**: **query a graph-shaped index**, then open files **only when deliberately targeted** (this run: **zero** such opens in the two subject repos).

---

## Billing screenshot (same session family)

One Cursor usage row for this style of session showed approximately:

- **Total** ~**110k** tokens  
- **Cache Read** ~**85%** of total  
- **Input** / **Output** much smaller than total  

That pattern matches **large recycled context** (rules, prior turns, tool outputs), not “Nexus printed megatokens.” The qualitative claim stands: **structural retrieval avoids shipping whole-repo text to the model.**

Canonical copy (repo): [`docs/assets/usage-metrics/cursor-cross-repo-orientation-110k.png`](assets/usage-metrics/cursor-cross-repo-orientation-110k.png)

![Cursor usage breakdown — cross-repo Nexus orientation session (~110k total, Cache Read dominant)](assets/usage-metrics/cursor-cross-repo-orientation-110k.png)

---

## Honesty constraints

- **Heuristic map:** Missing edges, noisy tags, and query sensitivity still apply — see [`README.md`](../README.md) “Repo health & known limitations.”
- **Session total ≠ Nexus stdout only:** Dashboard **Total** includes the **whole** agent conversation, not just CLI output.
- **Cross-repo counts:** Re-run `Get-ChildItem` / `find` with your own ignore rules if you need audit-grade file statistics.

---

## Related docs

- [`usage-metrics.md`](usage-metrics.md) — Cursor dashboards, controlled TTRPG A/B, gallery caveats  
- [`token-efficiency.md`](token-efficiency.md) — CLI metrics, amortization  
- [`nexus-scaling-law.md`](nexus-scaling-law.md) — informal scaling argument  

---

## Reproduce (shape only)

```powershell
$env:PYTHONPATH = "path\to\nexus\src"
python -m nexus.cli_opc map -q "package layout modules" "F:\YourRepo"
python -m nexus.cli_opc locate -q "your topic" "F:\YourRepo"
```

Use [`docs/tutorial-nexus-opc-isa.md`](tutorial-nexus-opc-isa.md) for opcode details and `--dry-run`.
