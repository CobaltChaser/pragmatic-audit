from __future__ import annotations

import ast
import re

from ..models import Finding
from ._ast import call_name
from .registry import Context, Rule, make_finding, register

TRAIN_RE = re.compile(
    r"(?<![\w.$])([A-Za-z_$][\w$]*)((?:\.[A-Za-z_$][\w$]*(?:\([^()]*\))?){3,})"
)
TRAIN_ROOTS = {
    "os",
    "sys",
    "pathlib",
    "typing",
    "collections",
    "enum",
    "math",
    "json",
    "re",
    "logging",
    "datetime",
    "console",
    "pd",
    "np",
    "plt",
    "sns",
    "tf",
    "torch",
    "this",
}
TRAIN_FRAGMENTS = {"assert", "mock", "call_args", "method_calls", "toHaveBeenCalled"}
MUTABLE_CALLS = {"list", "dict", "set", "defaultdict", "deque", "Counter", "OrderedDict"}
JS_GLOBAL_RE = re.compile(
    r"^(?:let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:\[|\{)", re.MULTILINE
)
JS_STATIC_RE = re.compile(
    r"\bstatic\s+([A-Za-z_$][\w$]*)\s*=\s*(?:\[|\{)", re.MULTILINE
)
JS_CLASS_RE = re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)\s+extends\s+([A-Za-z_$][\w$]*)")


def check_globals(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.prod_files:
        if item.language == "python":
            findings.extend(_python_globals(ctx, item))
        elif item.language in {"javascript", "typescript"}:
            findings.extend(_js_globals(item))
    return findings[:12]


def _python_globals(ctx: Context, item) -> list[Finding]:
    tree = ctx.tree(item)
    if tree is None:
        return []
    findings: list[Finding] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if not _mutable_value(value):
                continue
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                name = target.id
                if name.isupper() or name.startswith("__"):
                    continue
                findings.append(
                    make_finding(
                        RULE_GLOBALS,
                        item.rel,
                        node.lineno,
                        f"Module-level mutable state `{name}`.",
                        evidence="Pass state explicitly or wrap it behind an API.",
                    )
                )
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            findings.append(
                make_finding(
                    RULE_GLOBALS,
                    item.rel,
                    node.lineno,
                    f"`global` statement mutates {', '.join(node.names)}.",
                    evidence="Return the new value or keep state in one owner.",
                )
            )
    return findings


def _mutable_value(node: ast.AST | None) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Call):
        name = call_name(node.func)
        return name in MUTABLE_CALLS
    return False



def _js_globals(item) -> list[Finding]:
    findings: list[Finding] = []
    for regex in (JS_GLOBAL_RE, JS_STATIC_RE):
        for match in regex.finditer(item.text):
            name = match.group(1)
            if name.isupper():
                continue
            line = item.text.count("\n", 0, match.start()) + 1
            findings.append(
                make_finding(
                    RULE_GLOBALS,
                    item.rel,
                    line,
                    f"Module-level mutable state `{name}`.",
                    evidence="Pass state explicitly or wrap it behind an API.",
                )
            )
    return findings


