"""
Policy layer for "inference-safe retrieval".

This module is intentionally small and deterministic: it decides scope, risk,
intent confidences, and stage caps *before* calling the inference map, then
renders a bounded, names-only output with guidance.
"""
