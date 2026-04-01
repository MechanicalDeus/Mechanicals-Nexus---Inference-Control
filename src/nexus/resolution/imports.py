from __future__ import annotations

import ast


def current_package(module_name: str) -> str:
    parts = module_name.split(".")
    if len(parts) <= 1:
        return ""
    return ".".join(parts[:-1])


def resolve_relative_base(
    module_name: str,
    level: int,
    relative: str | None,
) -> str:
    """
    Absolute import base for ``from ...module import`` (PEP 328 style).

    ``module_name`` is the dotted name of the file (e.g. ``pkg.sub.main``).
    """
    pkg = current_package(module_name)
    if not pkg and level > 0:
        return relative or ""
    parts = pkg.split(".") if pkg else []
    up = level - 1
    if up > len(parts):
        base_parts: list[str] = []
    else:
        base_parts = parts[:-up] if up else parts
    base = ".".join(base_parts)
    if relative:
        return f"{base}.{relative}" if base else relative
    return base


def _add_alias(targets: dict[str, list[str]], local: str, fqn: str) -> None:
    if not local or not fqn:
        return
    lst = targets.setdefault(local, [])
    if fqn not in lst:
        lst.append(fqn)


def extract_import_aliases(
    tree: ast.Module,
    module_hint: str,
) -> tuple[dict[str, list[str]], dict[str, str], list[str]]:
    """
    Returns (symbol_alias_targets, module_aliases, star_import_modules).

    *symbol_alias_targets*: local name -> list of fully qualified symbols (order preserved).
    *module_aliases*: local name -> dotted module path.
    *star_import_modules*: absolute module strings for ``from … import *``.
    """
    symbol_alias_targets: dict[str, list[str]] = {}
    module_aliases: dict[str, str] = {}
    star_import_modules: list[str] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                parts = alias.name.split(".")
                local = alias.asname or parts[0]
                module_aliases[local] = alias.name
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level and stmt.level > 0:
                base = resolve_relative_base(
                    module_hint,
                    stmt.level,
                    stmt.module,
                )
            else:
                base = stmt.module or ""
            for alias in stmt.names:
                if alias.name == "*":
                    if base:
                        star_import_modules.append(base)
                    continue
                local = alias.asname or alias.name
                if base:
                    _add_alias(symbol_alias_targets, local, f"{base}.{alias.name}")
                else:
                    _add_alias(symbol_alias_targets, local, alias.name)
    return symbol_alias_targets, module_aliases, star_import_modules


def _main_compare_is_name_main(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
        return False
    if len(node.comparators) != 1:
        return False
    left, right = node.left, node.comparators[0]
    if not isinstance(left, ast.Name) or left.id != "__name__":
        return False
    if isinstance(right, ast.Constant) and isinstance(right.value, str):
        return right.value == "__main__"
    return False


def extract_top_level_call_names(stmts: list[ast.stmt]) -> list[str]:
    out: list[str] = []
    for st in stmts:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            out.append(_call_to_string(st.value.func))
        elif isinstance(st, ast.If) and _main_compare_is_name_main(st.test):
            out.extend(extract_top_level_call_names(st.body))
    return out


def _call_to_string(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_to_string(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    if hasattr(ast, "unparse"):
        return ast.unparse(func)
    return "?"


def extract_entrypoint_call_names(tree: ast.Module) -> list[str]:
    """Raw callee strings from ``if __name__ == '__main__'`` bodies and top-level calls."""
    names: list[str] = []
    for st in tree.body:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            names.append(_call_to_string(st.value.func))
        elif isinstance(st, ast.If) and _main_compare_is_name_main(st.test):
            names.extend(extract_top_level_call_names(st.body))
    return names


def qualify_call_name(
    call_name: str,
    symbol_alias_targets: dict[str, list[str]],
    module_aliases: dict[str, str],
) -> list[str]:
    """
    Produce candidate fully qualified names using import tables (intra-repo).

    Preserves order; deduplicates. Multiple targets per local name (e.g. conflicting
    imports) are all returned.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def add(c: str) -> None:
        if c and c not in seen:
            seen.add(c)
            candidates.append(c)

    if call_name in symbol_alias_targets:
        for t in symbol_alias_targets[call_name]:
            add(t)
    if "." in call_name:
        head, _, tail = call_name.partition(".")
        if head in module_aliases:
            add(f"{module_aliases[head]}.{tail}")
        if head in symbol_alias_targets:
            for root in symbol_alias_targets[head]:
                add(f"{root}.{tail}")
    else:
        if call_name in module_aliases:
            add(module_aliases[call_name])
    return candidates
