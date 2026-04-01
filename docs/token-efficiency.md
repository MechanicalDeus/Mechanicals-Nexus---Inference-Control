# Effizienz & Messlogik — warum sich der Aufwand amortisiert

*Kurz auf Englisch:* One **local** full-repo scan builds a graph in memory. After that, every agent turn can use **bounded** Nexus output (`--names-only`, `nexus-grep`, small `--max-symbols`) instead of shipping huge grep dumps or whole files into the model. Below: **reproducible numbers** from this repository plus **reference scans** from larger legacy codebases.

---

## 1. Die ökonomische Kernidee

| Phase | Wo kosten entstehen | Nexus-Verhalten |
|--------|---------------------|-----------------|
| **Index / Scan** | CPU-Zeit auf deiner Maschine, **keine** LLM-Tokens | `attach()` / `nexus` / `nexus-grep` lesen den Baum **einmal** (pro Prozess) und halten den Graphen bereit. |
| **Jede Agenten-Runde** | **Kontext = Tokens** (alles, was ins Prompt-Fenster fließt) | Du steuerst die Menge mit **`--max-symbols`**, **`--names-only`** und **`nexus-grep`** (Slice → dann erst gezielt Dateien lesen). |

**Gewinn in einem Satz:** Das „Einlesen“ eines großen Repos passiert **lokal und einmal pro Lauf**; der **teure Teil** ist wiederholtes **Kontext-Füttern** des Modells — und genau dort hält Nexus die Ausgabe **deckelbar**, statt mit jedem Schritt halbe Trees als Text zu schicken.

---

## 2. Reproduzierbare Messung: Repository **Nexus** (dieser Code)

Umgebung: PowerShell, im Checkout-Root `F:\Nexus` (bzw. dein Pfad), `PYTHONPATH` auf `…\src` oder installiertes `nexus`.

### 2.1 Graph-Größe (ein Scan, typische Kopfzeile)

```bash
python -m nexus . -q "mutation" --max-symbols 10
```

Auszug aus der Ausgabe (nur Metadaten):

```text
REPO: F:\Nexus
QUERY (filtered): mutation
Files: 34  Symbols: 162  Edges: 191
Showing 10 symbol(s).
```

Das sind die **Dimensionen des einmal aufgebauten Indexes** (ungefähr: Dutzende Dateien, ~hundert Symbole, ~hundert Kanten) — **nicht** die Größe des LLM-Prompts.

### 2.2 Kontext sparen: `--names-only` (statt breitem Textgrep)

Derselbe Filter, nur qualifizierte Namen (Ausgabe gekürzt dargestellt):

```bash
python -m nexus . -q "mutation" --max-symbols 10 --names-only
```

**Gemessen (Stand der Auswertung):** etwa **11 Zeilen**, **~480 Zeichen** Gesamtausgabe — ein brauchbarer **Orientierungs-Schritt** fürs Modell.

### 2.3 Naiver Gegenpol: „alles, was nach Definition aussieht“

Als **Proxy** für „Agent schmeißt breiten Grep ins Prompt“: alle Zeilen mit Wort `def` unter `src/` und `tests/` (PowerShell `Select-String`).

**Gemessen:** **208 Trefferzeilen**, zusammen **~10.200 Zeichen** reiner Zeilentext (ohne Pfade/Metadaten).

**Interpretation (vorsichtig):** Das ist **nicht** semantisch dasselbe wie `mutation` — aber es zeigt die **Größenordnung**: breite Text-Trefferlisten skalieren mit **Repo-Wachstum**; **`--names-only` mit festem `--max-symbols`** bleibt **konstant klein**.

### 2.4 Voller Kurzbrief vs. Namensliste

| Modus | Größenordnung (Nexus-Repo, `mutation`, 10 Symbole) |
|--------|------------------------------------------------------|
| `--names-only` | ~0,5 KB, ~11 Zeilen |
| Voller Text-Brief (Felder wie reads, calls, chains) | ~12 KB, ~130 Zeilen |

**Konsequenz:** Erst **dünn** orientieren, **dann** gezielt `read_file` auf 1–3 Pfade; den **vollen Brief** nur holen, wenn die Frage es braucht — sonst zahlt man pro Symbol viele strukturierte Tokens.

