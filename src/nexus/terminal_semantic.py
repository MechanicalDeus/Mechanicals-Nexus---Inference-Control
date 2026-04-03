"""
Semantische Terminal-Stile — gleiche Hex-Basis wie ``nexus.semantic_palette`` / UI.

Rich-Markup und optionale ANSI-Truecolor-Fallbacks (Plaintext + TTY).
"""

from __future__ import annotations

from nexus.semantic_palette import (
    GRAPH_ROLE_HEX,
    HEX_CENTER,
    HEX_FOCUS_LOCK,
    INFLUENCE_LABEL_HEX,
    LAYER_LABEL_HEX,
    SEMANTIC_RELATION_HEX,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

# Rückwärtskompatibel mit frühen Imports
HEX_CALLER = GRAPH_ROLE_HEX["caller"]
HEX_CALLEE = GRAPH_ROLE_HEX["callee"]
HEX_ACCENT = SEMANTIC_RELATION_HEX["calls"]
HEX_IMPACT = SEMANTIC_RELATION_HEX["writes"]
HEX_MUTED = TEXT_MUTED

RELATION_MARKUP = {
    "called_by": f"[bold {SEMANTIC_RELATION_HEX['called_by']}]called_by[/]",
    "writes": f"[bold {SEMANTIC_RELATION_HEX['writes']}]writes[/]",
    "calls": f"[bold {SEMANTIC_RELATION_HEX['calls']}]calls[/]",
    "reads": f"[{SEMANTIC_RELATION_HEX['reads']}]reads[/]",
}

ROLE_MARKUP = {
    "center": f"[bold {HEX_CENTER}]",
    "caller": f"[{HEX_CALLER}]",
    "callee": f"[{HEX_CALLEE}]",
}

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"


def ansi_truecolor_fg(hex_rgb: str) -> str:
    h = hex_rgb.strip().removeprefix("#")
    if len(h) != 6:
        return ""
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


def layer_badge_markup(layer: str) -> str:
    key = (layer or "").strip().lower()
    tags = {
        "core": "CORE",
        "interface": "IFACE",
        "support": "SUPPORT",
        "test": "TEST",
    }
    tag = tags.get(key, (key.upper() if key else "?"))
    h = LAYER_LABEL_HEX.get(key, TEXT_MUTED)
    return f"[bold {h}][{tag}][/]"


def layer_badge_plain(layer: str, *, use_color: bool) -> str:
    key = (layer or "").strip().lower()
    tags = {
        "core": "CORE",
        "interface": "IFACE",
        "support": "SUPPORT",
        "test": "TEST",
    }
    tag = tags.get(key, (key.upper() if key else "?"))
    inner = f"[{tag}]"
    if not use_color:
        return inner
    h = LAYER_LABEL_HEX.get(key, TEXT_MUTED)
    return f"{ansi_truecolor_fg(h)}{ANSI_BOLD}{inner}{ANSI_RESET}"


def focus_banner_markup() -> str:
    return f"[bold {HEX_FOCUS_LOCK}]▌ FOCUS LOCKED[/]"


def focus_banner_plain(*, use_color: bool) -> str:
    if not use_color:
        return "▌ FOCUS LOCKED"
    return f"{ansi_truecolor_fg(HEX_FOCUS_LOCK)}{ANSI_BOLD}▌ FOCUS LOCKED{ANSI_RESET}"


def chain_banner_markup() -> str:
    return f"[bold {HEX_FOCUS_LOCK}]▌ CHAIN[/]"


def matrix_rain_symbol_style(*, intensity: float) -> str:
    """Symbolname: hell (primary), gedimmt = weniger Kontrast — kein Grünzwang."""
    t = max(0.0, min(1.0, float(intensity)))
    if t < 0.35:
        return f"dim {TEXT_MUTED}"
    if t < 0.7:
        return TEXT_PRIMARY
    return f"bold {TEXT_PRIMARY}"


def matrix_panel_title_markup() -> str:
    return f"[bold {HEX_FOCUS_LOCK}]NEXUS MATRIX[/] [dim {TEXT_MUTED}]— stream[/]"


def relation_plain_label(rel: str, *, use_color: bool) -> str:
    if not use_color:
        return rel
    h = SEMANTIC_RELATION_HEX.get(rel, TEXT_PRIMARY)
    return f"{ansi_truecolor_fg(h)}{ANSI_BOLD}{rel}{ANSI_RESET}"


def influence_plain_summary(inf: dict, *, use_color: bool) -> str:
    t = int(inf.get("total", 0))
    c = int(inf.get("calls", 0))
    w = int(inf.get("writes", 0))
    if not use_color:
        return f"influence → total={t} calls={c} writes={w}"
    lab = f"{ansi_truecolor_fg(INFLUENCE_LABEL_HEX)}{ANSI_BOLD}influence{ANSI_RESET}"
    cyan = ansi_truecolor_fg(SEMANTIC_RELATION_HEX["calls"])
    red = ansi_truecolor_fg(SEMANTIC_RELATION_HEX["writes"])
    return (
        f"{lab} → total={t} {cyan}calls={c}{ANSI_RESET} {red}writes={w}{ANSI_RESET}"
    )


__all__ = [
    "ANSI_BOLD",
    "ANSI_DIM",
    "ANSI_RESET",
    "HEX_ACCENT",
    "HEX_CALLEE",
    "HEX_CALLER",
    "HEX_CENTER",
    "HEX_IMPACT",
    "HEX_MUTED",
    "RELATION_MARKUP",
    "ROLE_MARKUP",
    "ansi_truecolor_fg",
    "chain_banner_markup",
    "focus_banner_markup",
    "focus_banner_plain",
    "influence_plain_summary",
    "layer_badge_markup",
    "layer_badge_plain",
    "matrix_panel_title_markup",
    "matrix_rain_symbol_style",
    "relation_plain_label",
]
