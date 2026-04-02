# Nexus — tutorial

This file is the **entry point** for learning Nexus by example. It points to the full walkthrough (text + screenshots) in `docs/`.

---

## Start here

**[→ Full tutorial: CLI + Inference Console (one map, two surfaces)](docs/tutorial-nexus-cli-and-ui.md)**

That guide covers:

- **CLI in the IDE** — run `nexus` / `nexus-grep` in a terminal (Cursor, VS Code, …): local analysis, **no LLM API call** for the scan, **bounded** briefs and `NEXT_OPEN` hints so you do not grep-hunt the whole tree.
- **Inference Console** (optional GUI, `pip install -e ".[ui]"` then `nexus-console`) — same engine as the CLI; **Copy Brief** matches `nexus -q` for the same repo, query, and caps.
- **Invariant** — one `InferenceGraph` per scan; terminal, GUI, and clipboard are **projections**, not a second analyzer.

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
