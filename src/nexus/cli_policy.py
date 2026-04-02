from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nexus import attach
from nexus.output.llm_format import agent_symbol_lines_with_reasons
from nexus.policy.planner import build_plan
from nexus.policy.profile import ProfileV2, load_default_profile


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def _truncate_lines(lines: list[str], *, max_lines: int, max_chars: int) -> tuple[list[str], bool]:
    out: list[str] = []
    total = 0
    truncated = False
    for line in lines:
        if len(out) >= max_lines:
            truncated = True
            break
        # +1 for newline
        projected = total + len(line) + 1
        if projected > max_chars:
            truncated = True
            break
        out.append(line)
        total = projected
    return out, truncated


def _budget_footer(
    *, stage: str, k: int, scope: str, risk: str, est_chars: int, est_lines: int
) -> str:
    return (
        f"BUDGET: est_chars≈{est_chars}, lines≈{est_lines}, stage={stage}, K={k}, "
        f"scope={scope}, risk={risk}"
    )


def _noisy_suggestions(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    t = q.split()[0].strip().lower()
    if not t:
        return []
    return [
        f"{t} mutation flow",
        f"{t} persistence",
        f"why {t} changes",
    ]


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    parser = argparse.ArgumentParser(
        prog="nexus-policy",
        description="Inference-safe retrieval wrapper (scope-gating, risk, staged caps).",
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    parser.add_argument("--query", "-q", required=True, metavar="TEXT", help="User query text.")
    parser.add_argument(
        "--stage",
        choices=("auto", "1", "2", "3"),
        default="auto",
        help="Stage to run. auto runs stage 1, then (if empty) stage 2. Stage 3 is explicit only.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        metavar="PATH",
        help="Path to a policy profile YAML. Default: packaged safe-default-v2.",
    )
    parser.add_argument(
        "--mode",
        choices=("fresh", "persistent", "hybrid"),
        default="fresh",
        help="Inference mode (same as `nexus`).",
    )
    parser.add_argument(
        "--cache-dir", default=None, metavar="PATH", help="Cache dir for persistent/hybrid."
    )
    args = parser.parse_args(argv)

    if args.mode != "fresh" and not args.cache_dir:
        parser.error("--mode persistent/hybrid requires --cache-dir")

    repo_root = Path(args.path).resolve()
    profile = ProfileV2.load(Path(args.profile)) if args.profile else load_default_profile()
    q = args.query.strip()
    if not q:
        parser.error("--query / -q must be non-empty")

    stages = ["1", "2"] if args.stage == "auto" else [args.stage]
    if args.stage == "auto":
        # Never auto-run stage 3.
        pass

    last_plan = None
    last_lines: list[str] = []
    for st in stages:
        plan = build_plan(repo_root=repo_root, query=q, stage=st, profile=profile)  # type: ignore[arg-type]
        last_plan = plan

        g = attach(plan.scope.path, mode=args.mode, cache_dir=args.cache_dir)
        lines = agent_symbol_lines_with_reasons(
            g,
            query=q,
            annotate=profile.stages[st].annotate,
            max_symbols=plan.k,
            min_confidence=None,
        )
        if lines is None:
            # Special queries: keep behavior explicit. Users should call `nexus -q` directly.
            sys.stderr.write(
                "nexus-policy: special queries (impact/why/mutation chain/…) are not supported here; "
                "use `nexus -q` directly.\n"
            )
            return 2

        if lines:
            last_lines = lines
            break
        last_lines = lines

    if last_plan is None:
        return 2

    if last_plan.risk == "high":
        sugg = _noisy_suggestions(q)
        if sugg:
            sys.stderr.write(f"nexus-policy: high-noise query detected: {q!r}\n")
            sys.stderr.write("nexus-policy: try one of:\n")
            for s in sugg[:3]:
                sys.stderr.write(f"  - {s}\n")

    bounded, truncated = _truncate_lines(
        last_lines,
        max_lines=profile.limits.max_output_lines,
        max_chars=profile.limits.max_output_chars,
    )
    if bounded:
        sys.stdout.write("\n".join(bounded))
        sys.stdout.write("\n")

    # Guidance when empty or truncated.
    if not bounded:
        sys.stderr.write(
            "nexus-policy: no candidates in this stage under primary scope. "
            "Try a more specific identifier (e.g. ClassName.method) or run stage 2/3 explicitly.\n"
        )
    elif truncated:
        sys.stderr.write(
            "nexus-policy: output truncated by policy caps; tighten the query or use a narrower scope.\n"
        )

    if profile.stages[last_plan.stage].include_budget_footer:
        est_chars = sum(len(x) + 1 for x in bounded)
        footer = _budget_footer(
            stage=last_plan.stage,
            k=last_plan.k,
            scope=f"{last_plan.scope.tier}({last_plan.scope.path.as_posix()}) (restricted)",
            risk=last_plan.risk,
            est_chars=est_chars,
            est_lines=len(bounded),
        )
        sys.stdout.write("\n" + footer + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
