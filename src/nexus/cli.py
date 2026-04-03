from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nexus import attach
from nexus.control_header import (
    collect_control_config,
    control_header_enabled,
    emit_control_header,
)
from nexus import __version__ as nexus_version
from nexus.output.context_metrics import (
    build_context_metrics,
    emit_context_metrics_line,
    metrics_json_enabled,
)
from nexus.output.llm_format import (
    DEFAULT_QUERY_MAX_SYMBOLS,
    agent_compact_default_fields,
    parse_agent_compact_fields_arg,
)

# --agent-mode: opinionierter Agenten-Einstieg (kompakt, kleiner Slice-Cap).
AGENT_MODE_DEFAULT_MAX_SYMBOLS = 10
from nexus.output.perspective import (
    CenterKind,
    PerspectiveAdvice,
    PerspectiveKind,
    PerspectivePayloadKind,
    PerspectiveRequest,
    PerspectiveResult,
    render_perspective,
)


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def _debug_perspective_stderr(pr: PerspectiveResult, enabled: bool) -> None:
    """Eine Zeile stderr, stdout bleibt unverändert (pipe-tauglich)."""
    if not enabled:
        return
    row: dict[str, object] = {
        "payload_kind": pr.payload_kind.value,
        "advice": pr.advice.value,
        "error": pr.error,
    }
    if pr.provenance is not None:
        row["provenance"] = {
            "backend": pr.provenance.backend,
            "driver": pr.provenance.driver.value,
            "center_qualified_name": pr.provenance.center_qualified_name,
        }
    sys.stderr.write("[NEXUS_PERSPECTIVE] " + json.dumps(row, ensure_ascii=False) + "\n")


def _validate_perspective_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.perspective is None:
        return
    kind = PerspectiveKind(args.perspective)
    ck = CenterKind(args.center_kind)
    cref = (args.center_ref or "").strip()
    if cref and ck is CenterKind.NONE:
        parser.error(
            "--center-ref requires --center-kind symbol_id or symbol_qualified_name"
        )
    if kind in (PerspectiveKind.TRUST_DETAIL, PerspectiveKind.FOCUS_GRAPH):
        if ck is CenterKind.NONE or not cref:
            parser.error(
                f"--perspective {kind.value} requires --center-kind and non-empty --center-ref"
            )
    elif ck is not CenterKind.NONE:
        parser.error(
            "--center-kind/--center-ref only apply to --perspective trust_detail or focus_graph"
        )
    if kind is PerspectiveKind.MUTATION_TRACE:
        if not (args.mutation_key and str(args.mutation_key).strip()):
            parser.error(
                "--perspective mutation_trace requires non-empty --mutation-key "
                "(same semantics as --trace-mutation)"
            )
    if kind in (
        PerspectiveKind.HEURISTIC_SLICE,
        PerspectiveKind.QUERY_SLICE_JSON,
        PerspectiveKind.AGENT_NAMES,
        PerspectiveKind.AGENT_SYMBOL_LINES,
        PerspectiveKind.AGENT_COMPACT,
    ):
        if not (args.query and args.query.strip()):
            parser.error(
                f"--perspective {kind.value} requires a non-empty --query / -q"
            )


