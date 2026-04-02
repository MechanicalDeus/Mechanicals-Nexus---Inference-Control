"""Nexus: structural inference graph for Python codebases."""

import importlib.metadata

from nexus.core.graph import InferenceGraph
from nexus.scanner import attach, scan


def _distribution_version() -> str:
    try:
        return importlib.metadata.version("nexus-inference")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = _distribution_version()
__all__ = ["attach", "scan", "InferenceGraph", "__version__"]
