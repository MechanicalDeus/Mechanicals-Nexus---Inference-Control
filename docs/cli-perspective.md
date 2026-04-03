# CLI: canonical perspectives (`nexus --perspective`)

The `nexus` CLI can speak the same **perspective contract** as the library and the Inference Console: `PerspectiveKind` string values (stable API semantics — see [`src/nexus/output/perspective.py`](../src/nexus/output/perspective.py)).

**Why this exists:** One stable vocabulary for “what shape of answer do I want?” — whether you call Nexus from a **script**, an **agent tool**, or the **Inference Console**. The default `nexus -q …` path still works; `--perspective` is the **explicit** switch when you want a named projection only.

**Canonical path:** `--perspective NAME` plus the flags below. **Legacy shortcuts** (`--names-only`, `--query-slice-json`, …) are unchanged and **must not** be combined with `--perspective`.

**`--agent-mode`:** opinionated shortcut for agents — implies `agent_compact` + `minimal` compact fields + `--max-symbols 10` unless overridden; incompatible with `--json`, `--names-only`, etc. See `nexus --help`.

**Debug (stderr only, stdout unchanged):** `--debug-perspective` prints one JSON object per `render_perspective` call, prefixed with `[NEXUS_PERSPECTIVE]`, containing `payload_kind`, `advice`, `error`, and optional `provenance` (`backend`, `driver`, `center_qualified_name`).

## Requirements and typical payload

| `PerspectiveKind` | Non-empty `-q` | `--center-kind` + `--center-ref` | `--mutation-key` | Typical `payload_kind` | CLI stdout |
|-------------------|----------------|-----------------------------------|------------------|-------------------------|------------|
| `heuristic_slice` | yes | — | — | `symbol_list` | one `qualified_name` per line |
| `query_slice_json` | yes | — | — | `json` | bounded slice JSON |
| `llm_brief` | optional | — | — | `text` | balanced brief |
| `agent_names` | yes | — | — | `text` or `error` | names lines, or stderr error on special query |
| `agent_symbol_lines` | yes | — | — | `text`, `none`+advice, or fallback | lines; special query → same as `llm_brief` |
| `agent_compact` | yes | — | — | `text`, `none`+advice, or fallback | structured fields per symbol; special query → same as `llm_brief`. Optional **`--compact-fields`** (`minimal` / `standard` / `full` or comma-list: `meta,calls,writes,called_by,reads,tags,next_open`; default `full` = previous behavior) |
| `trust_detail` | no | yes (`symbol_id` or `symbol_qualified_name`) | — | `text` | trust / inspector text |
| `focus_graph` | no | yes | — | `graph_json` | one-hop layout JSON |
| `mutation_trace` | no | — | yes | `json` | `trace_mutation` buckets |

**Notes**

- `heuristic_slice` and `llm_brief` can disagree for the same `-q` (special query modes only affect the brief). That is intentional; see the module docstring in `perspective.py`. Regression: **`tests/test_perspective_semantics.py`** asserts this separation (e.g. `impact` / `why` vs. heuristic slice).
- `agent_symbol_lines` and `agent_compact` may return `advice: fallback_to_llm_brief` with no primary payload; the CLI then renders `llm_brief` (two debug lines if `--debug-perspective`).

## Examples

```bash
nexus . --perspective heuristic_slice -q "flow" --max-symbols 12
nexus . --perspective trust_detail --center-kind symbol_qualified_name --center-ref "mymod.foo"
nexus . --perspective mutation_trace --mutation-key "hp"
nexus . -q "mutation" --debug-perspective
```
