# AGENTS.md — Nexus (Nexus Code for Python)

Use this file as the **reference** when working in **any Python repo** and you need to **use or set up Nexus Code** — the **Python map** CLI (`nexus`, `nexus-opc`, `nexus-grep`, …): structural retrieval instead of blind grep. **Nexus** is the **product**; **Nexus Code** is that **code-oriented slice**.

**Cursor-specific explanation anchor** (agent loop, terminal, rules): **[`docs/nexus-agent-cursor.md`](docs/nexus-agent-cursor.md)** in the Nexus repo.

**Documentation index (`docs/`):** **[`docs/README.md`](docs/README.md)**.

**Changelog / releases:** **[`CHANGELOG.md`](CHANGELOG.md)** (links to GitHub Releases and patchnotes).

**Patch notes (this repo):** **[`docs/patchnotes/README.md`](docs/patchnotes/README.md)** — dated reports on metrics keys, perspectives, and CLI (e.g. `agent_compact`, `--compact-fields`, `--agent-mode`); template for new entries in the same folder.

## Working in the Nexus checkout (this repository)

When the open project **is** the Nexus source tree, agents should treat **Nexus Code** (inference map) as the **default retriever** — not a pile of blind `read_file` calls. This matches the enforced Cursor rule **`.cursor/rules/nexus-checkout-cli-default.mdc`**.

1. **Orient on `src/nexus` with Nexus Code (ISA first):** For *where does X live?* / *how is Y wired?*, prefer **`python -m nexus.cli_opc locate -q "<topic or identifier>" src/nexus`** from the repo root (or **`nexus-opc locate …`** on `PATH`; set `PYTHONPATH=<checkout>/src` if the package is not installed). Use **`python -m nexus.cli_opc --dry-run locate …`** to print the resolved **`argv`**. **Fallback** when you need flags/opcodes the ISA does not wrap, or `cli_opc` is unavailable: **`python -m nexus src/nexus --agent-mode -q "…"`**, **`python -m nexus.cli_grep src/nexus -q "…" --max-symbols 20`**, or **`python -m nexus.cli_policy …`** — see **`.cursor/rules/nexus-checkout-cli-default.mdc`** and **`docs/cli-perspective.md`**. Then **`read_file`** only at paths (and slices) Nexus Code returns — do not open `pyproject.toml`, `cli.py`, and random modules “just to be sure” first.
2. **Skip Nexus Code when already precise:** If the path, symbol, or line is explicit, read or edit directly.
3. **Trivial shell tasks:** e.g. start the Inference Console (**`python -m nexus.ui`** or **`nexus-console`**), run **`extras/nexus_benchmark.py`** — execute immediately; no pre-reading source unless the command fails and you need the error message’s hint.
4. **Opcode reference (Cursor checkout):** Full walkthrough **[`docs/tutorial-nexus-opc-isa.md`](docs/tutorial-nexus-opc-isa.md)**; skill **`.cursor/skills/nexus-opc-isa/SKILL.md`**; slash helpers **`/nx`** (Retriever-Reminder), **`/nx-map`**, **`/nx-locate`**, … in **`.cursor/commands/`**. Opcodes: `map`, `locate`, `explain`, `focus`, `grep`, `policy`, `bench`, `compare`, `catalog`, **`stats`**. Optional **run log + ROI:** `--opc-log-append` / `NEXUS_OPC_LOG_APPEND`, `--opc-roi-score`, **`--opc-run-id`**; aggregate with **`nexus-opc stats <file.jsonl>`**. Machine-readable list: **`python -m nexus.cli_opc catalog --json`**.

## Other repos: one-time setup per project

1. **Install Nexus** (package **`nexus-inference`**; Nexus Code CLI on `PATH`):  
   **From GitHub (no clone):** `python -m pip install "nexus-inference @ git+https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control.git"` (or `pipx install "…"` with the same URL).  
   **From PyPI:** `pip install nexus-inference` when published.  
   **From a clone:** `pip install -e <path-to-nexus-clone>` or `pipx install -e …`.  
   **Without install:** `PYTHONPATH=<nexus-clone>/src` and `python -m nexus …` / `python -m nexus.cli_opc …` / `python -m nexus.cli_grep …`.  
   Full order of options: **`README.md` → Installation**.
