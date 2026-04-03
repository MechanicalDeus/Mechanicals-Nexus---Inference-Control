# Proof of concept — Nexus

## Goal

Show how **structured inference** can cut LLM (or human) context cost compared to **flat text search** across a whole Python tree — without dumping a full graph into the prompt first.

## Scenario

**Question:** “Where does state or tags get touched along the scan path?”

### Traditional approach

- Run `grep` / `rg` over the repo for broad terms (`write`, `tag`, `mutat`…).  
- Open many files from noisy hit lists.  
- Manually connect call chains.

### Nexus approach

**Step 1 — thin slice (token-cheap):**

```bash
nexus-grep . -q "mutation" --max-symbols 10
```

Nexus first restricts attention to **relevant symbols and files**, then searches text only inside that slice (see `nexus-grep` design).

**Step 2 — structured chain (still bounded):**

```bash
nexus . -q "mutation" --max-symbols 5
```

For **minimal prompts** with **confidence/tags** but no full symbol blocks:

```bash
nexus . -q "mutation" --names-only --annotate --max-symbols 10
```

Example **mutation chain** line you may see when scanning this repository (format is illustrative; your graph will differ):

```text
src.nexus.cli.main → src.nexus.scanner.attach → src.nexus.scanner.scan → src.nexus.scanner._scan_impl → src.nexus.scanner._tag_symbol
```

That is a **ready-made path** from CLI entry into tagging / semantic annotation — not a flat list of every match in the tree.

## Outcome (qualitative)

- Fewer files need to be opened to answer “where does this kind of work happen?”  
- Chains and confidence cues reduce **guesswork** vs. raw grep.  
- Full `nexus . --json` remains optional — use **only** when you need a machine-export and can keep it **private** (see `SECURITY.md`).

## Mental model

| Without Nexus | With Nexus |
|---------------|------------|
| Search → read → guess | Narrow → target → read |

## Security reminder

Any **saved** inference map (`--json`, exports) can encode **structure and paths of your codebase**. Do not commit or publish those files; see root `SECURITY.md` and `.gitignore`.

## Deeper dive: measured efficiency

See [`token-efficiency.md`](token-efficiency.md) for **reproducible character counts**, graph-size metrics, **reference snapshots** (scoped Python trees — not whole-product disk totals), and an **amortization** section (scan once vs. tokens every turn). **Messlatte** for measured **disk / `.py`** across example checkouts: [`case-study-cross-repo-orientation.md` § Messlatte](case-study-cross-repo-orientation.md#messlatte-measured-sizes-2026-04-03).
