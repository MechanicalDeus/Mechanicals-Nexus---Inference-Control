# Nexus opcode ISA — `nexus-opc` tutorial

**Audience:** humans and **LLM agents** that should run Nexus **without inventing** `nexus` / `nexus-grep` flags.  
**Prerequisite:** basic Nexus ideas (`-q`, bounded slices) — see **[`TUTORIAL.md`](../TUTORIAL.md)** and **[`tutorial-nexus-cli-and-ui.md`](tutorial-nexus-cli-and-ui.md)**.

---

## Why this exists

Plain `nexus` has many flags (`--perspective`, `--agent-mode`, `--center-ref`, …). In agent loops, models sometimes **hallucinate** combinations or mutual exclusions.

**`nexus-opc`** (module: **`nexus.cli_opc`**) exposes a **small vocabulary**: you pick an **opcode** (subcommand) and **operands**. Each opcode maps to a **fixed** subprocess `argv` — same engine as the normal CLI, **deterministic wiring**.

| Idea | Detail |
|------|--------|
| **Invariant** | Still one scan, one graph, same projections as `python -m nexus …`. |
| **Variable** | You choose a **named pipeline** instead of assembling flags. |
| **Escape hatch** | If you need `impact` / `why`, odd perspectives, or full `--json`, use **`nexus`** manually (see **When not to use opcodes**). |

---

## Install and entry points

After installing **`nexus-inference`** (e.g. **`python -m pip install "nexus-inference @ git+https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control.git"`**, **`pip install nexus-inference`** from PyPI, or **`pip install -e .`** from a clone):

```bash
nexus-opc catalog
# equivalent:
python -m nexus.cli_opc catalog
```

From a clone without install:

```bash
PYTHONPATH=/path/to/Nexus/src python -m nexus.cli_opc catalog
```

**Machine-readable manifest** (for tools / agents):

```bash
nexus-opc catalog --json
```

---

## Global flags (all opcodes)

| Flag | Effect |
|------|--------|
| **`--dry-run`** | Print one JSON line `{"argv":[...]}` and **do not** execute. Use to verify the exact command. |
| **`--opc-log-append PATH`** | After a **real** run, append one **JSONL** record (`kind: nexus_opc_run`, opcode, duration, exit code, argv, …). Or set **`NEXUS_OPC_LOG_APPEND`**. |
| **`--opc-roi-score FLOAT`** | Optional numeric label (e.g. from benchmark ROI) stored in the log line. |
| **`--opc-run-id ID`** | Optional correlation id (session / job). |

**Aggregate logs:**

```bash
python -m nexus.cli_opc stats .nexus-opc-runs.jsonl
```

Emits `opcode_stats` with **count**, **roi_samples**, **avg_roi** per opcode.

---

## Operand order (important)

For opcodes that take **`-q` / `--query`**, put the query **before** the optional **path** (argparse layout):

```text
nexus-opc locate -q "mutation flow" .
nexus-opc map -q "resolver" src/mypkg
```

Default **path** is **`.`** if omitted.

---

## Opcodes → meaning

| Opcode | When to use | Underlying pipeline |
|--------|-------------|---------------------|
| **catalog** | List opcodes; **`--json`** for agents | manifest only |
| **map** | Heuristic **slice** only (no full agent brief path) | `--perspective heuristic_slice` |
| **locate** | Default **agent** entry: compact structural slice | `--agent-mode` → `agent_compact` |
| **explain** | One symbol: trust / detail | `--perspective trust_detail` + `--center-ref` |
| **focus** | Canonical **focus graph** JSON | `python -m nexus focus … -s …` |
| **grep** | Map-bounded search | `python -m nexus.cli_grep …` |
| **policy** | Safe caps / staged retrieval | `python -m nexus.cli_policy …` |
| **bench** | Batch benchmark runs | `extras/nexus_benchmark.py` (see below) |
| **compare** | Diff two benchmark JSONs (ROI) | `nexus_benchmark --roi-compare OLD NEW` |
| **stats** | Roll up **`--opc-log-append`** JSONL | local aggregation |

Details and `argv` templates are in **`catalog --json`** and in **[`src/nexus/cli_opc.py`](../src/nexus/cli_opc.py)** (`catalog_manifest`).

