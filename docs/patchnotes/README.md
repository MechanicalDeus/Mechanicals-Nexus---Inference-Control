# Patchnotes (Nexus)

**Patchnotes** sind kurze, versionierbare **Berichte** zu größeren Änderungswellen: neue CLI-Flags, Metrikfelder, Perspektiven, Benchmarks — mit **Messbarkeit** und **Migrationshinweisen**. Sie ergänzen die **PyPI-Version** in `pyproject.toml` und können **zwischen Releases** erscheinen.

## Wann eine Patchnote schreiben?

- Neue oder geänderte **Telemetrie** (`--metrics-json`, Metrik-Keys).
- Neue **Perspektiven** / **Ausgabeformate** mit Nutzer-Kontrakt.
- **Benchmark-** oder **Policy-relevante** CLI-Änderungen.
- Kein Ersatz für jede Kleinigkeit: triviale Fixes → Commit/PR reicht.

## Dateiname

```
YYYY-MM-DD-kurz-slug.md
```

Beispiel: `2026-04-03-agent-output-und-metriken.md`

## Aufbau

Vorlage: **[`TEMPLATE.md`](TEMPLATE.md)** — Abschnitte: Meta, Zusammenfassung, Messmetriken, CLI/API, Tests/Docs, Breaking, Migration, Siehe auch.

## Index (neueste oben)

| Datum | Datei | Thema |
|-------|--------|--------|
| 2026-04-03 | [2026-04-03-agent-output-und-metriken.md](2026-04-03-agent-output-und-metriken.md) | `agent_compact`, `--compact-fields`, `--agent-mode`, Metrikfelder, Benchmark |
