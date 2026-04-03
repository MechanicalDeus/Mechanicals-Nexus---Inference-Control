from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_nexus_benchmark_script_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "extras" / "nexus_benchmark.py"
    (tmp_path / "pkg.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "out.json"
    env = os.environ.copy()
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(tmp_path),
            "--query",
            "alpha",
            "--out-json",
            str(out),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["exit_code"] == 0
    assert data[0]["metrics"] is not None
    assert data[0]["metrics"].get("instrument") == "nexus_context_metrics"
