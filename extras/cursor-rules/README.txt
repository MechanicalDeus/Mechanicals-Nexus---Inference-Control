Nexus als Agent-Tool (Token-effizient statt breitem Grep)

Die Cursor-Regel (.mdc) liegt jetzt IM PAKET und wird mit nexus-inference ausgeliefert:
  Python-Modul: nexus.cursor_rules
  Quelldatei im Klon: src/nexus/cursor_rules/nexus-over-grep.mdc

INSTALLATION IN DEIN PYTHON-PROJEKT (Cursor erkennt .cursor/rules/*.mdc):
  cd <dein-projekt-root>
  nexus-cursor-rules install
  # oder: python -m nexus.cursor_rules install
  # Überschreiben: nexus-cursor-rules install --force
  # Nur Pfad anzeigen: nexus-cursor-rules --path

Agenten-Doku (Nachimport, Kommandos):
  AGENTS.md  (Repo-Root des Nexus-Klons)

Sicherheit (Inferenz-Exports nicht committen):
  SECURITY.md

README (Überblick):
  README.md

---

1) Global auf einem Rechner (optional)
   - Regel-Datei nach %USERPROFILE%\.cursor\rules\ kopieren (z. B. aus nexus-cursor-rules --path)
   - Oder Inhalt der .mdc in Cursor Settings > Rules > User Rules
   - Checkout-Pfad und pipx-Pfad in Doku anpassen

2) Nur pro Python-Projekt (empfohlen)
   - nexus-cursor-rules install  im Projektroot

3) CLI überall
   pip install nexus-inference
   pipx install nexus-inference
   Danach: nexus . -q "mutation" --max-symbols 20
   Windows PowerShell: python -m nexus . "-q" "mutation" "--max-symbols" "20"

4) Optional
   NEXUS_HOME = Pfad zum Nexus-Checkout
   PYTHONPATH=%NEXUS_HOME%\src

Staffelung: nexus-grep / nexus --names-only -> read_file (Slice) -> nexus -q -> --json nur bei Bedarf.
