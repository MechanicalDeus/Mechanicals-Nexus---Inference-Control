"""Nexus: structural inference graph for Python codebases."""

from nexus.core.graph import InferenceGraph
from nexus.scanner import attach, scan

__all__ = ["attach", "scan", "InferenceGraph"]
__version__ = "0.1.0"
