from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from nexus.semantic_palette import TEXT_MUTED, TEXT_PRIMARY
from nexus.terminal_semantic import (
    layer_badge_markup,
    matrix_rain_symbol_style,
)


def test_layer_badge_markup() -> None:
    assert "[CORE]" in layer_badge_markup("core")
    assert "[IFACE]" in layer_badge_markup("interface")


def test_matrix_rain_symbol_style_bounds() -> None:
    assert matrix_rain_symbol_style(intensity=-1) == f"dim {TEXT_MUTED}"
    assert matrix_rain_symbol_style(intensity=2) == f"bold {TEXT_PRIMARY}"


def test_matrix_help_exits_zero() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "nexus", "matrix", "--help"],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "rain" in r.stdout


@pytest.mark.skipif(
    importlib.util.find_spec("rich") is None,
    reason="rich optional; install nexus-inference[matrix]",
)
def test_matrix_rain_non_tty_emits_multiple_lines() -> None:
    """Ohne TTY darf kein Live-only-Endframe sein — zeilenweiser Stream."""
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus",
            "matrix",
            "rain",
            "src/nexus",
            "--seconds",
            "0.35",
            "--fps",
            "10",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout.count("symbol:") >= 3


@pytest.mark.skipif(
    importlib.util.find_spec("rich") is None,
    reason="rich optional; install nexus-inference[matrix]",
)
def test_matrix_focus_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus",
            "matrix",
            "focus",
            "src/nexus",
            "-s",
            "cli.main",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "cli.main" in r.stdout
