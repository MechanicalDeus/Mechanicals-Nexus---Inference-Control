from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def _load_benchmark_module(repo_root: Path):
    script = repo_root / "extras" / "nexus_benchmark.py"
    spec = importlib.util.spec_from_file_location("nexus_benchmark_mod", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_roi_formulas() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    m = _load_benchmark_module(repo_root)
    assert m.efficiency_score(1) == 1.0
    assert abs(m.efficiency_score(2) - 1.0 / 1.7) < 1e-9
    assert m.cost_hat_nexus(None, token_budget=100_000) == 0.0
    assert m.cost_hat_nexus(50_000, token_budget=100_000) == 0.5
    assert m.cost_hat_nexus(150_000, token_budget=100_000) == 1.0
    q = m.quality_from_ground_truth("partial")
    assert q == 0.5
    E = m.efficiency_score(3)
    C = m.cost_hat_nexus(30_000, token_budget=100_000)
    score = m.roi_composite_score(q, E, C, wq=0.6, we=0.3, wc=0.1)
    assert score is not None
    assert abs(score - (0.6 * 0.5 + 0.3 * E - 0.1 * C)) < 1e-9


def test_build_roi_report_for_row() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    m = _load_benchmark_module(repo_root)
    row = {
        "repo": "/tmp/r",
        "query": "q",
        "exit_code": 0,
        "error": None,
        "metrics": {"output_tokens_tiktoken": 1000, "symbols_in_result": 3},
    }
    r = m.build_roi_report_for_row(
        row,
        run_id="nx-test",
        phases=4,
        iterations=1,
        ground_truth_kind="manual",
        ground_truth_result="hit",
    )
    assert r["scores"]["Q"] == 1.0
    assert r["scores"]["E"] == 1.0
    assert r["scores"]["roi_score"] is not None
    assert r["metrics"]["nexus_output_tokens"] == 1000
    assert r["metrics"]["symbols_returned"] == 3
    assert r["errors"]["types"] == []


def test_low_confidence_error_type() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    m = _load_benchmark_module(repo_root)
    row = {
        "repo": "/tmp/r",
        "query": "q",
        "exit_code": 0,
        "error": None,
        "metrics": {
            "output_tokens_tiktoken": 100,
            "symbols_in_result": 2,
            "slice_avg_confidence": 0.35,
        },
    }
    r = m.build_roi_report_for_row(
        row,
        run_id="x",
        ground_truth_kind="none",
        ground_truth_result=None,
        low_confidence_threshold=0.4,
    )
    assert "low_confidence" in r["errors"]["types"]
    assert r["metrics"]["avg_confidence"] == 0.35


def test_ground_truth_sidecar_and_per_row() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    m = _load_benchmark_module(repo_root)
    rows = [
        {"repo": "R", "query": "flow", "exit_code": 0, "metrics": None},
        {"repo": "R", "query": "mutation", "exit_code": 0, "metrics": None},
    ]
    gt = {
        "queries": {"flow": "hit", "mutation": "partial"},
        "kind": "golden",
    }
    pr = m.build_per_row_ground_truth(
        rows, gt_file=gt, cli_result="miss", cli_kind="manual"
    )
    assert pr[0] == ("hit", "golden")
    assert pr[1] == ("partial", "golden")
    pr2 = m.build_per_row_ground_truth(
        rows, gt_file=None, cli_result="miss", cli_kind="manual"
    )
    assert pr2[0] == ("miss", "manual")


def test_build_roi_compare_document() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    m = _load_benchmark_module(repo_root)
    old_runs = [
        {
            "repo": "R",
            "query": "q",
            "scores": {"roi_score": 0.5, "Q": 1.0, "E": 1.0, "C_hat": 0.1},
            "metrics": {"nexus_output_tokens": 100},
        }
    ]
    new_runs = [
        {
            "repo": "R",
            "query": "q",
            "scores": {"roi_score": 0.7, "Q": 1.0, "E": 1.0, "C_hat": 0.05},
            "metrics": {"nexus_output_tokens": 50},
        },
        {
            "repo": "R",
            "query": "only_new",
            "scores": {"roi_score": 0.1},
            "metrics": {},
        },
    ]
    doc = m.build_roi_compare_document(old_runs, new_runs)
    assert doc["kind"] == "roi_compare"
    assert len(doc["pairs"]) == 1
    assert abs(doc["pairs"][0]["delta"]["roi_score"] - 0.2) < 1e-9
    assert len(doc["only_new"]) == 1
    assert len(doc["only_old"]) == 0


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


def test_nexus_benchmark_out_roi_json_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "extras" / "nexus_benchmark.py"
    (tmp_path / "pkg.py").write_text("def beta():\n    return 2\n", encoding="utf-8")
    out = tmp_path / "out.json"
    roi_path = tmp_path / "roi.json"
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
            "beta",
            "--out-json",
            str(out),
            "--out-roi-json",
            str(roi_path),
            "--roi-ground-truth-result",
            "hit",
            "--roi-phases",
            "3",
            "--roi-session-error-tokens",
            "100",
            "--roi-session-total-tokens",
            "1000",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    roi = json.loads(roi_path.read_text(encoding="utf-8"))
    assert roi["schema_version"] == 1
    assert roi["session"]["error_cost_ratio"] == 0.1
    assert len(roi["runs"]) == 1
    assert roi["runs"][0]["ground_truth"]["result"] == "hit"
    assert roi["runs"][0]["phases"] == 3
    bench = json.loads(out.read_text(encoding="utf-8"))
    assert "roi" not in bench[0]


def test_nexus_benchmark_roi_enrich_attaches_roi(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "extras" / "nexus_benchmark.py"
    (tmp_path / "pkg.py").write_text("def gamma():\n    return 3\n", encoding="utf-8")
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
            "gamma",
            "--out-json",
            str(out),
            "--roi-enrich",
            "--roi-ground-truth-result",
            "partial",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    bench = json.loads(out.read_text(encoding="utf-8"))
    assert bench[0]["roi"]["scores"]["Q"] == 0.5


def test_nexus_benchmark_roi_ground_truth_file(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "extras" / "nexus_benchmark.py"
    (tmp_path / "pkg.py").write_text(
        "def a(): pass\ndef b(): pass\n", encoding="utf-8"
    )
    truth = tmp_path / "truth.json"
    truth.write_text(
        json.dumps(
            {
                "queries": {"a": "hit", "b": "partial"},
                "kind": "golden",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    roi_path = tmp_path / "roi.json"
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
            "a",
            "--query",
            "b",
            "--out-roi-json",
            str(roi_path),
            "--roi-ground-truth-file",
            str(truth),
            "--roi-ground-truth-result",
            "miss",
            "--roi-ground-truth-kind",
            "manual",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    roi = json.loads(roi_path.read_text(encoding="utf-8"))
    assert roi["runs"][0]["ground_truth"] == {"kind": "golden", "result": "hit"}
    assert roi["runs"][1]["ground_truth"] == {"kind": "golden", "result": "partial"}


def test_nexus_benchmark_roi_compare_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "extras" / "nexus_benchmark.py"
    old = {
        "schema_version": 1,
        "runs": [
            {
                "repo": "R",
                "query": "q",
                "scores": {"roi_score": 0.4, "Q": 0.5, "E": 1.0, "C_hat": 0.2},
                "metrics": {"nexus_output_tokens": 80},
            }
        ],
    }
    new = {
        "schema_version": 1,
        "runs": [
            {
                "repo": "R",
                "query": "q",
                "scores": {"roi_score": 0.9, "Q": 1.0, "E": 1.0, "C_hat": 0.1},
                "metrics": {"nexus_output_tokens": 40},
            }
        ],
    }
    old_p = tmp_path / "old.json"
    new_p = tmp_path / "new.json"
    old_p.write_text(json.dumps(old), encoding="utf-8")
    new_p.write_text(json.dumps(new), encoding="utf-8")
    cmp_out = tmp_path / "cmp.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--roi-compare",
            str(old_p),
            str(new_p),
            "--roi-compare-out",
            str(cmp_out),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(cmp_out.read_text(encoding="utf-8"))
    assert doc["kind"] == "roi_compare"
    assert len(doc["pairs"]) == 1
    assert doc["pairs"][0]["delta"]["roi_score"] == 0.5
