from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

StageId = Literal["1", "2", "3"]
ScopeTier = Literal[
    "primary_core",
    "primary_adjacent",
    "secondary_tests",
    "secondary_vendor",
]


@dataclass(frozen=True)
class StageConfig:
    names_only: bool
    annotate: bool
    k_default: int
    k_high_risk: int
    allow_scope_expand: bool
    include_budget_footer: bool
    include_control_header: bool


@dataclass(frozen=True)
class Limits:
    max_output_chars: int
    max_output_lines: int


@dataclass(frozen=True)
class ScopeConfig:
    tiers: list[ScopeTier]
    primary_core_dir_names: list[str]
    primary_adjacent_dir_names: list[str]
    secondary_tests_dir_names: list[str]
    secondary_vendor_dir_names: list[str]
    excluded_dir_names: list[str]


@dataclass(frozen=True)
class RiskConfig:
    noisy_keywords: list[str]
    repo_shape_high_risk_dir_names: list[str]


@dataclass(frozen=True)
class IntentConfig:
    keywords: list[str]


@dataclass(frozen=True)
class ProfileV2:
    version: int
    name: str
    limits: Limits
    stages: dict[StageId, StageConfig]
    scope: ScopeConfig
    risk: RiskConfig
    intents: dict[str, IntentConfig]

    @staticmethod
    def from_yaml_text(text: str) -> "ProfileV2":
        raw = yaml.safe_load(text)
        if not isinstance(raw, dict):
            raise ValueError("profile must be a mapping")

        version = int(raw.get("version") or 0)
        name = str(raw.get("name") or "")
        if version != 2:
            raise ValueError(f"unsupported profile version: {version}")
        if not name:
            raise ValueError("profile.name is required")

        limits_raw = raw.get("limits") or {}
        if not isinstance(limits_raw, dict):
            limits_raw = {}
        limits = Limits(
            max_output_chars=int(limits_raw.get("max_output_chars") or 6000),
            max_output_lines=int(limits_raw.get("max_output_lines") or 80),
        )

        stages_raw = raw.get("stages") or {}
        if not isinstance(stages_raw, dict):
            raise ValueError("profile.stages must be a mapping")
        stages: dict[StageId, StageConfig] = {}
        for sid in ("1", "2", "3"):
            s_raw = stages_raw.get(sid) or {}
            if not isinstance(s_raw, dict):
                s_raw = {}
            stages[sid] = StageConfig(
                names_only=bool(s_raw.get("names_only") if "names_only" in s_raw else True),
                annotate=bool(s_raw.get("annotate") if "annotate" in s_raw else True),
                k_default=int(s_raw.get("k_default") or (5 if sid == "1" else 10 if sid == "2" else 20)),
                k_high_risk=int(s_raw.get("k_high_risk") or (3 if sid == "1" else 6 if sid == "2" else 12)),
                allow_scope_expand=bool(s_raw.get("allow_scope_expand") if "allow_scope_expand" in s_raw else (sid == "3")),
                include_budget_footer=bool(
                    s_raw.get("include_budget_footer") if "include_budget_footer" in s_raw else True
                ),
                include_control_header=bool(
                    s_raw.get("include_control_header") if "include_control_header" in s_raw else False
                ),
            )

        scope_raw = raw.get("scope") or {}
        if not isinstance(scope_raw, dict):
            scope_raw = {}
        tiers = scope_raw.get("tiers") or ["primary_core", "primary_adjacent", "secondary_tests", "secondary_vendor"]
        if not isinstance(tiers, list) or not tiers:
            tiers = ["primary_core", "primary_adjacent", "secondary_tests", "secondary_vendor"]
        tiers_typed: list[ScopeTier] = []
        for t in tiers:
            if t in ("primary_core", "primary_adjacent", "secondary_tests", "secondary_vendor"):
                tiers_typed.append(t)  # type: ignore[arg-type]
        if not tiers_typed:
            tiers_typed = ["primary_core", "primary_adjacent", "secondary_tests", "secondary_vendor"]
        scope = ScopeConfig(
            tiers=tiers_typed,
            primary_core_dir_names=[str(x) for x in (scope_raw.get("primary_core_dir_names") or [])],
            primary_adjacent_dir_names=[str(x) for x in (scope_raw.get("primary_adjacent_dir_names") or [])],
            secondary_tests_dir_names=[str(x) for x in (scope_raw.get("secondary_tests_dir_names") or [])],
            secondary_vendor_dir_names=[str(x) for x in (scope_raw.get("secondary_vendor_dir_names") or [])],
            excluded_dir_names=[str(x) for x in (scope_raw.get("excluded_dir_names") or [])],
        )

        risk_raw = raw.get("risk") or {}
        if not isinstance(risk_raw, dict):
            risk_raw = {}
        risk = RiskConfig(
            noisy_keywords=[str(x) for x in (risk_raw.get("noisy_keywords") or [])],
            repo_shape_high_risk_dir_names=[
                str(x) for x in (risk_raw.get("repo_shape_high_risk_dir_names") or [])
            ],
        )

        intent_raw = raw.get("intent") or {}
        if not isinstance(intent_raw, dict):
            intent_raw = {}
        intents: dict[str, IntentConfig] = {}
        for k, v in intent_raw.items():
            if not isinstance(k, str):
                continue
            if not isinstance(v, dict):
                continue
            intents[k] = IntentConfig(keywords=[str(x) for x in (v.get("keywords") or [])])

        return ProfileV2(
            version=version,
            name=name,
            limits=limits,
            stages=stages,
            scope=scope,
            risk=risk,
            intents=intents,
        )

    @staticmethod
    def load(path: Path) -> "ProfileV2":
        return ProfileV2.from_yaml_text(path.read_text(encoding="utf-8"))


def default_profile_path() -> Path:
    return Path(__file__).with_name("default_profile.v2.yaml")


def load_default_profile() -> ProfileV2:
    return ProfileV2.load(default_profile_path())

