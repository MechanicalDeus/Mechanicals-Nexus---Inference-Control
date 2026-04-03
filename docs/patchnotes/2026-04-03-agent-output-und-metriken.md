# Patchnote: Agent-Ausgabe, Informationsdichte und Messmetriken

## Meta

- **Datum:** 2026-04-03
- **Bezug Version:** `nexus-inference` **0.1.0b1** (`pyproject.toml` — keine Versionsbump in dieser Welle)
- **Scope:** CLI, Perspektiven, `context_metrics`, Benchmark-Dokumentation, ergänzende Projekt-Doku

## Zusammenfassung

Nexus trennt weiter **Auswahl** (Slice, `--max-symbols`) und **Darstellung**. Neu: die Perspektive **`agent_compact`** (strukturierte Felder statt narrativen `llm_brief`), steuerbar über **`--compact-fields`** (Presets `minimal` / `standard` / `full` oder explizite Feldliste). Der Einzeiler **`--agent-mode`** setzt eine opinionierte Kombination für Agenten (`agent_compact` + `minimal` + `--max-symbols 10`, überschreibbar). Die stderr-Zeile **`[NEXUS_METRICS]`** enthält dafür die Felder **`compact_fields`** und optional **`agent_mode`**, damit Läufe in Benchmarks und CI **filter- und diffbar** bleiben. Spezialqueries (`impact`, `why`, …) fallen weiterhin auf **`llm_brief`** zurück — keine zweite Heuristik.

## Messmetriken (`[NEXUS_METRICS]`)

Aktivierung unverändert: **`--metrics-json`** oder **`NEXUS_METRICS_JSON=1`** (stderr, stdout bleibt unverändert).

### Neue / erweiterte Keys

| Key | Wann gesetzt | Bedeutung |
|-----|----------------|-----------|
| **`compact_fields`** | Erfolgreiche Ausgabe mit Perspektive **`agent_compact`** (ohne Fallback auf `llm_brief`) | Sortierte Liste der **effektiv** ausgegebenen Felder, z. B. `["calls","writes"]` bei Preset `minimal` |
| **`agent_mode`** | `true`, wenn **`--agent-mode`** gesetzt war und die Metrik für diesen Lauf geschrieben wird | Kennzeichnet den **Shortcut-Pfad** in Benchmark-Auswertungen |

Bestehende Keys (`output_tokens_tiktoken`, `slice_fill_ratio`, `graph_*`, `context_handoff`, …) bleiben gültig; siehe **`docs/token-efficiency.md`** §2.5.

### Typische Größenordnung (Referenz, nicht Garantie)

Auf einer großen Codebasis (z. B. TTRPG Studio `app/`, 15 Symbole, gleiche Query): **`llm_brief`** oft **~8k–9k** tiktoken (cl100k_base); **`agent_compact`** **full** deutlich darunter; **`minimal`** nochmals **~50 %** unter **full** — rein **Darstellung**, gleicher Slice.

**README (Reproduzierbarkeit):** Im Root-**[`README.md`](../../README.md)** steht unter *Agent quick start* eine **Tabellen-Zusammenfassung** plus **SVG-Grafiken** (Ablauf **`--agent-mode`**, Balkendiagramm Token-Summen): [`docs/assets/readme-agent-mode-flow.svg`](../assets/readme-agent-mode-flow.svg), [`docs/assets/readme-benchmark-output-tokens.svg`](../assets/readme-benchmark-output-tokens.svg). Zahlen: Σ `output_tokens_tiktoken` über **vier** Queries auf TTRPG Studio `app/`, `llm_brief` vs. `agent_compact` full vs. **`--agent-mode`** — **N=1**, nicht als statistischer Beweis.

## CLI & Perspektiven

| Element | Beschreibung |
|---------|----------------|
| **`--perspective agent_compact`** | Strukturierte Zeilen pro Symbol (`calls`, `writes`, … je nach Feldern); **`SAME_NAME`**-Footer wie bei anderen Agent-Formaten |
| **`--compact-fields SPEC`** | Nur mit **`agent_compact`**: Presets **`minimal`** / **`standard`** / **`full`** oder Kommaliste aus `meta`, `calls`, `writes`, `called_by`, `reads`, `tags`, `next_open`. **Ohne Flag** = **`full`** (bisheriges Verhalten) |
| **`--agent-mode`** | Setzt `agent_compact` + `minimal` + `max_symbols=10`, sofern nicht explizit gesetzt. **Nicht** kombinierbar mit `--json`, `--names-only`, `--query-slice-json`, `--trace-mutation`, `--focus-graph`. Mit anderem `--perspective` nur wenn dieser `agent_compact` ist |
| **Fallback** | `agent_compact` + Spezialquery → **`llm_brief`** (wie `agent_symbol_lines`) |

Kontrakt-Tabelle: **`docs/cli-perspective.md`**, Moduldoc: **`src/nexus/output/perspective.py`**.

## Library / interne API

- **`nexus.output.llm_format`:** `agent_compact_lines(...)`, `parse_agent_compact_fields_arg`, `agent_compact_default_fields`, Konstanten `AGENT_COMPACT_FIELD_NAMES`, `AGENT_COMPACT_PRESETS`
- **`PerspectiveRequest`:** optionales Feld **`agent_compact_fields`** (`frozenset[str] | None`)
- **`build_context_metrics(..., compact_fields=..., agent_mode=...)`** in **`nexus.output.context_metrics`**

## Benchmarks & Reproduzierbarkeit

- **`extras/nexus_benchmark.py`:** weiterhin `python -m nexus <repo> -q … --metrics-json`; zusätzlich z. B.  
  `--nexus-arg --agent-mode`  
  oder  
  `--nexus-arg --perspective --nexus-arg agent_compact --nexus-arg --compact-fields --nexus-arg minimal`  
  (jeweils wiederholbar `--nexus-arg`).
- Für tiktoken-Zahlen: optional **`nexus-inference[metrics]`** bzw. **`NEXUS_TIKTOKEN_ENCODING`**.

## Tests

- **`tests/test_perspective_semantics.py`** — `agent_compact`, Presets, Fallback
- **`tests/test_cli_perspective.py`** — `--agent-mode`, Konflikte, Override `--max-symbols`
- **`tests/test_context_metrics.py`** — `compact_fields`, `agent_mode` in Metriken

## Breaking changes

**Keine.** Defaults ohne neue Flags entsprechen dem früheren Verhalten (`llm_brief` / `agent_compact` ohne `--compact-fields` = full).

## Migration

- Skripte, die nur **`nexus -q`** nutzen: unverändert.
- Agenten-Pipelines mit Token-Limit: schrittweise **`--agent-mode`** oder **`--perspective agent_compact --compact-fields minimal`** testen; Metrik **`compact_fields`** in Logs persistieren für Vergleiche.

## Siehe auch

- [`README.md`](../../README.md) — Agent Quick Start, **gemessene** Token-Tabelle (TTRPG-Beispiel)
- [`docs/token-efficiency.md`](../token-efficiency.md) — Messung, `--metrics-json`, Benchmark-Hinweis
- [`docs/cli-perspective.md`](../cli-perspective.md) — Perspektiven-Tabelle
- [`AGENTS.md`](../../AGENTS.md) — Agenten-Kurzreferenz, `--agent-mode`
- [`extras/nexus_benchmark.py`](../../extras/nexus_benchmark.py)
