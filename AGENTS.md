# AGENTS.md — Nexus for Cursor agents

Use this file as the **reference** when working in **any Python repo** and you need to **use or set up Nexus** (structural map instead of blind grep).

## Other repos: one-time setup per project

1. **Install Nexus** (usable everywhere):  
   `pipx install -e <path-to-nexus-clone>` **or** `pip install -e <path-to-nexus-clone>`  
   Without install: `PYTHONPATH=<nexus-clone>/src` and `python -m nexus …` / `python -m nexus.cli_grep …`.
2. **Install the Cursor rule** (ships in **`nexus-inference`**, module `nexus.cursor_rules`):  
   From the **target repo root**: **`nexus-cursor-rules install`** — writes `nexus-over-grep.mdc` to **`<your-repo>/.cursor/rules/`** (Cursor loads `.mdc` from there).  
   Alternatives: **`python -m nexus.cursor_rules install`**, print bundled path with **`nexus-cursor-rules --path`**, overwrite with **`install --force`**.  
   When hacking on Nexus itself: source **`src/nexus/cursor_rules/nexus-over-grep.mdc`**; notes in **`extras/cursor-rules/README.txt`**.
3. **Optional global:** copy the same `.mdc` to `%USERPROFILE%\.cursor\rules\` or paste into Cursor **User Rules**.
4. **Bookmark or share this `AGENTS.md`** — it complements the `.mdc` with commands; for inference exports see **`SECURITY.md`**.

## Design: token efficiency and grep

**Goal:** Agents should not drag half a repo into context via broad `rg` first. **Nexus** structures search; **`nexus-grep`** is the **default tier** (thin output). **Grep** still makes sense **after** narrowing or for non-Python — see the decision layer and **decision engine** in the `.mdc` (default: tight `nexus-grep` → read slice → STOP). Use **`nexus --json`** and long **`nexus -q`** briefs only when needed (export, chains, impact).

## 1. Default usage (when Nexus is available)

From the **target repo root** (or `src/<package>`):

```bash
nexus . -q "mutation" --max-symbols 25
nexus . -q "full mutation chain" --max-symbols 40
nexus . -q "impact ClassName"
nexus . -q "state" --names-only --max-symbols 50
nexus-grep . -q "mutation" --max-symbols 25
nexus . --json > nexus-inference.json
```

**Agent order on an unfamiliar codebase:** start with `nexus … --names-only` or `nexus-grep …` (structure → targeted name search in a few `.py` files), then open relevant files; do **not** start with broad `grep`/`rg`. Special queries (`impact`, `why`, …) stay on `nexus -q`, not `nexus-grep`.

**Windows PowerShell** without `nexus` on PATH:

```powershell
$env:PYTHONPATH = "F:\Nexus\src"   # adjust to your Nexus checkout
python -m nexus . "-q" "mutation" "--max-symbols" "20"
python -m nexus.cli_grep . "-q" "mutation" "--max-symbols" "25"
```

## 2. Checklist: Nexus in a **new** repo

1. **Check:** Does `nexus` or `python -m nexus --help` work (with `PYTHONPATH` on Nexus `src`)?
2. **If not — install once** (recommended):  
   `pipx install -e F:\Nexus` **or** `pip install -e F:\Nexus`  
   Replace `F:\Nexus` with your real checkout path.
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

## 4. When **not** to use Nexus

- Not Python, pure string search in config/logs → `grep` / editor search is fine.
- Very small file, known location → open the file directly.

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

Example local path: `nexus <path> --json > ./exports/my-graph.json` (keep `exports/` **ignored**).
