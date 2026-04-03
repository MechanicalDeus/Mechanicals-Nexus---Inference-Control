from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

def test_cli_opc_catalog_json() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(repo / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "nexus.cli_opc", "catalog", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo),
        env={**__import__("os").environ, **env},
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["schema_version"] == 1
    names = {op["name"] for op in data["opcodes"]}
    assert names >= {
        "map",
        "locate",
        "explain",
        "grep",
        "policy",
        "bench",
        "compare",
        "focus",
        "stats",
    }


def test_cli_opc_map_dry_run() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(repo / "src")}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "--dry-run",
            "map",
            "-q",
            "cli",
            str(repo / "src" / "nexus"),
            "--max-symbols",
            "5",
            "--",
            "--control-header",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo),
        env={**__import__("os").environ, **env},
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    line = json.loads(proc.stdout)
    argv = line["argv"]
    assert "-m" in argv and "nexus" in argv
    assert "--perspective" in argv and "heuristic_slice" in argv
    assert "--control-header" in argv


def test_cli_opc_locate_explain_focus_dry_run() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(repo / "src")}
    tiny = repo / "src" / "nexus"
    for argv in (
        [sys.executable, "-m", "nexus.cli_opc", "--dry-run", "locate", "-q", "flow", str(tiny)],
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "--dry-run",
            "explain",
            "--center-ref",
            "nexus.cli.main",
            str(tiny),
        ],
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "--dry-run",
            "focus",
            "-s",
            "nexus.cli.main",
            str(tiny),
        ],
    ):
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(repo),
            env={**__import__("os").environ, **env},
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr


def test_cli_opc_log_append_and_stats(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    env = {"PYTHONPATH": str(repo / "src")}
    logf = tmp_path / "runs.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "--opc-log-append",
            str(logf),
            "--opc-roi-score",
            "0.91",
            "--opc-run-id",
            "t1",
            "--dry-run",
            "locate",
            "-q",
            "x",
            ".",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo),
        env={**__import__("os").environ, **env},
        timeout=30,
    )
    assert proc.returncode == 0
    assert not logf.exists(), "dry-run must not write log"

    proc2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "--opc-log-append",
            str(logf),
            "--opc-roi-score",
            "0.5",
            "--opc-run-id",
            "t1",
            "catalog",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo),
        env={**__import__("os").environ, **env},
        timeout=30,
    )
    assert proc2.returncode == 0, proc2.stderr
    assert logf.is_file()
    lines = logf.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = __import__("json").loads(lines[0])
    assert row["opcode"] == "catalog"
    assert row["roi"] == 0.5
    assert row["run_id"] == "t1"

    proc3 = subprocess.run(
        [
            sys.executable,
            "-m",
            "nexus.cli_opc",
            "stats",
            str(logf),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo),
        env={**__import__("os").environ, **env},
        timeout=30,
    )
    assert proc3.returncode == 0, proc3.stderr
    agg = json.loads(proc3.stdout)
    assert agg["opcode_stats"]["catalog"]["count"] == 1
    assert abs(agg["opcode_stats"]["catalog"]["avg_roi"] - 0.5) < 1e-9
