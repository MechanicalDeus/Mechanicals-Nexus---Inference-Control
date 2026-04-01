# Nexus — Abschlussbericht und Konzept-Pitch

Dieses Dokument fasst **Zweck, Nutzen und Positionierung** von Nexus zusammen — als **Abschlussbericht** für Überblick und Entscheidungen und als **Pitch** für Teams, die LLM-Agenten oder strukturierte Code-Analyse einsetzen.

---

## Pitch (60 Sekunden)

**Problem:** Große Python-Codebasen mit **breitem Grep oder `rg`** in den Kontext eines LLM zu schleifen, liefert viele Zeilen, wenig Struktur und frisst **Token** — ohne garantiert die richtigen Dateien zu treffen.

**Lösung:** **Nexus** baut aus dem Quellcode eine **Inferenzkarte**: Symbole (Funktionen, Klassen, Methoden), **Aufrufkanten**, heuristische **Lese-/Schreibspuren** und **Mutationspfade**, plus **Confidence** und **Schichten** (z. B. core vs. support). Statt Roh-Trefferlisten bekommen Agenten und Menschen **kompakte, sortierte Briefings** oder **gezielte Namenslisten**.

**Staffelung:** Zuerst **`nexus-grep`** oder **`nexus --names-only`** (dünne Ausgabe), dann **gezielt Dateien lesen**, **`nexus -q`** mit kleinem `--max-symbols` für Ketten/Impact, **`--json`** nur wenn der volle Graph nötig ist.

**Ein Satz:** Nexus ist **Grep mit Vorwissen über Struktur** — gebaut, um **LLM-Kontext schlank und relevant** zu halten.

---

## Abschlussbericht: Was Nexus leistet

### Zielbild

Nexus adressiert eine konkrete Lücke im Agenten-Workflow: **Orientierung und Wirkungsanalyse** in Python-Repos ohne blindes Durchsuchen halber Trees. Die Ausgabe ist für **Maschinenlesbarkeit und Token-Budget** optimiert (`AGENTS.md`, gebündelte Cursor-Regel in `nexus.cursor_rules` / `nexus-cursor-rules install`).

### Kernkonzept

1. **Statische Analyse:** AST-basiertes Einlesen der `.py`-Dateien unter einem Wurzelpfad.
2. **Graph im Speicher:** `InferenceGraph` mit `SymbolRecord`-Knoten und `Edge`-Kanten (v. a. `calls`).
3. **Heuristiken:** Direkte und indirekte sowie **transitive** Schreib-Spuren über Aufrufketten (Fixpunkt), **semantische Tags** (z. B. `mutator`, `delegate`, `ambiguous-call`), **Confidence** [0, 1], **Layer** nach Pfad/Name.
4. **Abfrage-Schicht:** Freitext `-q` mit Keyword-Filtern für Mutation vs. Flow; **Spezialmodi** (z. B. Impact, Mutation Chain, Why) für tiefere, aber weiterhin formatierte Antworten.
5. **Zweites Werkzeug `nexus-grep`:** Erst Nexus-Slice (relevante Symbole/Dateien), dann **Grep nur in diesem Slice** — nicht im ganzen Repo.

### Technische Kurzfassung (Pipeline)

- **Einstieg:** `attach(path)` bzw. `scan(path)` → vollständiger Graph für gewählte Optionen (`include_tests`, `transitive_depth`, …).
- **CLI `nexus`:** JSON-Export oder **LLM-Brief** (`to_llm_brief`), optional **`--names-only`** für minimale Tokenlast.
- **CLI `nexus-grep`:** Keine Spezialqueries; Fokus auf **enge Symbolmenge → Suche in wenigen Dateien**.

### Messbare Effizienz

Kurz erklärt mit Zahlen (reproduzierbar im Nexus-Repo, plus Referenzsnapshots größerer Projekte): **`docs/token-efficiency.md`** — Fokus: **einmaliger lokaler Scan** vs. **deckelbare Prompt-Größe** pro Agenten-Runde.

### Für wen?

- **LLM-gestützte Entwicklung** (Cursor, Codex, eigene Pipelines), die **Kontextbudget** ernst nimmt.
- **Reviews und Refactors**, bei denen **„wer ruft wen“** und **„wo wird Zustand berührt“** schnell sichtbar sein soll.
- **Onboarding** in fremde Python-Projekte ohne sofortigen Vollgraph-Export.

### Was Nexus bewusst nicht ist

- Kein Ersatz für **Linter**, **Typechecker** oder **Profiler**.
- Keine **Laufzeit-Garantien** über tatsächliches Verhalten — Inferenz und Heuristiken können **falsch oder unvollständig** sein; **Confidence** und Tags machen Unsicherheit sichtbar.
- **`follow_imports`** für externe Auflösung ist im Modell vorgesehen, die Fokus-Story bleibt **intra-repo** und **statisch**.

---

## Nutzenargumente (für Entscheider:innen)

| Aspekt | Nutzen |
|--------|--------|
| **Kosten** | Weniger irrelevante Tokens → geringere Modellkosten und schnellere Antworten. |
| **Qualität** | Strukturierte Karten reduzieren Halluzinationen über „irgendwo im Repo“. |
| **Workflow** | Klare Staffelung: dünn → lesen → bei Bedarf tief — passt zu menschlicher und agentischer Arbeit. |
| **Integration** | Bibliothek (`attach`) + CLI + kopierbare Cursor-Regel; kein zwingender Cloud-Dienst. |

---

## Nächste Schritte im Projekt

1. **Installation:** `pipx install -e <nexus-checkout>` oder `PYTHONPATH=<checkout>/src` und `python -m nexus …` (Details: `README.md`, `AGENTS.md`).
2. **Regel im Ziel-Repo:** `nexus-cursor-rules install` im Projektroot (Regel aus dem Paket nach `.cursor/rules/`).
3. **Erste Nutzung:** `nexus-grep . -q "<konkrete Code-Begriffe>" --max-symbols 20` im Ziel-Projekt, dann gezielt Dateien öffnen.

---

## Fazit

Nexus ist ein **fokussiertes Werkzeug** für **strukturierte Python-Karten** und **tokenbewusste** Agenten-Workflows. Der Pitch: **weniger Rauschen, mehr Kante** — zuerst die Karte, dann der Text, nicht umgekehrt.

*Stand: Abschlussbericht / Pitch-Dokument im Nexus-Repository.*
