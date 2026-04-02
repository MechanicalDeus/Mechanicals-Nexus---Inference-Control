from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import IO, Any

from nexus.parsing.nexus_deny import _deny_file_paths
from nexus.parsing.nexus_ignore import NEXUS_IGNORE_NAME


def _truthy_env(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def repo_id(repo_root: Path) -> str:
    """
    Stable, redacted identifier for a repo root.

    We avoid printing absolute paths in control headers.
    """
    h = hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()
    return h[:12]


def collect_control_config(
    *,
    repo_root: Path,
    mode: str,
    include_tests: bool | None = None,
    transitive_depth: int | None = None,
    cache_dir: str | None = None,
) -> dict[str, Any]:
    rr = repo_root.resolve()
    ignore_present = (rr / NEXUS_IGNORE_NAME).is_file()
    deny_paths = _deny_file_paths(rr)
    deny_present = bool(deny_paths)

    return {
        "version": None,  # optionally filled by caller
        "repo_id": repo_id(rr),
        "mode": mode,
        "include_tests": include_tests,
        "transitive_depth": transitive_depth,
        "nexusignore": "present" if ignore_present else "absent",
        "nexusdeny": "present" if deny_present else "absent",
        "cache": "enabled" if (mode in {"persistent", "hybrid"}) else "disabled",
        "cache_dir": "<redacted>" if cache_dir else None,
    }


def emit_control_header(
    config: dict[str, Any],
    *,
    stream: IO[str] | None = None,
) -> None:
    """
    Emit a small, parseable control header.

    Important: keep this bounded and free of sensitive repo structure.
    Use stderr by default so JSON output on stdout remains valid.
    """
    s = stream or sys.stderr
    s.write("[NEXUS_CONFIG]\n")
    for k in (
        "version",
        "repo_id",
        "mode",
        "cache",
        "cache_dir",
        "include_tests",
        "transitive_depth",
        "nexusignore",
        "nexusdeny",
    ):
        v = config.get(k)
        if v is None:
            continue
        s.write(f"{k}={v}\n")
    if config.get("mode") in {"persistent", "hybrid"}:
        s.write("WARNING=cached_mode_is_security_sensitive\n")
    s.write("[/NEXUS_CONFIG]\n\n")


def control_header_enabled(flag_value: bool) -> bool:
    """
    Decide whether to emit the header.

    Priority:
    - CLI flag enables it
    - Env var can enable globally: NEXUS_CONTROL_HEADER=1
    """
    return bool(flag_value) or _truthy_env("NEXUS_CONTROL_HEADER")

