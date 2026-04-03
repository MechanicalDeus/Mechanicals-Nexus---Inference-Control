# Changelog

**Version-tagged summaries** for end users and integrators: **[GitHub Releases](https://github.com/MechanicalDeus/Mechanicals-Nexus---Inference-Control/releases)**.

**Structured technical notes** between releases (CLI, metrics, perspectives, benchmarks): **[`docs/patchnotes/README.md`](docs/patchnotes/README.md)**.

The **package version** is defined in **`pyproject.toml`**. For **install paths** (PyPI, **pip from GitHub**, editable clone) and **product limits**, see **[`README.md` → Installation](README.md#installation)**.

---

## [0.1.0] — 2026-04-03

First **packaged milestone** for **nexus-inference**: structural inference over Python trees, CLI + agent-oriented outputs, opcode ISA, and Cursor/agent docs. This is still **`0.x`**: heuristics, ranking, and projection details may evolve; treat **JSON / perspective outputs** as integration surfaces and read **patchnotes** when upgrading.

### Highlights

- **Core:** AST + heuristic **inference graph** (symbols, calls, reads/writes, mutation hints, layers, confidence).
- **CLI:** `nexus`, `nexus-grep`, `nexus-policy`, `nexus-opc`, `nexus-cursor-rules`, optional `nexus-console` (see `pyproject.toml` `[project.scripts]`).
- **Agents:** `--agent-mode` (compact structural slice); bounded `--max-symbols`, `--perspective`, `--compact-fields` (see `docs/cli-perspective.md`, `docs/token-efficiency.md`).
- **Opcode ISA:** `nexus-opc` with fixed pipelines (`locate`, `map`, `grep`, `policy`, …), `--dry-run`, optional run logging (`docs/tutorial-nexus-opc-isa.md`, `docs/patchnotes/`).
- **Policy:** `nexus-policy` safe-default retrieval profile (`src/nexus/policy/`).
- **Telemetry:** `[NEXUS_METRICS]` / `--metrics-json` for per-invocation output metrics.
- **Docs:** `docs/README.md`, `AGENTS.md`, `SECURITY.md`, usage metrics narrative (`docs/usage-metrics.md`).

### Contract impact (agents & integrators)

| Topic | Notes for `0.1.0` |
|-------|-------------------|
| **Entrypoints** | Use documented console scripts; behavior is versioned with the **wheel/sdist**, not loose scripts. |
| **Recommended agent flow** | `nexus-opc locate …` or `nexus … --agent-mode -q "…"` first; then narrow reads — caps are part of the contract. |
| **`--json` / perspectives** | Machine-readable and **text projection** outputs may change in **`0.x` minor** releases; check **patchnotes** and release **Contract impact** when pinning automation. |
| **Semantics** | Graph is **static / heuristic** — not runtime truth; **confidence** and **ordering** are allowed to move until a future **1.x** “stable inference contract” statement. |

### Links

- Compare: *n/a* (first release line tag — use `v0.1.0` when tagging).
- Deep dives: [`docs/patchnotes/2026-04-03-nexus-opc-isa.md`](docs/patchnotes/2026-04-03-nexus-opc-isa.md), [`docs/patchnotes/2026-04-03-agent-output-und-metriken.md`](docs/patchnotes/2026-04-03-agent-output-und-metriken.md).