def check_orthogonality(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for cycle in ctx.metrics.cycles[:8]:
        findings.append(
            make_finding(
                RULE_ORTHO,
                cycle[0],
                1,
                "Import cycle: " + " -> ".join(cycle + [cycle[0]]),
                evidence="Break the cycle behind a narrower interface or move shared knowledge.",
            )
        )
    for path, targets in sorted(ctx.metrics.imports.items()):
        if len(targets) > 15:
            findings.append(
                make_finding(
                    RULE_ORTHO,
                    path,
                    1,
                    f"Module imports {len(targets)} internal modules.",
                    evidence="Split the module or introduce a boundary.",
                )
            )
        if len(findings) >= 12:
            break
    return findings


def check_trainwrecks(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.prod_files:
        if item.is_test or item.language not in {
            "python",
            "javascript",
            "typescript",
            "java",
            "kotlin",
            "csharp",
        }:
            continue
        for number, line in enumerate(item.lines, start=1):
            stripped = line.strip()
            if stripped.startswith(("#", "//", "*", "import ", "from ")):
                continue
            if "http://" in line or "https://" in line:
                continue
            for match in TRAIN_RE.finditer(line):
                root = match.group(1)
                chain = match.group(0)
                if root in TRAIN_ROOTS or any(part in chain for part in TRAIN_FRAGMENTS):
                    continue
                findings.append(
                    make_finding(
                        RULE_TRAINWRECK,
                        item.rel,
                        number,
                        f"Long call chain through `{root}`: {chain.strip()}.",
                        evidence="Ask the owner for the result instead of navigating its internals.",
                    )
                )
                break
            if len(findings) >= 12:
                return findings
    return findings


def check_inheritance(ctx: Context) -> list[Finding]:
    findings = _python_inheritance(ctx)
    findings.extend(_js_inheritance(ctx))
    return findings[:10]


def _python_inheritance(ctx: Context) -> list[Finding]:
    bases = ctx.metrics.class_bases
    cache: dict[str, int] = {}
    findings: list[Finding] = []
    for name, direct in sorted(bases.items()):
        if _skip_inheritance(name):
            continue
        depth = _class_depth(name, bases, cache, set())
        if depth <= 2:
            continue
        path = ctx.metrics.class_paths.get(name, ".")
        item = ctx.repo.file(path)
        line = _class_line(item, name) if item else 1
        findings.append(_inheritance_finding(name, depth, path, line))
    return findings


def _inheritance_finding(name: str, depth: int, path: str, line: int) -> Finding:
    return make_finding(
        RULE_INHERIT,
        path,
        line,
        f"`{name}` sits {depth} levels deep in an inheritance hierarchy.",
        evidence="Prefer composition, interfaces, or delegation.",
    )


def _class_depth(
    name: str, bases: dict[str, set[str]], cache: dict[str, int], seen: set[str]
) -> int:
    if name in cache:
        return cache[name]
    if name in seen:
        return 0
    parents = [base for base in bases.get(name, set()) if base in bases]
    if not parents:
        cache[name] = 1
        return 1
    depth = 1 + max(_class_depth(base, bases, cache, seen | {name}) for base in parents)
    cache[name] = depth
    return depth


def _skip_inheritance(name: str) -> bool:
    return name.endswith(
        ("Error", "Exception", "Mixin", "Protocol", "ABC", "Base", "Abstract")
    )


def _js_inheritance(ctx: Context) -> list[Finding]:
    bases: dict[str, set[str]] = {}
    paths: dict[str, tuple[str, int]] = {}
    for item in ctx.prod_files:
        if item.language not in {"javascript", "typescript"}:
            continue
        for match in JS_CLASS_RE.finditer(item.text):
            child, parent = match.group(1), match.group(2)
            bases.setdefault(child, set()).add(parent)
            paths.setdefault(
                child, (item.rel, item.text.count("\n", 0, match.start()) + 1)
            )
    cache: dict[str, int] = {}
    findings: list[Finding] = []
    for name in sorted(bases):
        depth = _class_depth(name, bases, cache, set())
        if depth <= 2:
            continue
        path, line = paths.get(name, (".", 1))
        findings.append(_inheritance_finding(name, depth, path, line))
    return findings


def _class_line(item, name: str) -> int:
    pattern = re.compile(rf"^\s*class\s+{re.escape(name)}\b", re.MULTILINE)
    match = pattern.search(item.text)
    if not match:
        return 1
    return item.text.count("\n", 0, match.start()) + 1


RULE_GLOBALS = register(
    Rule(
        id="PP-GLOBALS",
        title="Avoid global data",
        principle="Act locally",
        tips=(41, 47),
        severity="medium",
        confidence="medium",
        description="Finds module-level mutable state and global mutation.",
        fix="Pass state explicitly or wrap it behind a single owning API.",
        check=check_globals,
    )
)

RULE_ORTHO = register(
    Rule(
        id="PP-ORTHO",
        title="Keep components orthogonal",
        principle="Orthogonality",
        tips=(17, 44),
        severity="medium",
        confidence="high",
        description="Finds import cycles and modules with excessive internal fan-out.",
        fix="Break cycles and reduce the number of modules one change can touch.",
        check=check_orthogonality,
    )
)

RULE_TRAINWRECK = register(
    Rule(
        id="PP-TRAINWRECK",
        title="Don't chain method calls",
        principle="Decoupled code",
        tips=(46,),
        severity="low",
        confidence="low",
        description="Finds long attribute and method chains that reach through objects.",
        fix="Ask the owning object for the final value or behavior.",
        check=check_trainwrecks,
    )
)

RULE_INHERIT = register(
    Rule(
        id="PP-INHERIT",
        title="Don't pay inheritance tax",
        principle="Composition over inheritance",
        tips=(51, 52, 53),
        severity="medium",
        confidence="medium",
        description="Finds deep inheritance hierarchies.",
        fix="Use composition, interfaces, delegation, or mixins.",
        check=check_inheritance,
    )
)
