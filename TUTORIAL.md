# Nexus — tutorial

This file is the **entry point** for learning Nexus by example. It points to the full walkthrough (text + screenshots) in `docs/`.

**What Nexus is for:** The **CPU scans once**; the **LLM queries** that map (**`-q`**, caps) and gets **IR-like structural slices** — callers, writes, `NEXT_OPEN` — **without** using “open file” as the primary way to explore. Refining means **another query**, not re-filtering the repo by hand. *Stop reading code. Start querying structure.*

---

## Start here

**[→ Full tutorial: CLI + Inference Console (one map, two surfaces)](docs/tutorial-nexus-cli-and-ui.md)**

That guide is written as a **story**: first the **CLI output** (what you already get in the terminal), then **screenshots** that replay the **same internal pipeline** in the Inference Console — so you see *what the CLI was doing anyway*, laid out as table, brief, detail, mutation, and graph.

- **CLI in the IDE** — local run, **no LLM API** for the scan, **bounded** briefs and `NEXT_OPEN`.
- **Inference Console** — optional GUI (`nexus-console`); **Copy Brief** = `nexus -q` stdout for the same inputs.
- **Invariant** — one `InferenceGraph`; UI = X-ray of the CLI, not a second analyzer.

---

## Shorter paths

| Topic | Document |
|--------|----------|
| Console only (quick steps) | [`docs/inference-console-tutorial.md`](docs/inference-console-tutorial.md) |
| Console architecture & exports | [`docs/inference-console-deep-dive.md`](docs/inference-console-deep-dive.md) |
| Token caps & amortization | [`docs/token-efficiency.md`](docs/token-efficiency.md) |
| Narrative PoC | [`docs/proof-of-concept.md`](docs/proof-of-concept.md) |

**Screenshots** (GUI + CLI-in-IDE) live in **[`console tutorial/`](console tutorial/)**.

---

## Install (minimal)

```bash
pip install -e .
nexus-grep . -q "mutation" --max-symbols 10
```

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
