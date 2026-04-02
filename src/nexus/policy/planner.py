from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from nexus.policy.profile import ProfileV2, ScopeTier, StageId

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RepoShape:
    repo_root: Path
    has_high_risk_dirs: bool
    has_tests: bool


@dataclass(frozen=True)
class ScopePick:
    tier: ScopeTier
    path: Path


@dataclass(frozen=True)
class IntentScores:
    scores: dict[str, float]

    def top_intent(self) -> tuple[str, float] | None:
        if not self.scores:
            return None
        k = max(self.scores.items(), key=lambda kv: kv[1])
        return k if k[1] > 0 else None


@dataclass(frozen=True)
class Plan:
    stage: StageId
    scope: ScopePick
    risk: RiskLevel
    intents: IntentScores
    k: int


def describe_repo_shape(repo_root: Path, profile: ProfileV2) -> RepoShape:
    root = repo_root.resolve()
    names = {p.name.lower() for p in root.iterdir() if p.is_dir()}
    high = any(n in names for n in (x.lower() for x in profile.risk.repo_shape_high_risk_dir_names))
    has_tests = any(n in names for n in ("tests", "test"))
    return RepoShape(repo_root=root, has_high_risk_dirs=high, has_tests=has_tests)


def _tokenize(q: str) -> list[str]:
    return [t for t in q.replace("\t", " ").split(" ") if t.strip()]


def assess_risk(query: str, *, repo_shape: RepoShape, profile: ProfileV2) -> RiskLevel:
    q = query.strip().lower()
    toks = _tokenize(q)
    noisy = {k.lower() for k in profile.risk.noisy_keywords}
    noisy_hits = sum(1 for t in toks if t in noisy) + sum(1 for k in noisy if k in q)

    looks_like_identifier = any(
        any(c.isupper() for c in t) or "_" in t or "." in t or (len(t) >= 10) for t in toks
    )

    if len(toks) <= 1:
        base: RiskLevel = "medium"
    elif noisy_hits >= 2 and not looks_like_identifier:
        base = "high"
    elif noisy_hits >= 1 and not looks_like_identifier:
        base = "medium"
    else:
        base = "low"

    # Repo-shape bump: monorepo-ish / frontend / generated often turns generic queries toxic.
    if repo_shape.has_high_risk_dirs and base != "high":
        return "high" if base == "medium" else "medium"
    return base


def classify_intents(query: str, profile: ProfileV2) -> IntentScores:
    q = query.strip().lower()
    scores: dict[str, float] = {}
    for name, cfg in profile.intents.items():
        hits = 0
        for kw in cfg.keywords:
            k = kw.strip().lower()
            if not k:
                continue
            if k in q:
                hits += 1
        # Soft confidence: saturates quickly; intent is a ranker feature, not an expander.
        scores[name] = min(1.0, hits * 0.35)
    return IntentScores(scores=scores)


def _pick_first_existing(repo_root: Path, dir_names: list[str]) -> Path | None:
    for dn in dir_names:
        p = (repo_root / dn).resolve()
        if p.is_dir():
            return p
    return None


def resolve_scope(repo_root: Path, *, profile: ProfileV2, allow_expand: bool) -> ScopePick:
    root = repo_root.resolve()

    core = _pick_first_existing(root, profile.scope.primary_core_dir_names)
    if core is not None:
        return ScopePick(tier="primary_core", path=core)

    adj = _pick_first_existing(root, profile.scope.primary_adjacent_dir_names)
    if adj is not None:
        return ScopePick(tier="primary_adjacent", path=adj)

    if allow_expand:
        tests = _pick_first_existing(root, profile.scope.secondary_tests_dir_names)
        if tests is not None:
            return ScopePick(tier="secondary_tests", path=tests)
        vendor = _pick_first_existing(root, profile.scope.secondary_vendor_dir_names)
        if vendor is not None:
            return ScopePick(tier="secondary_vendor", path=vendor)

    # Fallback: repo root, but policy still relies on NexusIgnore for large junk dirs.
    return ScopePick(tier="primary_adjacent", path=root)


def build_plan(
    *,
    repo_root: Path,
    query: str,
    stage: StageId,
    profile: ProfileV2,
) -> Plan:
    shape = describe_repo_shape(repo_root, profile)
    risk = assess_risk(query, repo_shape=shape, profile=profile)
    intents = classify_intents(query, profile)

    st = profile.stages[stage]
    k = st.k_high_risk if risk == "high" else st.k_default
    scope = resolve_scope(shape.repo_root, profile=profile, allow_expand=st.allow_scope_expand)

    return Plan(stage=stage, scope=scope, risk=risk, intents=intents, k=k)