---

## Examples (POSIX shell)

```bash
# Agent-style orientation (compact)
nexus-opc locate -q "mutation resolver" .

# Slice only (heuristic pick, perspective slice)
nexus-opc map -q "state" src/nexus --max-symbols 15

# Trust view for one symbol
nexus-opc explain --center-ref "nexus.cli_opc.main" .

# Focus payload JSON
nexus-opc focus -s "nexus.cli_opc.main" .

# Policy wrapper
nexus-opc policy -q "state" .

# Dry-run: see exact argv
nexus-opc --dry-run locate -q "flow" .
```

---

## Extra flags after `--`

For **map**, **locate**, **explain**, **grep**, **policy**, you may append **`--`** and then **additional** arguments forwarded to the underlying `nexus` / `cli_grep` / `cli_policy` invocation (e.g. **`--control-header`**).

```bash
nexus-opc locate -q "mutation" . -- --control-header
```

---

## PowerShell (Windows)

Quote **`-q`** and flags so the shell does not eat them:

```powershell
Set-Location F:\myrepo
$env:PYTHONPATH = "F:\Nexus\src"   # if using a clone without install
python -m nexus.cli_opc locate "-q" "mutation flow" "."
python -m nexus.cli_opc --dry-run locate "-q" "mutation" "."
```

---

## Benchmark opcodes (`bench`, `compare`)

These need **`extras/nexus_benchmark.py`**, which ships in the **Nexus checkout**. Discovery walks parents from the installed `nexus` package; if missing (bare PyPI tree), set:

```bash
export NEXUS_BENCHMARK_SCRIPT=/path/to/Nexus/extras/nexus_benchmark.py
```

```bash
# Pass benchmark script arguments after -- (optional leading -- stripped)
nexus-opc bench -- --help

# Compare two saved JSON outputs from benchmark runs
nexus-opc compare old.json new.json
```

---

## When **not** to use opcodes (use `nexus` directly)

- **`llm_brief`** with **special query modes** (`impact Class`, `why …`, long mutation narratives).
- Explicit **`--perspective llm_brief`** / **`mutation_trace`** / **`query_slice_json`** not covered by the table above.
- Full repo export: **`nexus … --json`** (treat as **security-sensitive** — see **`SECURITY.md`**).

Run **`nexus …`** / **`nexus-grep`** / **`nexus-policy`** as documented in **[`cli-perspective.md`](cli-perspective.md)** and **`AGENTS.md`**.

---

## Cursor / agents (Nexus checkout)

| Asset | Role |
|-------|------|
| **`.cursor/skills/nexus-opc-isa/SKILL.md`** | Opcode table, `--dry-run`, logging. |
| **`.cursor/commands/nx-*.md`** | Slash-command prompts (`/nx-locate`, `/nx-map`, …). |
| **`.cursor/rules/nexus-checkout-cli-default.mdc`** | Checkout: ISA first, manual CLI fallback. |

Installed **`nexus-cursor-rules`** copies **`nexus-over-grep.mdc`**, which now mentions **`nexus-opc`** as the preferred path when available.

---

## See also

| Doc | Content |
|-----|---------|
| [`AGENTS.md`](../AGENTS.md) | Agent checklist, checkout vs other repos |
| [`cli-perspective.md`](cli-perspective.md) | `--perspective` contract |
| [`tutorial-nexus-cli-extended.md`](tutorial-nexus-cli-extended.md) | Long CLI reference + console shots |
| [`patchnotes/2026-04-03-nexus-opc-isa.md`](patchnotes/2026-04-03-nexus-opc-isa.md) | Changelog-style note for this ISA wave |
| [`tests/test_cli_opc.py`](../tests/test_cli_opc.py) | Opcode / argv tests |

---

## One-minute recap

1. **`nexus-opc catalog --json`** — know the opcodes.  
2. **`nexus-opc --dry-run locate -q "…" .`** — verify `argv`.  
3. **`nexus-opc locate -q "…" .`** — default agent structural query.  
4. **`stats`** on a JSONL log — see which opcodes you actually use.  
5. Fall back to **`nexus -q`** when the ISA does not cover the question.
