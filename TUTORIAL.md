# Nexus — tutorial

This file is the **entry point** for learning Nexus by example. It points to the full walkthrough (text + screenshots) in `docs/`.

**What Nexus is for:** The **CPU scans once**; the **LLM queries** that map (**`-q`**, caps) and gets **IR-like structural slices** — callers, writes, `NEXT_OPEN` — **without** using “open file” as the primary way to explore. Refining means **another query**, not re-filtering the repo by hand. *Stop reading code. Start querying structure.*

---

## Start here

**[→ Full tutorial: CLI + Inference Console (one map, two surfaces)](docs/tutorial-nexus-cli-and-ui.md)**

**[→ Extended CLI tutorial (all new console screenshots + command deep dive)](docs/tutorial-nexus-cli-extended.md)**

**[→ Opcode ISA (`nexus-opc`) — deterministic pipelines for agents](docs/tutorial-nexus-opc-isa.md)**

The full guide is written as a **story**: first the **CLI output** (what you already get in the terminal), then **screenshots** that replay the **same internal pipeline** in the Inference Console. The **extended** page adds every **`docs/ui-screenshots/`** frame, PowerShell patterns, and **§0** (CLI proof + metrics assets under `console tutorial/`).

- **CLI in the IDE** — local run, **no LLM API** for the scan, **bounded** briefs and `NEXT_OPEN`.
- **Inference Console** — optional GUI (`nexus-console`); **Copy Brief** = `nexus -q` stdout for the same inputs.
- **Invariant** — one `InferenceGraph`; UI = X-ray of the CLI, not a second analyzer.

---

## Shorter paths

| Topic | Document |
|--------|----------|
| **Repository deep dive** (architecture, modules, security, roadmap) — whole-picture read | **EN** [`docs/repository-analysis.md`](docs/repository-analysis.md) · **DE** [`docs/repository-analyse.md`](docs/repository-analyse.md) |
| **Agent + Cursor** (loop, terminal, rules) | [`docs/nexus-agent-cursor.md`](docs/nexus-agent-cursor.md) |
| Console only (quick steps) | [`docs/inference-console-tutorial.md`](docs/inference-console-tutorial.md) |
| **Extended CLI tutorial** (all `ui-screenshots/`, PowerShell, `console tutorial/` extras) | [`docs/tutorial-nexus-cli-extended.md`](docs/tutorial-nexus-cli-extended.md) |
| **Opcode ISA** (`nexus-opc`, `--dry-run`, agent logging, `stats`) | [`docs/tutorial-nexus-opc-isa.md`](docs/tutorial-nexus-opc-isa.md) |
| Console architecture & exports | [`docs/inference-console-deep-dive.md`](docs/inference-console-deep-dive.md) |
| Token caps & amortization (totals **vs** purpose / search offloaded) | [`docs/token-efficiency.md`](docs/token-efficiency.md) (§1.1) |
| **Real session screenshots:** token totals with vs without Nexus | [`docs/usage-metrics.md`](docs/usage-metrics.md) · PNGs in [`docs/assets/usage-metrics/`](docs/assets/usage-metrics/) |
| **Patch notes** (metrics keys, CLI/perspective changes, benchmarks) | [`docs/patchnotes/README.md`](docs/patchnotes/README.md) |
| **Cursor usage:** why the metric looks “broken” with Nexus | [`docs/cursor-metrics-nexus.md`](docs/cursor-metrics-nexus.md) |
| Narrative PoC | [`docs/proof-of-concept.md`](docs/proof-of-concept.md) |

**Inference Console screenshots (current UI)** live in **[`docs/ui-screenshots/`](docs/ui-screenshots/)**. **`cli-ide-proof.png`** (CLI in the IDE) and **Cursor / metrics** PNGs remain under **[`console tutorial/`](console tutorial/)** — see **`docs/tutorial-nexus-cli-extended.md` §0**.

---

## Install (minimal)

```bash
pip install -e .
nexus-grep . -q "mutation" --max-symbols 10
```

**Commands** (after install): **`nexus-opc`**, **`nexus`**, **`nexus-grep`**, **`nexus-policy`**, **`nexus-cursor-rules`**, **`nexus-console`** (GUI). The pip package name is **`nexus-inference`** — that is not a terminal command.

Optional GUI:

```bash
pip install -e ".[ui]"
nexus-console
```

---

## Related

- **[SECURITY.md](SECURITY.md)** — sensitive exports, `.nexusignore` / `.nexusdeny`  
- **[LICENSE](LICENSE)** — MIT  
- **[AGENTS.md](AGENTS.md)** — checklist for tools/agents using Nexus  
