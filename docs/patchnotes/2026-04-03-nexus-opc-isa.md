# Patchnote: `nexus-opc` Opcode-ISA, Agent-Rules, Doku

## Meta

- **Datum:** 2026-04-03
- **Bezug Version:** `nexus-inference` 0.1.0b1 (`pyproject.toml`)
- **Scope:** CLI (`nexus-opc`), Cursor-Rules, Agent-Doku, Tutorials

## Zusammenfassung

Es gibt einen stabilen **Opcode-CLI** **`nexus-opc`** (`python -m nexus.cli_opc`): feste Subcommands (**`map`**, **`locate`**, **`explain`**, **`focus`**, **`grep`**, **`policy`**, **`bench`**, **`compare`**, **`catalog`**, **`stats`**) mappen auf konkrete **`nexus`**-/`cli_grep`-/`cli_policy`-Aufrufe, damit Agenten **keine** `nexus`-Flags erfinden müssen. **`--dry-run`** gibt die **`argv`** als JSON aus; **`--opc-log-append`** / **`NEXUS_OPC_LOG_APPEND`** schreiben JSONL für Nachauswertung; **`stats`** aggregiert pro Opcode (**`count`**, **`avg_roi`**).

Die **Cursor-Rules** im Checkout und das gebündelte **`nexus-over-grep.mdc`** empfehlen **`nexus-opc`** **vor** manueller CLI, mit dokumentiertem **Fallback** für `impact`/`why`, weitere Perspektiven und **`--json`**.

Neues Tutorial: **[`docs/tutorial-nexus-opc-isa.md`](../tutorial-nexus-opc-isa.md)**.

## Messmetriken (`[NEXUS_METRICS]`)

Unverändert durch diese Welle; Opcodes leiten nur an bestehende CLI weiter. Optional weiterhin **`--metrics-json`** nach **`--`** bei **`map`**.

## CLI & Opcodes

| Kommando | Kurz |
|----------|------|
| `nexus-opc` / `python -m nexus.cli_opc` | Entry (Script in `pyproject.toml`) |
| `catalog [--json]` | Menschlesbarer oder JSON-Manifest |
| Global `--dry-run`, `--opc-log-append`, `--opc-roi-score`, `--opc-run-id` | Inspektion / Telemetrie |
| `stats <logfile.jsonl>` | Aggregation |

Vollständige **`argv`-Vorlagen:** `catalog --json` oder `catalog_manifest()` in **`nexus.cli_opc`**.

## Benchmarks & Reproduzierbarkeit

- **`bench`** / **`compare`** benötigen **`extras/nexus_benchmark.py`** oder **`NEXUS_BENCHMARK_SCRIPT`**.
- **`compare`** nutzt **`--roi-compare OLD NEW`**.

## Tests

- **`tests/test_cli_opc.py`** — Opcodes, `--dry-run`, Forwarding.

## Breaking changes

Keine: bestehende **`nexus`**-CLI bleibt unverändert; `nexus-opc` ist **zusätzlich**.

## Migration

- Agenten: zuerst **`nexus-opc locate -q "…"`** statt frei erfundener Flags.  
- Menschen: Tutorial **[`tutorial-nexus-opc-isa.md`](../tutorial-nexus-opc-isa.md)** lesen.

## Siehe auch

- **[`AGENTS.md`](../../AGENTS.md)** (Checkout-Abschnitt)  
- **`.cursor/skills/nexus-opc-isa/SKILL.md`** (Nexus-Checkout)  
- **`src/nexus/cursor_rules/nexus-over-grep.mdc`** (Bundle)
