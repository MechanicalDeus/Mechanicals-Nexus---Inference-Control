"""Write SVG placeholders for docs/assets/usage-metrics/ (stdlib only)."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "usage-metrics"

NAMES = [
    "without-nexus-1",
    "without-nexus-2",
    "without-nexus-3",
    "without-nexus-4",
    "without-nexus-5",
    "with-nexus-1",
    "with-nexus-2",
    "nexus-self-scan",
    "ttrpg-studio-with-nexus",
    "ttrpg-studio-without-nexus",
    "cursor-cross-repo-orientation-110k",
]

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="920" height="200" viewBox="0 0 920 200" role="img" aria-label="Usage metrics placeholder">
  <rect width="100%" height="100%" fill="#f6f8fa" stroke="#d0d7de" stroke-width="2" rx="6"/>
  <text x="460" y="82" text-anchor="middle" font-family="system-ui,Segoe UI,Helvetica,Arial,sans-serif" font-size="17" font-weight="600" fill="#1f2328">Cursor usage metrics (placeholder)</text>
  <text x="460" y="114" text-anchor="middle" font-family="ui-monospace,Courier New,monospace" font-size="13" fill="#656d76">{png_name}.png</text>
  <text x="460" y="142" text-anchor="middle" font-family="system-ui,Segoe UI,sans-serif" font-size="12" fill="#8c959f">Export from Cursor and replace this SVG, or keep as a figure stub.</text>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for base in NAMES:
        png_name = f"{base}.png"
        path = OUT / f"{base}.svg"
        path.write_text(SVG_TEMPLATE.format(png_name=base), encoding="utf-8")
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
