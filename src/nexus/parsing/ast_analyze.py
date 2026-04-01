from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any

from nexus.resolution.imports import (
    extract_entrypoint_call_names,
    extract_import_aliases,
)


def _unparse(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if hasattr(ast, "unparse"):
        return ast.unparse(node)
    return type(node).__name__


def _expr_to_access_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_to_access_string(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    if isinstance(node, ast.Subscript):
        val = _expr_to_access_string(node.value)
        if val and isinstance(node.slice, ast.Constant) and isinstance(
            node.slice.value, str
        ):
            return f"{val}.{node.slice.value}"
        if val and isinstance(node.slice, ast.Constant):
            return f"{val}[{node.slice.value!r}]"
        if val:
            return f"{val}[…]"
    return None


def _call_func_string(node: ast.AST, class_name: str | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "self" and class_name:
            return f"{class_name}.{node.attr}"
        base = _expr_to_access_string(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    if isinstance(node, ast.Subscript):
        return _unparse(node)
    return _unparse(node)


@dataclass
class RawSymbol:
    name: str
    kind: str
    line_start: int
    line_end: int
    qualified_name: str
    signature: str
    docstring: str | None
    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)
    calls: set[str] = field(default_factory=set)
    inherits_from: list[str] = field(default_factory=list)
    constructs: list[str] = field(default_factory=list)
    has_dynamic_call: bool = False
    has_local_assign: bool = False


@dataclass
class FileAnalysis:
    rel_path: str
    module_hint: str
    symbols: list[RawSymbol]
    import_names: set[str] = field(default_factory=set)
    symbol_alias_targets: dict[str, list[str]] = field(default_factory=dict)
    module_aliases: dict[str, str] = field(default_factory=dict)
    star_import_modules: list[str] = field(default_factory=list)
    entrypoint_calls: list[str] = field(default_factory=list)


class _Scope:
    __slots__ = ("qname_parts", "class_name")

    def __init__(
        self,
        qname_parts: tuple[str, ...],
        class_name: str | None = None,
    ) -> None:
        self.qname_parts = qname_parts
        self.class_name = class_name


class _Analyzer(ast.NodeVisitor):
    def __init__(self, module_hint: str) -> None:
        self.module_hint = module_hint
        self.symbols: list[RawSymbol] = []
        self._scope_stack: list[_Scope] = [_Scope((module_hint,))]
        self._import_names: set[str] = set()

    @property
    def _scope(self) -> _Scope:
        return self._scope_stack[-1]

    def _full_qualified(self, name: str) -> str:
        parts = self._scope.qname_parts + (name,)
        return ".".join(parts)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._import_names.add(alias.asname or alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self._import_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [_unparse(b) for b in node.bases]
        start = node.lineno
        end = getattr(node, "end_lineno", None) or node.lineno
        qn = self._full_qualified(node.name)
        self.symbols.append(
            RawSymbol(
                name=node.name,
                kind="class",
                line_start=start,
                line_end=end,
                qualified_name=qn,
                signature=f"class {node.name}",
                docstring=ast.get_docstring(node),
                inherits_from=bases,
            )
        )
        self._scope_stack.append(
            _Scope(self._scope.qname_parts + (node.name,), class_name=node.name)
        )
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(stmt, is_method=True)
            elif isinstance(stmt, ast.ClassDef):
                self.visit_ClassDef(stmt)
            else:
                self.visit(stmt)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if len(self._scope_stack) == 1:
            self._visit_function(node, is_method=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if len(self._scope_stack) == 1:
            self._visit_function(node, is_method=False)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        is_method: bool,
    ) -> None:
        class_name = self._scope.class_name if is_method else None
        start = node.lineno
        end = getattr(node, "end_lineno", None) or node.lineno
        qn = self._full_qualified(node.name)
        kind = "method" if is_method else "function"
        reads: set[str] = set()
        writes: set[str] = set()
        calls: set[str] = set()
        constructs: list[str] = []

        has_dynamic = False
        local_flag: list[bool] = [False]
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.Call):
                if not isinstance(child.func, (ast.Name, ast.Attribute)):
                    has_dynamic = True
                fname = _call_func_string(child.func, class_name)
                calls.add(fname)
                if isinstance(child.func, ast.Name):
                    cap = child.func.id[:1].isupper() if child.func.id else False
                    if child.func.id and cap:
                        constructs.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id in (
                        "type",
                        "super",
                    ):
                        pass

        for stmt in node.body:
            self._collect_assign_targets(stmt, writes, reads, local_flag)
            self._collect_reads(stmt, reads, class_name)

        self.symbols.append(
            RawSymbol(
                name=node.name,
                kind=kind,
                line_start=start,
                line_end=end,
                qualified_name=qn,
                signature=f"def {node.name}{_unparse(node.args)}",
                docstring=ast.get_docstring(node),
                reads=reads,
                writes=writes,
                calls=calls,
                constructs=list(dict.fromkeys(constructs)),
                has_dynamic_call=has_dynamic,
                has_local_assign=local_flag[0],
            )
        )

        self._scope_stack.append(
            _Scope(self._scope.qname_parts + (node.name,), class_name=class_name)
        )
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt)
            elif isinstance(stmt, ast.ClassDef):
                self.visit_ClassDef(stmt)
            else:
                self.visit(stmt)
        self._scope_stack.pop()

    def _visit_nested_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        class_name = self._scope.class_name
        start = node.lineno
        end = getattr(node, "end_lineno", None) or node.lineno
        qn = self._full_qualified(node.name)
        reads: set[str] = set()
        writes: set[str] = set()
        calls: set[str] = set()
        constructs: list[str] = []
        has_dynamic = False
        local_flag = [False]
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.Call):
                if not isinstance(child.func, (ast.Name, ast.Attribute)):
                    has_dynamic = True
                calls.add(_call_func_string(child.func, class_name))
        for stmt in node.body:
            self._collect_assign_targets(stmt, writes, reads, local_flag)
            self._collect_reads(stmt, reads, class_name)
        self.symbols.append(
            RawSymbol(
                name=node.name,
                kind="function",
                line_start=start,
                line_end=end,
                qualified_name=qn,
                signature=f"def {node.name}{_unparse(node.args)}",
                docstring=ast.get_docstring(node),
                reads=reads,
                writes=writes,
                calls=calls,
                constructs=list(dict.fromkeys(constructs)),
                has_dynamic_call=has_dynamic,
                has_local_assign=local_flag[0],
            )
        )
        self._scope_stack.append(
            _Scope(self._scope.qname_parts + (node.name,), class_name=class_name)
        )
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_nested_function(stmt)
            elif isinstance(stmt, ast.ClassDef):
                self.visit_ClassDef(stmt)
            else:
                self.visit(stmt)
        self._scope_stack.pop()

    def _collect_assign_targets(
        self,
        stmt: ast.stmt,
        writes: set[str],
        reads: set[str] | None,
        local_flag: list[bool],
    ) -> None:
        def mark_local_from_target(t: ast.AST) -> None:
            if isinstance(t, ast.Name):
                local_flag[0] = True
            elif isinstance(t, (ast.Tuple, ast.List)):
                for el in ast.walk(t):
                    if isinstance(el, ast.Name) and isinstance(el.ctx, ast.Store):
                        local_flag[0] = True

        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    local_flag[0] = True
                elif isinstance(t, (ast.Tuple, ast.List)):
                    mark_local_from_target(t)
                elif isinstance(t, (ast.Attribute, ast.Subscript)):
                    s = _expr_to_access_string(t)
                    if s:
                        writes.add(s)
                else:
                    mark_local_from_target(t)
        elif isinstance(stmt, ast.AnnAssign):
            if stmt.target:
                if isinstance(stmt.target, ast.Name):
                    local_flag[0] = True
                elif isinstance(stmt.target, (ast.Attribute, ast.Subscript)):
                    s = _expr_to_access_string(stmt.target)
                    if s:
                        writes.add(s)
                else:
                    mark_local_from_target(stmt.target)
        elif isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name):
                local_flag[0] = True
            elif isinstance(stmt.target, (ast.Attribute, ast.Subscript)):
                s = _expr_to_access_string(stmt.target)
                if s:
                    writes.add(s)
                    if reads is not None:
                        reads.add(s)
            else:
                mark_local_from_target(stmt.target)
        elif isinstance(stmt, ast.For):
            mark_local_from_target(stmt.target)

    def _collect_reads(
        self,
        node: ast.AST,
        reads: set[str],
        class_name: str | None,
    ) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.ctx, ast.Load):
                    xs = _expr_to_access_string(child)
                    if xs:
                        reads.add(xs)
            elif isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Load) and child.id not in (
                    "True",
                    "False",
                    "None",
                ):
                    reads.add(child.id)

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.ClassDef):
            self.visit_ClassDef(node)
            return None
        return super().visit(node)


def analyze_file(
    source: str,
    *,
    rel_path: str,
    module_hint: str,
) -> FileAnalysis:
    tree = ast.parse(source, filename=rel_path)
    an = _Analyzer(module_hint)
    for stmt in tree.body:
        an.visit(stmt)
    sat, module_aliases, star_import_modules = extract_import_aliases(tree, module_hint)
    entrypoint_calls = extract_entrypoint_call_names(tree)
    import_names = set(an._import_names) | set(sat) | set(module_aliases)
    return FileAnalysis(
        rel_path=rel_path,
        module_hint=module_hint,
        symbols=an.symbols,
        import_names=import_names,
        symbol_alias_targets=sat,
        module_aliases=module_aliases,
        star_import_modules=star_import_modules,
        entrypoint_calls=entrypoint_calls,
    )
