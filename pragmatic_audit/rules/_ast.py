from __future__ import annotations

import ast
from typing import TypeAlias

FunctionNode: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef


def function_nodes(tree: ast.AST | None) -> list[FunctionNode]:
    if tree is None:
        return []
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