def _cli_focus(argv: list[str]) -> int:
    """Unterbefehl ``nexus focus`` — kanonischer Focus-Payload (JSON)."""
    from nexus.output.inference_projection import build_focus_payload

    fp = argparse.ArgumentParser(
        prog="nexus focus",
        description=(
            "Emit canonical focus payload JSON for one symbol (UI / CLI / LLM parity). "
            "Same structure as the Inference Console „Copy Focus (LLM)“."
        ),
    )
    fp.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root or single .py file (default: .)",
    )
    fp.add_argument(
        "--symbol",
        "-s",
        required=True,
        metavar="REF",
        help="Symbol id (symbol:…) or exact qualified_name.",
    )
    args = fp.parse_args(argv)
    root = Path(args.path)
    g = attach(root)
    sym = g.resolve_symbol_ref(args.symbol)
    if sym is None:
        sys.stderr.write(f"nexus focus: symbol not found: {args.symbol!r}\n")
        return 2
    out = json.dumps(build_focus_payload(g, sym), indent=2, ensure_ascii=False)
    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "focus":
        return _cli_focus(argv[1:])
    if argv and argv[0] == "matrix":
        from nexus.cli_matrix import main as matrix_main

        return matrix_main(argv[1:])

    parser = argparse.ArgumentParser(
        prog="nexus",
        description="Structural inference map for Python (symbols, calls, mutations, confidence).",
        epilog=(
            "Subcommands: "
            "nexus focus [PATH] -s REF — canonical focus payload JSON "
            "(nexus.focus_payload/v1; same as Inference Console „Copy Focus (LLM)“). "
            "nexus matrix {rain|focus|chain} … — semantic terminal projection (optional: pip install rich)."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root or single .py file (default: .)",
    )
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        metavar="TEXT",
        help=(
            "Filter/sort brief. Heuristics: mutation, flow. Special: "
            "'full mutation chain', 'impact SymbolName', 'core system flow', "
            "'core mutation', 'why runtime changed'."
        ),
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Only include symbols with confidence >= FLOAT in text brief.",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        metavar="N",
        help=f"Cap number of symbols in brief (query mode default: {DEFAULT_QUERY_MAX_SYMBOLS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full graph as JSON (ignores --query / --min-confidence).",
    )
    parser.add_argument(
        "--names-only",
        action="store_true",
        help=(
            "With -q: one qualified_name per line (minimal tokens). "
            "Falls back to full brief for special queries (impact / why / …)."
        ),
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help=(
            "When used with --names-only: emit a compact one-liner per symbol with "
            "confidence/tags/layer/file:line (slightly more tokens, fewer follow-up turns)."
        ),
    )
    parser.add_argument(
        "--query-slice-json",
        action="store_true",
        help=(
            "With -q: emit the Inference Console's bounded slice JSON (symbols in slice + "
            "edges whose endpoints are both in that set). Same as generic_query_symbol_slice "
            "+ build_json_slice."
        ),
    )
    parser.add_argument(
        "--trace-mutation",
        default=None,
        metavar="SUBSTRING",
        help=(
            "Emit InferenceGraph.trace_mutation(SUBSTRING) as JSON (direct / indirect / "
            "transitive). Same data as the Console Mutation tab."
        ),
    )
    parser.add_argument(
        "--focus-graph",
        default=None,
        metavar="QUALIFIED_NAME",
        help=(
            "Emit one-hop caller/callee layout as JSON for the symbol with this exact "
            "qualified_name — same as the Console Focus Graph."
        ),
    )
    _pk_values = [e.value for e in PerspectiveKind]
    _ck_values = [e.value for e in CenterKind]
    parser.add_argument(
        "--perspective",
        default=None,
        metavar="NAME",
        choices=_pk_values,
        help=(
            "Canonical perspective (same names as PerspectiveKind). Mutually exclusive "
            "with --json, --names-only, --query-slice-json, --trace-mutation, --focus-graph. "
            "Uses -q / --query, --max-symbols, --min-confidence; for center views use "
            "--center-kind and --center-ref; for mutation_trace use --mutation-key."
        ),
    )
    parser.add_argument(
        "--center-kind",
        default=CenterKind.NONE.value,
        choices=_ck_values,
        help="With --perspective trust_detail|focus_graph: how --center-ref is resolved.",
    )
    parser.add_argument(
        "--center-ref",
        default=None,
        metavar="REF",
        help="Symbol id or qualified_name (see --center-kind).",
    )
    parser.add_argument(
        "--mutation-key",
        default=None,
        metavar="SUBSTRING",
        help="With --perspective mutation_trace: state-key substring (same as --trace-mutation).",
    )
    parser.add_argument(
        "--mode",
        choices=("fresh", "persistent", "hybrid"),
        default="fresh",
        help=(
            "Inference strategy. fresh rebuilds the map each call (no cache). "
            "persistent/hybrid require --cache-dir and may store sensitive structure."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        metavar="PATH",
        help="Cache directory for persistent/hybrid modes (explicit opt-in).",
    )
    parser.add_argument(
        "--control-header",
        action="store_true",
        help="Emit a small [NEXUS_CONFIG] header to stderr before the answer.",
    )
    parser.add_argument(
        "--debug-perspective",
        action="store_true",
        help=(
            "After each perspective render, emit one JSON line to stderr with payload_kind, "
            "advice, error (if any), and provenance. Stdout unchanged."
        ),
    )
    parser.add_argument(
        "--metrics-json",
        action="store_true",
        help=(
            "After successful output, emit one JSON line to stderr (prefix [NEXUS_METRICS]) "
            "with size/slice/handoff hints for benchmarking. Or set NEXUS_METRICS_JSON=1."
        ),
    )
    parser.add_argument(
        "--compact-fields",
        default=None,
        metavar="SPEC",
        help=(
            "Only with --perspective agent_compact: field preset minimal|standard|full, or "
            "comma-list meta,calls,writes,called_by,reads,tags,next_open. "
            "Default when omitted: full (unchanged output vs. pre-flag)."
        ),
    )
    parser.add_argument(
        "--agent-mode",
        action="store_true",
        help=(
            "Opinionated agent entry: same as --perspective agent_compact with "
            f"--compact-fields minimal and --max-symbols {AGENT_MODE_DEFAULT_MAX_SYMBOLS} "
            "unless you pass those flags explicitly. Incompatible with --json, --names-only, "
            "and other legacy output modes."
        ),
    )
    args = parser.parse_args(argv)

    if args.agent_mode:
        if (
            args.json
            or args.names_only
            or args.query_slice_json
            or args.trace_mutation is not None
            or args.focus_graph is not None
        ):
            parser.error(
                "--agent-mode cannot be combined with --json, --names-only, "
                "--query-slice-json, --trace-mutation, or --focus-graph"
            )
        if (
            args.perspective is not None
            and args.perspective != PerspectiveKind.AGENT_COMPACT.value
        ):
            parser.error(
                "--agent-mode implies --perspective agent_compact; "
                "omit --perspective or set it to agent_compact"
            )
        args.perspective = PerspectiveKind.AGENT_COMPACT.value
        if args.compact_fields is None:
            args.compact_fields = "minimal"
        if args.max_symbols is None:
            args.max_symbols = AGENT_MODE_DEFAULT_MAX_SYMBOLS

    agent_compact_fields_resolved: frozenset[str] | None = None
    if args.compact_fields is not None:
        if args.perspective != PerspectiveKind.AGENT_COMPACT.value:
            parser.error("--compact-fields requires --perspective agent_compact")
        try:
            agent_compact_fields_resolved = parse_agent_compact_fields_arg(args.compact_fields)
        except ValueError as e:
            parser.error(str(e))

    legacy_output = (
        args.names_only,
        args.query_slice_json,
        args.trace_mutation is not None,
        args.focus_graph is not None,
    )
    if args.perspective is not None:
        if args.json or any(legacy_output):
            parser.error(
                "--perspective cannot be combined with --json, --names-only, "
                "--query-slice-json, --trace-mutation, or --focus-graph"
            )
    output_modes = (
        args.json,
        args.names_only,
        args.query_slice_json,
        args.trace_mutation is not None,
        args.focus_graph is not None,
    )
    if sum(1 for m in output_modes if m) > 1:
        parser.error(
            "Use only one of: --json, --names-only, --query-slice-json, "
            "--trace-mutation, --focus-graph"
        )
    if args.annotate and not args.names_only and args.perspective != PerspectiveKind.AGENT_SYMBOL_LINES.value:
        parser.error("--annotate requires --names-only or --perspective agent_symbol_lines")
    if args.mode != "fresh" and not args.cache_dir:
        parser.error("--mode persistent/hybrid requires --cache-dir")

    _validate_perspective_cli(args, parser)

    root = Path(args.path)
    if control_header_enabled(args.control_header):
        cfg = collect_control_config(
            repo_root=(root if root.is_dir() else root.parent),
            mode=args.mode,
            include_tests=True,
            transitive_depth=12,
            cache_dir=args.cache_dir,
        )
        cfg["version"] = nexus_version
        emit_control_header(cfg)
    g = attach(root, mode=args.mode, cache_dir=args.cache_dir)
    dbg = args.debug_perspective
    want_metrics = metrics_json_enabled(args.metrics_json)
    captured_stdout: str | None = None
    last_pr: PerspectiveResult | None = None
    include_query_slice_stats = False
    is_full_json = False
    output_mode = ""
    compact_fields_for_metrics: list[str] | None = None
    agent_mode_for_metrics = bool(args.agent_mode)

    def _emit_perspective_stdout(pr: PerspectiveResult) -> tuple[int, str | None]:
        if pr.payload_kind is PerspectivePayloadKind.ERROR:
            sys.stderr.write(f"nexus: {pr.error}\n")
            return 1, None
        if pr.payload_kind is PerspectivePayloadKind.NONE:
            sys.stderr.write("nexus: perspective returned no payload (unhandled advice?)\n")
            return 1, None
        if pr.payload_kind is PerspectivePayloadKind.SYMBOL_LIST:
            syms = pr.symbols or []
            if syms:
                text = "\n".join(s.qualified_name for s in syms) + "\n"
                sys.stdout.write(text)
                return 0, text
            return 0, ""
        if pr.payload_json is not None:
            out = json.dumps(pr.payload_json, indent=2, ensure_ascii=False)
            sys.stdout.write(out)
            if not out.endswith("\n"):
                sys.stdout.write("\n")
            captured = out if out.endswith("\n") else out + "\n"
            return 0, captured
        if pr.payload_text is not None:
            sys.stdout.write(pr.payload_text)
            if not pr.payload_text.endswith("\n"):
                sys.stdout.write("\n")
            captured = (
                pr.payload_text
                if pr.payload_text.endswith("\n")
                else pr.payload_text + "\n"
            )
            return 0, captured
        sys.stderr.write("nexus: empty perspective result\n")
        return 1, None

    if args.json:
        out = g.to_json()
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
        captured_stdout = out if out.endswith("\n") else out + "\n"
        output_mode = "full_graph_json"
        is_full_json = True
    elif args.perspective is not None:
        kind = PerspectiveKind(args.perspective)
        perspective_kind_for_metrics = kind
        req = PerspectiveRequest(
            kind=kind,
            graph=g,
            query=args.query,
            max_symbols=args.max_symbols,
            min_confidence=args.min_confidence,
            center_kind=CenterKind(args.center_kind),
            center_ref=(args.center_ref or "").strip() or None,
            mutation_key=(args.mutation_key or "").strip() or None,
            annotate=args.annotate,
            agent_compact_fields=agent_compact_fields_resolved,
        )
        pr = render_perspective(req)
        _debug_perspective_stderr(pr, dbg)
        if (
            kind
            in (
                PerspectiveKind.AGENT_SYMBOL_LINES,
                PerspectiveKind.AGENT_COMPACT,
            )
            and pr.advice is PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF
        ):
            pr = render_perspective(
                PerspectiveRequest(
                    kind=PerspectiveKind.LLM_BRIEF,
                    graph=g,
                    query=args.query,
                    max_symbols=args.max_symbols,
                    min_confidence=args.min_confidence,
                )
            )
            perspective_kind_for_metrics = PerspectiveKind.LLM_BRIEF
            _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = f"perspective:{perspective_kind_for_metrics.value}"
        if perspective_kind_for_metrics is PerspectiveKind.AGENT_COMPACT:
            eff = (
                agent_compact_default_fields()
                if agent_compact_fields_resolved is None
                else agent_compact_fields_resolved
            )
            compact_fields_for_metrics = sorted(eff)
        include_query_slice_stats = perspective_kind_for_metrics in (
            PerspectiveKind.LLM_BRIEF,
            PerspectiveKind.AGENT_NAMES,
            PerspectiveKind.AGENT_SYMBOL_LINES,
            PerspectiveKind.AGENT_COMPACT,
        )
    elif args.trace_mutation is not None:
        pr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.MUTATION_TRACE,
                graph=g,
                mutation_key=args.trace_mutation,
            )
        )
        _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = "trace_mutation"
    elif args.focus_graph is not None:
        pr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.FOCUS_GRAPH,
                graph=g,
                center_kind=CenterKind.SYMBOL_QUALIFIED_NAME,
                center_ref=args.focus_graph,
            )
        )
        _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = "focus_graph"
    elif args.query_slice_json:
        if not (args.query and args.query.strip()):
            parser.error("--query-slice-json requires a non-empty --query / -q")
        pr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.QUERY_SLICE_JSON,
                graph=g,
                query=args.query.strip(),
                max_symbols=args.max_symbols,
                min_confidence=args.min_confidence,
            )
        )
        _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = "query_slice_json"
    elif args.names_only:
        if not (args.query and args.query.strip()):
            parser.error("--names-only requires a non-empty --query / -q")
        pr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.AGENT_SYMBOL_LINES,
                graph=g,
                query=args.query,
                annotate=args.annotate,
                max_symbols=args.max_symbols,
                min_confidence=args.min_confidence,
            )
        )
        _debug_perspective_stderr(pr, dbg)
        if pr.advice is PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF:
            pr = render_perspective(
                PerspectiveRequest(
                    kind=PerspectiveKind.LLM_BRIEF,
                    graph=g,
                    query=args.query,
                    max_symbols=args.max_symbols,
                    min_confidence=args.min_confidence,
                )
            )
            _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = "names_only"
        include_query_slice_stats = True
    else:
        pr = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.LLM_BRIEF,
                graph=g,
                query=args.query,
                max_symbols=args.max_symbols,
                min_confidence=args.min_confidence,
            )
        )
        _debug_perspective_stderr(pr, dbg)
        code, captured_stdout = _emit_perspective_stdout(pr)
        if code != 0:
            return code
        last_pr = pr
        output_mode = "llm_brief"
        include_query_slice_stats = True

    if want_metrics and captured_stdout is not None:
        emit_context_metrics_line(
            build_context_metrics(
                stdout_payload=captured_stdout,
                output_mode=output_mode,
                graph=g,
                query=args.query,
                max_symbols_arg=args.max_symbols,
                min_confidence=args.min_confidence,
                pr=last_pr,
                is_full_json=is_full_json,
                include_query_slice_stats=include_query_slice_stats,
                compact_fields=compact_fields_for_metrics,
                agent_mode=agent_mode_for_metrics,
            )
        )
    return 0
