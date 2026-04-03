# Patchnote: Titel (Kurzbeschreibung)

> **Vorlage** — Kopieren, Datum/Slug anpassen, unter `docs/patchnotes/YYYY-MM-DD-slug.md` speichern und in [`README.md`](README.md) indexieren.

## Meta

- **Datum:** YYYY-MM-DD
- **Bezug Version:** z. B. `nexus-inference` 0.1.0b1 (siehe `pyproject.toml`)
- **Scope:** CLI / Library / UI / Benchmark / Docs

## Zusammenfassung

2–5 Sätze: Was ändert sich für Nutzer:innen und Agenten?

## Messmetriken (`[NEXUS_METRICS]`)

Neue oder geänderte Keys, Semantik, wann sie gesetzt werden.

| Key | Bedeutung |
|-----|-----------|
| … | … |

## CLI & Perspektiven

Neue Flags, `PerspectiveKind`-Werte, Defaults, Konfliktregeln.

## Library / interne API

Relevante Funktionen/Module (Import-Pfade), falls öffentlich relevant.

## Benchmarks & Reproduzierbarkeit

Skripte (z. B. `extras/…`), empfohlene Aufrufe, Umgebungsvariablen.

## Tests

Wichtige neue/angepasste Tests (`tests/…`).

## Breaking changes

Explizit `Keine` oder Liste mit Ersatz.

## Migration

Konkrete Ersetzungen für Skripte und Rules.

## Siehe auch

- Verknüpfte Docs (`docs/…`, `AGENTS.md`).
