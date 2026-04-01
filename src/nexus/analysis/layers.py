from __future__ import annotations


def infer_layer(file_rel: str, qualified_name: str) -> str:
    """
    Grobe Schicht für typische App-Layouts (ohne Domainwissen).

    core | infrastructure | interface | test | support
    """
    p = file_rel.replace("\\", "/").lower()
    _ = qualified_name.lower()

    base = p.rsplit("/", 1)[-1]
    if base.startswith("test_") or base.endswith("_test.py"):
        return "test"
    if "/tests/" in p or p.startswith("tests/"):
        return "test"

    if any(
        x in p
        for x in (
            "/ui/",
            "/views/",
            "/frontend/",
            "/templates/",
            "/static/",
        )
    ):
        return "interface"
    if "gateway" in p or "/client/" in p or "/api/" in p or "/routes/" in p:
        return "interface"
    if "/cli/" in p or p.endswith("cli.py"):
        return "interface"

    if any(
        x in p
        for x in (
            "chronicle",
            "persist",
            "storage",
            "migration",
            "database",
            "db/",
        )
    ):
        return "infrastructure"

    if any(
        x in p
        for x in (
            "resolver",
            "runtime",
            "/services/",
            "/engine/",
            "/domain/",
            "/core/",
        )
    ):
        return "core"

    return "support"
