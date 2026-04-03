"""
``nexus matrix`` — semantisch eingefärbte Terminal-Projektion (optional Rich).

Unterbefehle:
  rain   — scrollende echte Symbolnamen aus dem Graph (Idle-/Matrix-Feel)
  focus  — strukturierter Focus wie Payload, eingefärbt
  chain  — Inferenzkette Schritt für Schritt (build_inference_chain)
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path

from nexus import attach
from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord
from nexus.output.inference_projection import (
    build_focus_payload,
    build_inference_chain,
)
from nexus.semantic_palette import (
    ACCENT,
    HEX_CENTER,
    INFLUENCE_LABEL_HEX,
    SEMANTIC_RELATION_HEX,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from nexus.terminal_semantic import (
    ANSI_BOLD,
    ANSI_RESET,
    RELATION_MARKUP,
    ansi_truecolor_fg,
    chain_banner_markup,
    focus_banner_markup,
    focus_banner_plain,
    influence_plain_summary,
    layer_badge_markup,
    layer_badge_plain,
    matrix_panel_title_markup,
    matrix_rain_symbol_style,
    relation_plain_label,
)


def _stdout_is_tty() -> bool:
    """Rich Live braucht typischerweise eine echte TTY; Pipes/Agent-Capture meist nicht."""
    try:
        return sys.stdout.isatty()
    except (AttributeError, OSError, ValueError):
        return False


def _rich_colors_wanted(color: str, *, force_terminal_cli: bool) -> bool:
    """
    Hex-Markup aus semantic_palette braucht truecolor; Windows/VS-Code-„auto“
    wählt sonst oft ein Schema ohne 24-Bit → alles wirkt grau.
    """
    if color == "never":
        return False
    if "NO_COLOR" in os.environ:
        return False
    if color == "always":
        return True
    if force_terminal_cli:
        return True
    fc = (os.environ.get("FORCE_COLOR") or os.environ.get("NEXUS_FORCE_COLOR") or "").strip().lower()
    if fc in ("1", "true", "yes", "always"):
        return True
    return _stdout_is_tty()


def _make_rich_console(Console: type, *, colors: bool):
    if not colors:
        return Console(no_color=True, highlight=False)
    return Console(
        force_terminal=True,
        color_system="truecolor",
        highlight=False,
    )


def _log_candy_rain_banner(console: object, Text: type, *, repo: str) -> None:
    """Kurzer Rahmen für Nicht-TTY (Agent-Terminal, CI): sichtbar, nicht spammig."""
    console.print()
    console.print(
        Text.from_markup(
            f"[bold {INFLUENCE_LABEL_HEX}]▌ NEXUS MATRIX[/] [dim {TEXT_MUTED}]rain[/] "
            f"[dim italic {TEXT_MUTED}]· one line per frame (agent / pipe friendly)[/]"
        )
    )
    console.print(Text.from_markup(f"[dim]{repo}[/]"))
    console.print(Text("  " + "· " * 26, style=f"dim {SEMANTIC_RELATION_HEX['called_by']}"))


def _log_candy_chain_banner(console: object, Text: type) -> None:
    console.print()
    console.print(
        Text.from_markup(
            f"[bold {INFLUENCE_LABEL_HEX}]▌ CHAIN[/] [dim {TEXT_MUTED}]steps[/] "
            f"[dim italic {TEXT_MUTED}]· growing blocks in log (agent / pipe friendly)[/]"
        )
    )
    console.print(
        Text("  " + "· " * 26, style=f"dim {SEMANTIC_RELATION_HEX['calls']}")
    )


def _log_candy_footer(console: object, Text: type, *, frames: int, label: str) -> None:
    console.print(
        Text.from_markup(
            f"[dim {SEMANTIC_RELATION_HEX['called_by']}]▌[/] [dim]{frames} frame(s) · {label}[/]"
        )
    )
    console.print()


def _relation_for_hop_to_index(
    graph: InferenceGraph,
    sym: SymbolRecord,
    chain: list[str],
    target_idx: int,
) -> str:
    """Letzter Hop zum ersten Callee = calls (cyan); sonst called_by (grün)."""
    if target_idx <= 0:
        return "called_by"
    if (
        target_idx == len(chain) - 1
        and sym.calls
        and chain[-1] == graph.resolve_display_ref(sym.calls[0])
    ):
        return "calls"
    return "called_by"


def _try_rich():
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.tree import Tree

        return True, Console, Live, Panel, Text, Tree
    except ImportError:
        return (False,)


def _cmd_rain(
    path: Path,
    *,
    seconds: float | None,
    fps: int,
    fullscreen: bool,
    print_stream: bool,
    force_live: bool,
    force_terminal: bool,
    no_banner: bool,
    color: str,
) -> int:
    g = attach(path)
    rows = sorted(
        (
            (s.qualified_name, (s.layer or "support").strip().lower())
            for s in g.symbols.values()
        ),
        key=lambda t: t[0],
    )
    if not rows:
        sys.stderr.write("nexus matrix rain: no symbols in graph.\n")
        return 1
    if len(rows) > 4000:
        rows = rows[:4000]

    ok, *mod = _try_rich()
    if not ok:
        sys.stderr.write(
            "nexus matrix rain: requires the 'rich' package. "
            "Install with: pip install rich\n"
            "   or: pip install nexus-inference[matrix]\n"
        )
        return 2
    Console, Live, Panel, Text, _Tree = mod
    want_color = _rich_colors_wanted(color, force_terminal_cli=force_terminal)
    console = _make_rich_console(Console, colors=want_color)
    h = max(8, min(console.size.height - 3, 28))
    idx = 0
    start = time.monotonic()
    rng = random.Random(42)
    refresh = max(4, min(30, int(fps)))
    frame_interval = 1.0 / refresh

    if print_stream:
        use_live = False
    elif force_live:
        use_live = True
    else:
        use_live = _stdout_is_tty()

    def frame() -> Panel:
        out = Text()
        n = len(rows)
        for row in range(h):
            sym, layer = rows[(idx + row) % n]
            wave = (row + idx) % 7
            intensity = 0.25 + 0.12 * wave + 0.08 * (rng.random() if row % 3 == 0 else 0.5)
            style = matrix_rain_symbol_style(intensity=intensity)
            line = Text()
            line.append("  ·  ", style=f"dim {TEXT_MUTED}")
            line.append(Text.from_markup(layer_badge_markup(layer)))
            line.append(" symbol: ", style=TEXT_MUTED)
            line.append(sym, style=style)
            if row:
                out.append("\n")
            out.append(line)
        return Panel(
            out,
            title=matrix_panel_title_markup(),
            subtitle=f"[dim]{g.repo_root}[/]",
            border_style=ACCENT,
        )

    if not use_live:
        # Jeder Tick = neue Zeile → in Logs und ohne TTY sichtbare „Animation“
        ticks = 0
        interrupted = False
        if not no_banner:
            _log_candy_rain_banner(console, Text, repo=str(g.repo_root))
        try:
            while True:
                if seconds is not None and (time.monotonic() - start) >= seconds:
                    break
                sym, layer = rows[idx % len(rows)]
                wave = idx % 7
                intensity = 0.25 + 0.12 * wave + 0.08 * rng.random()
                style = matrix_rain_symbol_style(intensity=intensity)
                console.print(
                    Text.assemble(
                        Text("  ·  ", style=f"dim {TEXT_MUTED}"),
                        Text.from_markup(layer_badge_markup(layer)),
                        Text(" symbol: ", style=TEXT_MUTED),
                        Text(sym, style=style),
                    )
                )
                idx += 1
                ticks += 1
                time.sleep(frame_interval)
        except KeyboardInterrupt:
            interrupted = True
        finally:
            if not no_banner:
                _log_candy_footer(
                    console,
                    Text,
                    frames=ticks,
                    label="interrupted" if interrupted else "stream end",
                )
        return 0

    with Live(
        frame(),
        console=console,
        refresh_per_second=refresh,
        screen=fullscreen,
        transient=False,
    ) as live:
        try:
            while True:
                if seconds is not None and (time.monotonic() - start) >= seconds:
                    break
                idx += 1
                live.update(frame())
                time.sleep(frame_interval)
        except KeyboardInterrupt:
            pass
    return 0


def _plain_focus(payload: dict, *, use_color: bool) -> None:
    sys.stdout.write(focus_banner_plain(use_color=use_color) + "\n")
    layer = str(payload.get("layer") or "")
    badge = layer_badge_plain(layer, use_color=use_color)
    name = str(payload.get("symbol") or "")
    if use_color:
        sys.stdout.write(
            f"{badge} {ansi_truecolor_fg(TEXT_PRIMARY)}{ANSI_BOLD}{name}{ANSI_RESET}\n"
        )
    else:
        sys.stdout.write(f"{badge} {name}\n")
    inf = payload.get("influence_breakdown") or {}
    sys.stdout.write(influence_plain_summary(inf, use_color=use_color) + "\n")
    for row in payload.get("reason") or []:
        rt = str(row.get("type") or "")
        tgt = str(row.get("target") or "")
        lbl = relation_plain_label(rt, use_color=use_color)
        if use_color:
            sys.stdout.write(
                f"  └── {lbl} → {ansi_truecolor_fg(TEXT_MUTED)}{tgt}{ANSI_RESET}\n"
            )
        else:
            sys.stdout.write(f"  └── {rt} → {tgt}\n")


def _cmd_focus(
    path: Path,
    symbol_ref: str,
    *,
    force_terminal: bool = False,
    color: str = "auto",
) -> int:
    g = attach(path)
    sym = g.resolve_symbol_ref(symbol_ref)
    if sym is None:
        sys.stderr.write(f"nexus matrix focus: symbol not found: {symbol_ref!r}\n")
        return 2
    payload = build_focus_payload(g, sym)
    ok, *mod = _try_rich()
    if not ok:
        want = _rich_colors_wanted(color, force_terminal_cli=force_terminal)
        _plain_focus(payload, use_color=want)
        return 0
    _Console, _Live, _Panel, Text, Tree = mod
    want_color = _rich_colors_wanted(color, force_terminal_cli=force_terminal)
    console = _make_rich_console(_Console, colors=want_color)
    title = Text.from_markup(focus_banner_markup())
    badge = Text.from_markup(
        f"{layer_badge_markup(str(payload.get('layer') or ''))} "
        f"[bold white]{payload.get('symbol')}[/]"
    )
    tree = Tree(badge)
    reason = payload.get("reason") or []
    for row in reason:
        rt = str(row.get("type") or "")
        tgt = str(row.get("target") or "")
        label = RELATION_MARKUP.get(rt, f"[white]{rt}[/]")
        tree.add(Text.from_markup(f"{label} [white]→[/] [dim]{tgt}[/]"))
    inf = payload.get("influence_breakdown") or {}
    tree.add(
        Text.from_markup(
            f"[bold {INFLUENCE_LABEL_HEX}]influence[/] [white]→[/] "
            f"[dim {TEXT_MUTED}]total={inf.get('total', 0)}[/] "
            f"[{SEMANTIC_RELATION_HEX['calls']}]calls={inf.get('calls', 0)}[/] "
            f"[{SEMANTIC_RELATION_HEX['writes']}]writes={inf.get('writes', 0)}[/]"
        )
    )
    console.print()
    console.print(title)
    console.print(tree)
    console.print()
    return 0


def _plain_chain(
    graph: InferenceGraph,
    sym: SymbolRecord,
    chain: list[str],
    *,
    use_color: bool,
) -> None:
    for i, node in enumerate(chain):
        if i:
            rel = _relation_for_hop_to_index(graph, sym, chain, i)
            lbl = relation_plain_label(rel, use_color=use_color)
            sys.stdout.write(f"  └── {lbl} →\n")
        if use_color:
            if i == len(chain) - 1:
                sys.stdout.write(
                    f"{ansi_truecolor_fg(HEX_CENTER)}{ANSI_BOLD}{node}{ANSI_RESET}\n"
                )
            else:
                sys.stdout.write(f"{ansi_truecolor_fg(TEXT_PRIMARY)}{node}{ANSI_RESET}\n")
        else:
            sys.stdout.write(f"{node}\n")


def _cmd_chain(
    path: Path,
    symbol_ref: str,
    *,
    step_sleep: float,
    print_steps: bool,
    force_live: bool,
    force_terminal: bool,
    no_banner: bool,
    color: str,
) -> int:
    g = attach(path)
    sym = g.resolve_symbol_ref(symbol_ref)
    if sym is None:
        sys.stderr.write(f"nexus matrix chain: symbol not found: {symbol_ref!r}\n")
        return 2
    chain = build_inference_chain(g, sym)
    if not chain:
        sys.stderr.write("nexus matrix chain: empty chain.\n")
        return 1
    ok, *mod = _try_rich()
    if not ok:
        want = _rich_colors_wanted(color, force_terminal_cli=force_terminal)
        _plain_chain(g, sym, chain, use_color=want)
        return 0
    Console, Live, _Panel, Text, _Tree = mod
    want_color = _rich_colors_wanted(color, force_terminal_cli=force_terminal)
    console = _make_rich_console(Console, colors=want_color)
    delay = max(0.0, float(step_sleep))

    def render(k: int) -> Text:
        out = Text.from_markup(chain_banner_markup())
        out.append("\n")
        for i, node in enumerate(chain[:k]):
            if i:
                rel = _relation_for_hop_to_index(g, sym, chain, i)
                rh = SEMANTIC_RELATION_HEX[rel]
                out.append("\n  ", style=f"dim {TEXT_MUTED}")
                out.append(f"└── {rel} →", style=f"bold {rh}")
                out.append("\n", style="")
            style = f"bold {HEX_CENTER}" if i == k - 1 else TEXT_PRIMARY
            out.append(node, style=style)
        return out

    if delay <= 0:
        console.print(render(len(chain)))
        return 0

    want_live = not print_steps and (force_live or _stdout_is_tty())

    if not want_live:
        if not no_banner and delay > 0:
            _log_candy_chain_banner(console, Text)
        for k in range(1, len(chain) + 1):
            console.print(render(k))
            if k < len(chain):
                time.sleep(delay)
        if not no_banner and delay > 0:
            _log_candy_footer(
                console,
                Text,
                frames=len(chain),
                label="chain end",
            )
        else:
            console.print()
        return 0

    with Live(console=console, refresh_per_second=min(30, max(5, int(1.0 / delay)))) as live:
        for k in range(1, len(chain) + 1):
            live.update(render(k))
            time.sleep(delay)
    console.print()
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="nexus matrix",
        description=(
            "Semantic terminal projection for Nexus (Matrix-style stream + focus + chain). "
            "Optional dependency: pip install rich. "
            "Without a real TTY (e.g. agent tools, pipes), rain/chain use a line-by-line "
            "log stream so motion stays visible — with a small decorative banner."
        ),
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help=(
            "Colored output (semantic hex = truecolor). "
            "Use 'always' if VS Code / Windows shows no colors. "
            "Env: NO_COLOR (off), FORCE_COLOR / NEXUS_FORCE_COLOR=1 (on). "
            "Place before the subcommand, e.g. nexus matrix --color always rain ."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rain = sub.add_parser("rain", help="Scroll real symbol names from the graph (idle stream).")
    p_rain.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repo root or .py file (default: .)",
    )
    p_rain.add_argument(
        "--seconds",
        type=float,
        default=None,
        metavar="N",
        help="Stop after N seconds (default: run until Ctrl+C).",
    )
    p_rain.add_argument(
        "--fps",
        type=int,
        default=12,
        metavar="N",
        help="Target refresh rate (default: 12).",
    )
    p_rain.add_argument(
        "--fullscreen",
        action="store_true",
        help="Use alternate screen (clears terminal; exit restores).",
    )
    p_rain.add_argument(
        "--print-stream",
        action="store_true",
        help="One symbol per frame as new lines (visible in logs / non-TTY).",
    )
    p_rain.add_argument(
        "--force-live",
        action="store_true",
        help="Use Rich Live refresh even when stdout is not a TTY (often useless).",
    )
    p_rain.add_argument(
        "--force-terminal",
        action="store_true",
        help="Tell Rich the output is a terminal (colors/controls; use sparingly).",
    )
    p_rain.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress log-mode header/footer (rain line stream).",
    )

    p_focus = sub.add_parser("focus", help="Focus lock: colored reason tree for one symbol.")
    p_focus.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repo root or .py file (default: .)",
    )
    p_focus.add_argument(
        "--symbol",
        "-s",
        required=True,
        metavar="REF",
        help="Symbol id or qualified_name.",
    )
    p_focus.add_argument(
        "--force-terminal",
        action="store_true",
        help="Tell Rich the output is a terminal (use sparingly).",
    )

    p_chain = sub.add_parser(
        "chain",
        help="Animate inference_chain (called_by walk + center + first call).",
    )
    p_chain.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repo root or .py file (default: .)",
    )
    p_chain.add_argument(
        "--symbol",
        "-s",
        required=True,
        metavar="REF",
        help="Symbol id or qualified_name.",
    )
    p_chain.add_argument(
        "--step-delay",
        type=float,
        default=0.18,
        metavar="SEC",
        help="Pause between chain steps (default: 0.18; 0 = instant).",
    )
    p_chain.add_argument(
        "--print-steps",
        action="store_true",
        help="Print the growing chain line-by-line (no Live); best for logs / non-TTY.",
    )
    p_chain.add_argument(
        "--force-live",
        action="store_true",
        help="Use Rich Live even when stdout is not a TTY.",
    )
    p_chain.add_argument(
        "--force-terminal",
        action="store_true",
        help="Tell Rich the output is a terminal (use sparingly).",
    )
    p_chain.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress log-mode header/footer (chain step stream).",
    )

    args = parser.parse_args(argv)
    root = Path(args.path)

    if args.cmd == "rain":
        return _cmd_rain(
            root,
            seconds=args.seconds,
            fps=args.fps,
            fullscreen=args.fullscreen,
            print_stream=args.print_stream,
            force_live=args.force_live,
            force_terminal=args.force_terminal,
            no_banner=args.no_banner,
            color=args.color,
        )
    if args.cmd == "focus":
        return _cmd_focus(
            root,
            args.symbol,
            force_terminal=args.force_terminal,
            color=args.color,
        )
    if args.cmd == "chain":
        return _cmd_chain(
            root,
            args.symbol,
            step_sleep=args.step_delay,
            print_steps=args.print_steps,
            force_live=args.force_live,
            force_terminal=args.force_terminal,
            no_banner=args.no_banner,
            color=args.color,
        )
    parser.error(f"unknown command: {args.cmd!r}")
    return 1
