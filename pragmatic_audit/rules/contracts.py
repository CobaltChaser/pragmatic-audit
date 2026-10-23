from __future__ import annotations

import ast
import re

from ..models import Finding
from ._ast import call_name
from .registry import Context, Rule, make_finding, register

JS_EMPTY_CATCH_RE = re.compile(
    r"catch\s*(?:\([^)]*\))?\s*\{\s*(?://[^\n]*\s*)?\}"
)
JS_EMPTY_PROMISE_RE = re.compile(
    r"\.catch\s*\(\s*(?:\([^)]*\)|\w+)\s*=>\s*\{\s*\}\s*\)"
)
RESOURCE_NAMES = {
    "open",
    "connect",
    "Popen",
    "Session",
    "socket",
    "urlopen",
    "create_connection",
    "TemporaryFile",
    "NamedTemporaryFile",
}
LOOSE_EQUALITY_RE = re.compile(r"(?<![=!<>])(?:==|!=)(?!=)")
JS_VAR_RE = re.compile(r"\bvar\s+([A-Za-z_$][\w$]*)")


def check_contracts(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.files:
        if item.language == "python":
            findings.extend(_python_contracts(ctx, item))
        elif item.language in {"javascript", "typescript"}:
            findings.extend(_js_contracts(item))
        if len(findings) >= 20:
            return findings
    return findings


def _python_contracts(ctx: Context, item) -> list[Finding]:
    tree = ctx.tree(item)
    if tree is None:
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        caught = _handler_name(node)
        passive = _passive_body(node.body)
        if not passive:
            continue
        if node.type is None or caught in {"Exception", "BaseException"}:
            findings.append(
                make_finding(
                    RULE_CONTRACTS,
                    item.rel,
                    node.lineno,
                    f"`except {caught or '*'}` swallows the error.",
                    evidence="Handle it, add context and re-raise, or crash early.",
                )
            )
        else:
            findings.append(
                make_finding(
                    RULE_CONTRACTS,
                    item.rel,
                    node.lineno,
                    f"`except {caught}` does nothing.",
                    evidence="Handle it or let it propagate.",
                )
            )
    return findings


def _handler_name(node: ast.ExceptHandler) -> str:
    if node.type is None:
        return ""
    if isinstance(node.type, ast.Name):
        return node.type.id
    if isinstance(node.type, ast.Attribute):
        return node.type.attr
    if isinstance(node.type, ast.Tuple):
        return ", ".join(_handler_name(ast.ExceptHandler(type=item)) for item in node.type.elts)
    return "exception"


def _passive_body(body: list[ast.stmt]) -> bool:
    if not body:
        return True
    for statement in body:
        if isinstance(statement, ast.Pass):
            continue
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if statement.value.value is Ellipsis:
                continue
        return False
    return True


def _js_contracts(item) -> list[Finding]:
    findings: list[Finding] = []
    for regex in (JS_EMPTY_CATCH_RE, JS_EMPTY_PROMISE_RE):
        for match in regex.finditer(item.text):
            line = item.text.count("\n", 0, match.start()) + 1
            findings.append(
                make_finding(
                    RULE_CONTRACTS,
                    item.rel,
                    line,
                    "Empty catch block swallows the error.",
                    evidence="Handle it, log with context and rethrow, or fail fast.",
                )
            )
    return findings


def check_resources(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.prod_files:
        if item.language != "python":
            continue
        tree = ctx.tree(item)
        if tree is None:
            continue
        parents = _parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node.func)
            if name not in RESOURCE_NAMES:
                continue
            if _inside_with(node, parents) or _owned_by_caller(node, parents):
                continue
            if _closed_in_finally(node, parents):
                continue
            findings.append(
                make_finding(
                    RULE_RESOURCES,
                    item.rel,
                    node.lineno,
                    f"Resource from `{name}()` is not released on every path.",
                    evidence="Use a context manager or `try/finally` that closes it.",
                )
            )
        if len(findings) >= 12:
            return findings
    return findings


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _inside_with(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.With):
            return True
    return False


def _owned_by_caller(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.Return):
            return True
        if isinstance(current, (ast.Call, ast.List, ast.Tuple, ast.Dict)):
            if current is not node:
                return True
    return False


def _closed_in_finally(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST | None = node
    while current is not None and current in parents:
        current = parents[current]
        if isinstance(current, ast.Try):
            for statement in current.finalbody:
                if _has_close_call(statement):
                    return True
    return False


def _has_close_call(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and call_name(child.func) in {
            "close",
            "release",
            "terminate",
            "kill",
            "disconnect",
            "quit",
            "cancel",
        }:
            return True
    return False



def check_coincidence(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.prod_files:
        if item.language == "python":
            findings.extend(_python_coincidence(ctx, item))
        elif item.language in {"javascript", "typescript"}:
            findings.extend(_js_coincidence(item))
        if len(findings) >= 20:
            return findings
    return findings


def _python_coincidence(ctx: Context, item) -> list[Finding]:
    tree = ctx.tree(item)
    if tree is None:
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = list(node.args.defaults) + [
                value for value in node.args.kw_defaults if value is not None
            ]
            for value in defaults:
                if _mutable_literal(value):
                    findings.append(
                        make_finding(
                            RULE_COINCIDENCE,
                            item.rel,
                            value.lineno,
                            f"Mutable default argument in `{node.name}`.",
                            evidence="Use `None` and create the value inside the function.",
                        )
                    )
        elif isinstance(node, ast.Compare):
            if _float_comparison(node):
                findings.append(
                    make_finding(
                        RULE_COINCIDENCE,
                        item.rel,
                        node.lineno,
                        "Float equality comparison.",
                        evidence="Use a tolerance or `math.isclose`.",
                    )
                )
            elif _identity_literal(node):
                findings.append(
                    make_finding(
                        RULE_COINCIDENCE,
                        item.rel,
                        node.lineno,
                        "Identity comparison against a literal.",
                        evidence="Use equality for values; reserve `is` for identity.",
                    )
                )
    return findings


def _mutable_literal(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Call):
        return call_name(node.func) in {"list", "dict", "set", "defaultdict", "deque"}
    return False


def _float_comparison(node: ast.Compare) -> bool:
    if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
        return False
    values = [node.left, *node.comparators]
    return any(
        isinstance(value, ast.Constant) and isinstance(value.value, float)
        or isinstance(value, ast.Call) and call_name(value.func) == "float"
        for value in values
    )


def _identity_literal(node: ast.Compare) -> bool:
    if not any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
        return False
    return any(
        isinstance(value, ast.Constant)
        and value.value is not None
        and not isinstance(value.value, bool)
        for value in node.comparators
    )


def _js_coincidence(item) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(item.lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "*")):
            continue
        if LOOSE_EQUALITY_RE.search(line) and "null" not in line and "undefined" not in line:
            findings.append(
                make_finding(
                    RULE_COINCIDENCE,
                    item.rel,
                    number,
                    "Loose equality allows surprising coercion.",
                    evidence="Use strict equality (`===` / `!==`).",
                )
            )
            continue
        if JS_VAR_RE.search(line) and not stripped.startswith(("//", "*")):
            findings.append(
                make_finding(
                    RULE_COINCIDENCE,
                    item.rel,
                    number,
                    "`var` is function-scoped and hoisted.",
                    evidence="Use `const` or `let`.",
                )
            )
    return findings


RULE_CONTRACTS = register(
    Rule(
        id="PP-CONTRACTS",
        title="Crash early, don't swallow errors",
        principle="Design with contracts",
        tips=(37, 38, 39),
        severity="high",
        confidence="high",
        description="Finds empty catch blocks and silently swallowed errors.",
        fix="Handle the error, add context and re-raise, or fail fast.",
        check=check_contracts,
    )
)

RULE_RESOURCES = register(
    Rule(
        id="PP-RESOURCES",
        title="Finish what you start",
        principle="Resource ownership",
        tips=(40, 41),
        severity="medium",
        confidence="medium",
        description="Finds resources allocated without a guaranteed release path.",
        fix="Use a context manager or `try/finally` that closes the resource.",
        check=check_resources,
    )
)

RULE_COINCIDENCE = register(
    Rule(
        id="PP-COINCIDENCE",
        title="Don't program by coincidence",
        principle="Rely on reliable things",
        tips=(62,),
        severity="medium",
        confidence="medium",
        description="Finds mutable defaults, float equality, and loose JavaScript equality.",
        fix="Make the behavior explicit and rely on documented semantics.",
        check=check_coincidence,
    )
)
