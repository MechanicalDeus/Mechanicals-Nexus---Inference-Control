# Security Notice — Nexus Inference Maps

## Sensitive data warning

Nexus generates **inference maps** (e.g. JSON graph exports, saved briefings) that can contain:

- Structural relationships between code symbols  
- Call graphs and mutation chains  
- Heuristic behavioural / state-touching analysis  
- File paths and qualified names across your tree  

These artefacts may reveal:

- Internal architecture and module layout  
- Sensitive control flows and integration points  
- Security-relevant mutation or trust boundaries  

Treat them as **highly sensitive**: comparable to sharing **source plus an architectural index** of the scanned codebase.

## Do not commit generated maps

Generated inference data must **not** be committed to version control or pasted into public issues/PRs unless you have explicitly cleared that with your security policy.

## Recommended practice

- Generate maps **locally** only.  
- Keep exports **out of the repo** (see root `.gitignore` patterns).  
- Share **redacted summaries** or hand-picked snippets if you need help — not raw full graphs.  
- For CI: avoid archiving full `--json` exports as public artefacts unless the scanned tree is non-sensitive.

## Reporting security issues in Nexus itself

If you believe you have found a security vulnerability in **this tool** (the Nexus package), please open a **private** advisory via GitHub Security Advisories for the repository, or contact the maintainers through a non-public channel they document in the repo.

---

**In one line:** Inference maps are a **semantic index of the code you scanned** — handle them like confidential engineering material.