---

## 3. Referenz: größere produktive Trees (Smoke-/Explorationsläufe)

In **zwei** größeren Python-Projekten (u. a. **Aether VPN**-Backend und **TTRPG Studio**-Bereich) wurden Nexus-Läufe zur **Struktur- und Mutations-Orientierung** genutzt — **ohne** die rohen Graph-Exports öffentlich zu teilen (siehe `SECURITY.md`).

### 3.1 Typische Index-Größe (Aether VPN, repräsentativer Snapshot)

Aus einer internen Auswertung (Legacy-FastAPI-/Service-Baum):

| Metrik | Größenordnung |
|--------|----------------|
| Erfasste `.py`-Dateien | **82** |
| Symbole | **496** |
| Kanten im Graph | **392** |

**Botschaft:** Der **einmalige** Scan erzeugt einen Graphen in dieser Größenordnung — das ist **Arbeit für die CPU**, nicht für das Token-Budget. Was ins LLM geht, entscheidest du mit **Briefing-Länge** und **names-only**.

### 3.2 TTRPG Studio

Hier liegen **keine** veröffentlichten Roh-JSONs vor; fachlich gilt dieselbe **Staffelung**: bei **mehreren hundert Symbolen** explodieren breite Grep- oder Volltext-Kontexte schneller als **gebündelte** Nexus-Ausgaben mit hartem `--max-symbols`.

---

## 4. Log-Beispiel: was der Agent „sieht“

**A — breit (Stil: viele Trefferzeilen):**

```text
# Stil: 208 Zeilen mit "def ..." — nur Ausschnitt
def main(...):
def attach(...):
def scan(...):
def _scan_impl(...):
# ... hunderte Zeilen weiter, ohne Kanten, ohne Confidence
```

**B — Nexus, Orientierung (Stil: feste Kappe):**

```text
REPO: …
Files: 34  Symbols: 162  Edges: 191
src.nexus.cli_grep.main
src.nexus.scanner._scan_impl
src.nexus.cli.main
# … bis max. 10 Namen
```

**C — Nexus, fokussierter Brief (nur wenn nötig):**  
voller Block mit reads/calls/mutation_chain — **teurer**, aber immer noch **eine** zusammenhängende Struktur statt zufälliger Grep-Schnipsel.

---

## 5. Amortisation (grobe Denkrechnung)

- **Einmalig:** Scan-Zeit \(T_{\text{scan}}\) (Sekunden bis wenige Minuten, je nach Rechner und Repo). **0 LLM-Tokens.**
- **Pro Agenten-Runde:** Wenn du statt ~10k Zeichen „Grep-Wand“ nur ~0,5k Zeichen Namensliste schickst, sparst du grob **~9,5k Zeichen** pro Runde — in Tokens je nach Modell/Zählung oft **einige tausend Tokens** weniger **pro Schleife**.
- Nach **wenigen** solchen Runden hat sich der Scan **rechnerisch** „verzinst“, ohne dass du sensible Graph-Exports committen musst.

Das ist **kein** Garantieversprechen für jede Fragestellung — schlechte Queries können Nexus genauso „leer“ oder „zu fett“ machen wie Grep. Die **Decision-Engine** in der Cursor-Regel (`nexus-over-grep.mdc`) genau dazu: erst dünn, dann lesen, dann eskalieren.

---

## 6. Selbst nachmessen

```bash
# Graph-Kopf + bounded brief
python -m nexus <pfad-zum-repo> -q "mutation" --max-symbols 15

# Minimal-Tokens-Orientierung
python -m nexus <pfad-zum-repo> -q "mutation" --names-only --max-symbols 25

# Slice → dann Grep nur in wenigen Dateien
nexus-grep <pfad-zum-repo> -q "DeinEindeutigerSymbolname" --max-symbols 20
```

Wenn du **eigene** Before/After-Logs für Blog oder README brauchst: einmal **Zeichenzahl** der Prompts mit/ohne Nexus (gleiche Aufgabe) vergleichen — das ist die ehrlichste „Messung“ für dein Setup.
