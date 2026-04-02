Nexus as an agent tool (token-efficient instead of broad grep)

The Cursor rule (.mdc) ships INSIDE THE PACKAGE with nexus-inference:
  Python module: nexus.cursor_rules
  Source in a clone: src/nexus/cursor_rules/nexus-over-grep.mdc

INSTALL INTO YOUR PYTHON PROJECT (Cursor loads .cursor/rules/*.mdc):
  cd <your-project-root>
  nexus-cursor-rules install
  # or: python -m nexus.cursor_rules install
  # overwrite: nexus-cursor-rules install --force
  # print bundled path: nexus-cursor-rules --path

Agent docs (setup, commands):
  AGENTS.md  (repo root of the Nexus clone)

Security (do not commit inference exports):
  SECURITY.md

Overview:
  README.md

---

1) Global on one machine (optional)
   - Copy the rule file to %USERPROFILE%\.cursor\rules\ (e.g. from nexus-cursor-rules --path)
   - Or paste .mdc content into Cursor Settings > Rules > User Rules
   - Adjust checkout path and pipx paths in docs as needed

2) Per Python project (recommended)
   - nexus-cursor-rules install  at project root

3) CLI everywhere
   pip install nexus-inference
   pipx install nexus-inference
   (pip package name nexus-inference; shell commands are nexus, nexus-grep, nexus-policy, nexus-cursor-rules, nexus-console)
   Then: nexus . -q "mutation" --max-symbols 20
   Windows PowerShell: python -m nexus . "-q" "mutation" "--max-symbols" "20"

4) Optional
   NEXUS_HOME = path to Nexus checkout
   PYTHONPATH=%NEXUS_HOME%\src

Tiering: nexus-grep / nexus --names-only -> read_file (slice) -> nexus -q -> --json only when needed.