2. **Install the Cursor rule** (bundled in the **`nexus-inference`** package, import **`nexus.cursor_rules`**):  
   From the **target repo root**: **`nexus-cursor-rules install`** — writes `nexus-over-grep.mdc` to **`<your-repo>/.cursor/rules/`** (Cursor loads `.mdc` from there).  
   Alternatives: **`python -m nexus.cursor_rules install`**, print bundled path with **`nexus-cursor-rules --path`**, overwrite with **`install --force`**.  
   When hacking on Nexus itself: source **`src/nexus/cursor_rules/nexus-over-grep.mdc`**; notes in **`extras/cursor-rules/README.txt`**.
3. **Optional global:** copy the same `.mdc` to `%USERPROFILE%\.cursor\rules\` or paste into Cursor **User Rules**.
4. **Bookmark or share this `AGENTS.md`** — it complements the `.mdc` with commands; for inference exports see **`SECURITY.md`**.

## Design: token efficiency and grep

**Goal:** Agents should not drag half a repo into context via broad `rg` first. **Nexus Code** structures search; **`nexus-grep`** is the **default tier** (thin output). **Grep** still makes sense **after** narrowing or for non-Python — see the decision layer and **decision engine** in the `.mdc` (default: tight `nexus-grep` → read slice → STOP). Use **`nexus --json`** and long **`nexus -q`** briefs only when needed (export, chains, impact).

## 1. Default usage (when Nexus Code is available)

From the **target repo root** (or `src/<package>`):

```bash
nexus-policy . -q "state"
# Fast structural slice for agents (compact, default cap 10; override with --max-symbols / --compact-fields)
nexus . --agent-mode -q "mutation"
nexus . -q "mutation" --max-symbols 25
nexus . -q "full mutation chain" --max-symbols 40
nexus . -q "impact ClassName"
nexus . -q "state" --names-only --max-symbols 50
# Names-only with confidence/tags/layer/path (fewer follow-up turns than plain names)
nexus . -q "mutation" --names-only --annotate --max-symbols 20
nexus-grep . -q "mutation" --max-symbols 25
nexus . --json > ./exports/graph.json
```

**Slice behaviour (plain `-q`, not special modes):** default **`--max-symbols` is 12** if omitted. The textual brief adds **`NEXT_OPEN`** hints and folds **duplicate simple names** in the slice into one primary symbol plus compact **`SAME_NAME`** / `same_name_also` hints — see **`docs/token-efficiency.md`**. Real Cursor session screenshots (totals with vs without Nexus Code): **`docs/usage-metrics.md`**.

### 1.1 Canonical CLI perspectives (same language as UI / library)

Use **`nexus --perspective NAME`** when you want the **explicit contract** (stable enum strings: `heuristic_slice`, `llm_brief`, `query_slice_json`, `agent_names`, `agent_symbol_lines`, `agent_compact`, `trust_detail`, `focus_graph`, `mutation_trace`). Centered views need **`--center-kind`** (`symbol_id` | `symbol_qualified_name`) and **`--center-ref`**; **`mutation_trace`** needs **`--mutation-key`**. Do **not** mix `--perspective` with **`--names-only`**, **`--query-slice-json`**, **`--trace-mutation`**, **`--focus-graph`**, or **`--json`** in one command.

**Important:** **`heuristic_slice`** (heuristic pick only) and **`llm_brief`** (may activate `impact` / `why` / …) can **disagree** on the same `-q` — by design. For special-mode questions, use **`llm_brief`** or plain **`nexus -q`**.

**Agent entry (one switch):** **`--agent-mode`** sets **`--perspective agent_compact`**, **`--compact-fields minimal`**, and **`--max-symbols 10`** unless you pass those flags explicitly. Metrics include **`agent_mode`** and **`compact_fields`** when enabled.

Optional: **`--debug-perspective`** → one JSON line on **stderr** per render (`payload_kind`, `advice`, `provenance`); stdout unchanged.

Reference table and examples: **`docs/cli-perspective.md`**.

### Control header (recommended for agents)

To make the agent aware of how Nexus Code is currently configured, you can ask Nexus Code to
print a small **control header** before the actual answer:

- `--control-header` prints a bounded `[NEXUS_CONFIG] … [/NEXUS_CONFIG]` block to **stderr**
  (so `--json` on stdout stays valid JSON).
- Or set `NEXUS_CONTROL_HEADER=1` to enable it for every invocation.

Example:

```bash
nexus . -q "core system flow" --max-symbols 20 --control-header
```

**Agent order on an unfamiliar codebase:** start with `nexus … --names-only` or `nexus-grep …` (structure → targeted name search in a few `.py` files), then open relevant files; do **not** start with broad `grep`/`rg`. Special queries (`impact`, `why`, …) stay on `nexus -q`, not `nexus-grep`.

**Windows PowerShell** without `nexus` on PATH:

```powershell
$env:PYTHONPATH = "F:\Nexus\src"   # adjust to your Nexus checkout
python -m nexus.cli_policy . "-q" "state"
python -m nexus . "-q" "mutation" "--max-symbols" "20"
python -m nexus . "-q" "mutation" "--names-only" "--annotate" "--max-symbols" "15"
python -m nexus . "--perspective" "heuristic_slice" "-q" "flow" "--max-symbols" "20"
python -m nexus . "--perspective" "llm_brief" "-q" "impact MyClass" "--max-symbols" "15"
python -m nexus.cli_grep . "-q" "mutation" "--max-symbols" "25"
```

To enable control headers in PowerShell:

```powershell
$env:NEXUS_CONTROL_HEADER = "1"
python -m nexus . "-q" "core system flow" "--max-symbols" "20"
```

## 2. Checklist: Nexus Code in a **new** repo

1. **Check:** Does `nexus` or `python -m nexus --help` work (with `PYTHONPATH` on Nexus `src`)?
2. **If not — install once** (recommended):  
   `python -m pip install "nexus-inference @ git+https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control.git"`  
   or `pipx install "nexus-inference @ git+https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control.git"`  
   or from a checkout: `pipx install -e <path-to-Nexus>` / `pip install -e <path-to-Nexus>`.
3. **Rule in target repo:** run **`nexus-cursor-rules install`** in the target root (see “Other repos” above).
4. **Large / slow scans:** prefer `-q` + `--max-symbols` or `nexus-grep` over an immediate full-tree `--json`.

## 3. Environment variable (optional)

Set:

- `NEXUS_HOME` = path to the Nexus checkout (folder with `pyproject.toml`).

Example:

```powershell
$env:PYTHONPATH = "$env:NEXUS_HOME\src"
python -m nexus . "-q" "flow" "--names-only" "--max-symbols" "40"
```

## 4. When **not** to use Nexus Code

- Not Python, pure string search in config/logs → `grep` / editor search is fine.
- Very small file, known location → open the file directly.

## 4.1 When to prefer `nexus-policy`

Use **`nexus-policy`** when you want “safe by default” exploration:

- applies **scope gating** (project-code first)
- enforces **hard output caps** (chars + lines)
- reduces **high-noise** queries by lowering K and printing suggestions
- auto-escalates only from **stage 1 → stage 2** (never stage 3)

## 5. Where is the Cursor template?

- **Installed package:** `nexus.cursor_rules` → **`nexus-cursor-rules install`** from the target repo root.  
- **Nexus clone (source):** **`src/nexus/cursor_rules/nexus-over-grep.mdc`** — also **`extras/cursor-rules/README.txt`**.
- **Global (single machine):**  
  `%USERPROFILE%\.cursor\rules\nexus-python-context.mdc`  
  — same content; adjust paths (`F:\Nexus`, etc.) as needed.

## 6. Inference maps: keep local, do not commit

**Important:** Output from `nexus … --json` or saved graph exports are **not neutral logs**. They usually contain **symbol lists, call relationships, paths, and heuristic behavior hints** for the scanned code — comparable to **source plus an architecture index**. That can be **confidential and security-sensitive**.

- **Do not** commit them or paste full exports into public issues/PRs.  
- This repo uses **`.gitignore` patterns** and **`SECURITY.md`**; apply the same in **your** repo once you generate exports.  
- For external help: **redacted excerpts** or manually scrubbed short briefs only — **no** raw full graphs.

Example local path: `nexus <path> --json > ./exports/graph.json` (keep `exports/` **ignored**).

## 7. Inference modes (fresh vs cached)

Nexus supports an inference strategy switch:

- **fresh** (default): rebuild map each invocation (no persistent cache)
- **persistent / hybrid**: cache a full graph to a directory (explicit opt-in, security-sensitive)

CLI:

```bash
nexus . -q "state" --mode fresh
nexus . -q "state" --mode persistent --cache-dir ./.nexus-cache
nexus . -q "state" --mode hybrid --cache-dir ./.nexus-cache
```

Treat cached modes as **security-sensitive** (see `SECURITY.md`) and ensure cache
directories are ignored in VCS.
