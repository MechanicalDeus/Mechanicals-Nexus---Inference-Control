# AGENTS.md — Nexus für den Cursor-Agenten

Diese Datei ist die **Referenz**, wenn du in **beliebigen Python-Repos** arbeitest und **Nexus** (strukturelle Karte statt blindem Grep) nutzen oder einrichten sollst.

## Andere Repos: Nachimport (einmalig pro Projekt)

1. **Nexus installieren** (global nutzbar):  
   `pipx install -e <pfad-zum-nexus-klon>` **oder** `pip install -e <pfad-zum-nexus-klon>`  
   Ohne Install: `PYTHONPATH=<nexus-klon>/src` und `python -m nexus …` / `python -m nexus.cli_grep …`.
2. **Cursor-Regel installieren** (liegt **im Paket** `nexus-inference`, Modul `nexus.cursor_rules`):  
   Im **Ziel-Repo-Root**: **`nexus-cursor-rules install`** — legt `nexus-over-grep.mdc` nach **`<dein-repo>/.cursor/rules/`** (Cursor lädt `.mdc` von dort).  
   Alternativen: **`python -m nexus.cursor_rules install`**, Pfad nur anzeigen mit **`nexus-cursor-rules --path`**, bestehende Datei ersetzen mit **`install --force`**.  
   Beim Arbeiten am Nexus-Klon: Quelle **`src/nexus/cursor_rules/nexus-over-grep.mdc`**; Hinweise in **`extras/cursor-rules/README.txt`**.
3. **Optional global:** dieselbe `.mdc` nach `%USERPROFILE%\.cursor\rules\` kopieren oder Inhalt in Cursor **User Rules**.
4. **Diese `AGENTS.md`** als Doku bookmarken oder im Team verlinken — sie ergänzt die `.mdc` um Kommandos; zu Inference-Exports **`SECURITY.md`**.

## Design: Token-Effizienz und Grep

**Ziel:** Agenten sollen in großen Codebases **nicht** zuerst halbe Repos per breitem `rg` in den Kontext ziehen. **Nexus** strukturiert die Suche; **`nexus-grep`** ist die **Standard-Stufe** (dünne Ausgabe). **Grep** bleibt sinnvoll **nach** der Einengung oder für Nicht-Python — siehe Decision Layer und **Decision Engine** (Default: enge `nexus-grep` → Slice lesen → STOP) in der `.mdc`. **`nexus --json`** und lange **`nexus -q`**-Briefings nur bei Bedarf (Export, Ketten, Impact).

## 1. Standardverhalten (wenn Nexus schon geht)

Im **Ziel-Repo-Root** (oder `src/<paket>`):

```bash
nexus . -q "mutation" --max-symbols 25
nexus . -q "full mutation chain" --max-symbols 40
nexus . -q "impact Klassenname"
nexus . -q "state" --names-only --max-symbols 50
nexus-grep . -q "mutation" --max-symbols 25
nexus . --json > nexus-inference.json
```

**Agent-Reihenfolge bei unbekannter Codebasis:** zuerst `nexus … --names-only` oder `nexus-grep …` (Struktur → gezielte Namenssuche in wenigen `.py`), dann relevante Dateien öffnen; breites `grep`/`rg` nicht als ersten Schritt. Spezialqueries (`impact`, `why`, …) weiter mit `nexus -q`, nicht mit `nexus-grep`.

**Windows PowerShell** ohne global installiertes `nexus`:

```powershell
$env:PYTHONPATH = "F:\Nexus\src"   # Pfad zum Nexus-Checkout anpassen
python -m nexus . "-q" "mutation" "--max-symbols" "20"
python -m nexus.cli_grep . "-q" "mutation" "--max-symbols" "25"
```

## 2. Checkliste: Nexus in einem **neuen** Repo „fertig machen“

1. **Prüfen:** Läuft `nexus` bzw. `python -m nexus --help` (mit gesetztem `PYTHONPATH` auf Nexus-`src`)?
2. **Falls nein — einmalig installieren** (empfohlen, dann in jedem Repo nutzbar):
   - `pipx install -e F:\Nexus` **oder** `pip install -e F:\Nexus` (gilt für alle Venvs, die der Nutzer aktiv hat)
   - Checkout-Pfad `F:\Nexus` durch den **tatsächlichen** Nexus-Klon ersetzen.
3. **Regel im Ziel-Repo:**  
   **`nexus-cursor-rules install`** im Ziel-Repo-Root ausführen (siehe Abschnitt „Andere Repos“ oben).
4. **Große / langsame Scans:** lieber `-q` + `--max-symbols` oder `nexus-grep` als sofort `--json` auf dem ganzen Monorepo.

## 3. Umgebungsvariable (optional, für alle Rechner)

Nutzer kann setzen:

- `NEXUS_HOME` = Pfad zum Nexus-Checkout (Ordner mit `pyproject.toml`).

Dann Fallback z. B.:

```powershell
$env:PYTHONPATH = "$env:NEXUS_HOME\src"
python -m nexus . "-q" "flow" "--names-only" "--max-symbols" "40"
```

## 4. Wann **nicht** Nexus

- Kein Python, reine String-Suche in Config/Logs → `grep` / Suche im Editor ist ok.
- Sehr kleine Datei, eine bekannte Stelle → direkt Datei öffnen.

## 5. Wo liegt die Cursor-Vorlage?

- **Im installierten Paket:** `nexus.cursor_rules` → Installation mit **`nexus-cursor-rules install`** im Ziel-Repo-Root.  
- **Im Nexus-Klon (Quelle):** **`src/nexus/cursor_rules/nexus-over-grep.mdc`** — zusätzlich **`extras/cursor-rules/README.txt`**.
- **Global (einzelner Rechner):**  
  `%USERPROFILE%\.cursor\rules\nexus-python-context.mdc`  
  — kann denselben Inhalt referenzieren; Pfade (`F:\Nexus` etc.) anpassen.

## 6. Inferenz-Karten: lokal halten, nicht committen

**Wichtig:** Ausgaben von `nexus … --json` oder gespeicherte Graph-Exports sind **keine neutralen Logs**. Sie enthalten typischerweise **Symbollisten, Aufrufbeziehungen, Pfade und heuristische Verhaltenshinweise** eures gescannten Codes — vergleichbar mit **Quelltext + Architekturindex**. Das kann **vertraulich und sicherheitsrelevant** sein (interne Struktur, sensible Flüsse).

- **Nicht** ins Git legen, **nicht** ungefiltert in öffentliche Issues/PRs posten.  
- Im Nexus-Repo helfen **`.gitignore`-Muster** und **`SECURITY.md`**; dasselbe Muster solltet ihr im **Ziel-Repo** übernehmen, sobald ihr Exporte erzeugt.  
- Für Hilfe von außen: nur **reduzierte Auszüge** oder manuell geschwärzte Kurzbriefings — **keine** vollen Roh-Graph-Dateien.

Eigene Projekte lokal z. B.: `nexus <pfad> --json > ./exports/mein-graph.json` (Ordner `exports/` bzw. genutzte Pfade **ignorieren**).
