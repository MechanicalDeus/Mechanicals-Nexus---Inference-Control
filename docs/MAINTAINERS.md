# Maintainer notes — documentation drift

Use this as a **short checklist** when you change shipping surfaces so the GitHub-facing story stays aligned.

## Measuring stick — measured checkout sizes (`case-study-cross-repo-orientation.md`)

The canonical **disk / `.py` table** (**§ [Measuring stick (measured sizes, 2026-04-03)](case-study-cross-repo-orientation.md#measuring-stick-measured-sizes-2026-04-03)**) was produced with a **one-off PowerShell script** on the author’s machine. If you need updated numbers, re-run the same methodology on your paths and update **that section** — do not “hand edit” without re-measuring or fork size claims into other pages.

## Install snippets (GitHub `git+https` URL)

The **pip-from-GitHub** one-liner is duplicated in several docs. If the **canonical repository URL** changes, search the repo for `MechanicalDeus/Mechanicals-Nexus---Inference-Control` and update every copy (start with [`README.md`](../README.md) → Installation).

## After changing `pyproject.toml`

| Check | Update if needed |
|--------|------------------|
| **`[project.version]`** | [`README.md`](../README.md) — status table (`0.x` milestone + version line). |
| **`[project.scripts]`** (new/removed CLI) | [`README.md`](../README.md) Installation · [`AGENTS.md`](../AGENTS.md) · [`docs/repository-analysis.md`](repository-analysis.md) / [`repository-analyse.md`](repository-analyse.md) · [`extras/cursor-rules/README.txt`](../extras/cursor-rules/README.txt) · bundled [`nexus-over-grep.mdc`](../src/nexus/cursor_rules/nexus-over-grep.mdc) (when agent-facing). |
| **`requires-python` / classifiers** | [`README.md`](../README.md) · CI matrix in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). |

## After CLI or default-output changes

| Check | Update if needed |
|--------|------------------|
| Defaults (`--max-symbols`, `--agent-mode`, perspectives) | [`README.md`](../README.md) · [`docs/token-efficiency.md`](token-efficiency.md) · [`AGENTS.md`](../AGENTS.md) · relevant **patchnote** under [`patchnotes/`](patchnotes/README.md). |
| New opcodes or ISA behavior | [`docs/tutorial-nexus-opc-isa.md`](tutorial-nexus-opc-isa.md) · [`.cursor/skills/nexus-opc-isa/SKILL.md`](../.cursor/skills/nexus-opc-isa/SKILL.md) if the table changes. |

## Releases and narrative

| Check | Update if needed |
|--------|------------------|
| User-visible release | **GitHub Release** + optional line in [`CHANGELOG.md`](../CHANGELOG.md). |
| Deep technical wave | New file under [`docs/patchnotes/`](patchnotes/README.md) + index row in `patchnotes/README.md`. |

## Navigation

New topical Markdown under **`docs/`** should be linked from **[`docs/README.md`](README.md)** so the README does not accumulate duplicate tables.
