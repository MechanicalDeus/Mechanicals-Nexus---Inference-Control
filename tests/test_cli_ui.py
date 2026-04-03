"""Dispatch tests for ``nexus ui`` / ``nexus console`` (GUI entry via main CLI)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    importlib.util.find_spec("PyQt6") is not None,
    reason="nexus ui starts Qt main loop when PyQt6 is installed",
)
def test_nexus_ui_exits_with_install_hint_without_pyqt6() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "nexus", "ui"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert r.returncode == 1
    combined = (r.stderr or "") + (r.stdout or "")
    assert "PyQt6" in combined


def test_nexus_console_alias_dispatches_same_as_ui() -> None:
    """Both subcommand names hit the UI entry (same failure path without Qt)."""
    if importlib.util.find_spec("PyQt6") is not None:
        pytest.skip("PyQt6 installed — would start GUI")

    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    r_ui = subprocess.run(
        [sys.executable, "-m", "nexus", "ui"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    r_console = subprocess.run(
        [sys.executable, "-m", "nexus", "console"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert r_ui.returncode == r_console.returncode == 1
