from __future__ import annotations

import ast
import posixpath
import re
from pathlib import Path

from .models import FunctionMetric, Metrics, Repo, SourceFile

JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]+?\s+from\s+)?|export\s+[^'"]+?\s+from\s+|require\s*\(\s*)['"]([^'"]+)['"]"""
)
JS_FUNCTION_PATTERNS = [
    re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{"),
    re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
        r"\(([^)]*)\)\s*=>\s*\{"
    ),
    re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?"
        r"function\s*\(([^)]*)\)\s*\{"
    ),
    re.compile(
        r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*"
        r"([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{\s*$",
        re.MULTILINE,
    ),
]
JS_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "with",
    "function",
    "return",
    "typeof",
    "new",
    "do",
    "else",
    "try",
}
JS_BRANCH_RE = re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?")
PY_CONTROL = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match)
PY_SCOPE = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def compute_metrics(repo: Repo, duplicate_window: int = 6) -> Metrics:
    del duplicate_window
    loc = sum(_loc(item) for item in repo.files)
    prod_loc = sum(_loc(item) for item in repo.prod_files)
    test_loc = sum(_loc(item) for item in repo.test_files)
    languages: dict[str, int] = {}
    for item in repo.files:
        languages[item.language] = languages.get(item.language, 0) + _loc(item)

    python_trees: dict[str, ast.AST] = {}
    for item in repo.files:
        if item.language == "python":
            tree = _parse_python(item)
            if tree is not None:
                python_trees[item.rel] = tree

    functions: list[FunctionMetric] = []
    class_bases: dict[str, set[str]] = {}
    class_paths: dict[str, str] = {}

    for item in repo.files:
        tree = python_trees.get(item.rel)
        if tree is not None:
            functions.extend(_python_functions(item, tree))
            bases, paths = _python_classes(item, tree)
            class_bases.update(bases)
            class_paths.update(paths)
        elif item.language in {"javascript", "typescript"}:
            functions.extend(_js_functions(item))

    imports: dict[str, set[str]] = {}
    module_map = _python_module_map(repo)
    for item in repo.files:
        if item.language == "python":
            tree = python_trees.get(item.rel)
            if tree is not None:
                imports[item.rel] = _python_imports(item, tree, module_map)
        elif item.language in {"javascript", "typescript"}:
            imports[item.rel] = _js_imports(item, repo)

    cycles = _strongly_connected(imports)
    test_ratio = (test_loc / prod_loc) if prod_loc else (1.0 if test_loc else 0.0)

    return Metrics(
        loc=loc,
        prod_loc=prod_loc,
        test_loc=test_loc,
        languages=dict(sorted(languages.items())),
        functions=functions,
        imports=imports,
        cycles=cycles,
        class_bases=class_bases,
        class_paths=class_paths,
        test_ratio=test_ratio,
    )


def parse_python_file(item: SourceFile) -> ast.AST | None:
    return _parse_python(item)


def _loc(item: SourceFile) -> int:
    return sum(1 for line in item.lines if line.strip())


def _parse_python(item: SourceFile) -> ast.AST | None:
    try:
        return ast.parse(item.text, filename=item.rel)
    except (SyntaxError, ValueError):
        return None


def _python_functions(item: SourceFile, tree: ast.AST) -> list[FunctionMetric]:
    result: list[FunctionMetric] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            result.append(
                FunctionMetric(
                    path=item.rel,
                    name=node.name,
                    line=node.lineno,
                    length=length,
                    params=_param_count(node.args),
                    branches=_branch_count(node),
                    depth=_control_depth(node),
                    language="python",
                )
            )
    return result


def _param_count(args: ast.arguments) -> int:
    count = (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )
    names = [arg.arg for arg in args.posonlyargs + args.args]
    if names and names[0] in {"self", "cls"}:
        count -= 1
    return max(0, count)


def _walk_scope(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, PY_SCOPE):
            continue
        yield child
        yield from _walk_scope(child)


def _branch_count(node: ast.AST) -> int:
    count = 0
    for child in _walk_scope(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match)):
            count += 1
        elif isinstance(child, ast.ExceptHandler):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += max(0, len(child.values) - 1)
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            count += len(child.generators)
        elif isinstance(child, ast.IfExp):
            count += 1
    return count


def _control_depth(node: ast.AST, current: int = 0) -> int:
    best = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, PY_SCOPE):
            continue
        step = 1 if isinstance(child, PY_CONTROL) else 0
        best = max(best, _control_depth(child, current + step))
    return best


def _python_classes(
    item: SourceFile, tree: ast.AST
) -> tuple[dict[str, set[str]], dict[str, str]]:
    bases: dict[str, set[str]] = {}
    paths: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        names = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                names.add(base.id)
            elif isinstance(base, ast.Attribute):
                names.add(base.attr)
        bases[node.name] = names
        paths.setdefault(node.name, item.rel)
    return bases, paths


def _python_module_map(repo: Repo) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in repo.files:
        if item.language != "python" or not item.rel.endswith(".py"):
            continue
        module = item.rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        if module:
            result[module] = item.rel
    return result


def _module_name(item: SourceFile) -> str:
    module = item.rel[:-3].replace("/", ".") if item.rel.endswith(".py") else item.rel
    if module.endswith(".__init__"):
        module = module[: -len(".__init__")]
    return module


def _python_imports(
    item: SourceFile, tree: ast.AST, module_map: dict[str, str]
) -> set[str]:
    current = _module_name(item)
    edges: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for candidate in (alias.name, alias.name.split(".")[0]):
                    target = module_map.get(candidate)
                    if target and target != item.rel:
                        edges.add(target)
        elif isinstance(node, ast.ImportFrom):
            candidates = _import_candidates(item, current, node)
            for candidate in candidates:
                target = module_map.get(candidate)
                if target and target != item.rel:
                    edges.add(target)
    return edges


def _import_candidates(
    item: SourceFile, current: str, node: ast.ImportFrom
) -> set[str]:
    candidates: set[str] = set()
    if node.level:
        is_package = item.rel.endswith("__init__.py")
        if is_package:
            package_parts = current.split(".") if current else []
        else:
            package_parts = current.rsplit(".", 1)[0].split(".") if "." in current else []
            if not package_parts:
                package_parts = []
        up = node.level - 1
        if up:
            package_parts = package_parts[:-up] if up <= len(package_parts) else []
        base = ".".join(part for part in package_parts if part)
        roots = []
        if node.module:
            roots.append(_join_module(base, node.module))
        else:
            roots.append(base)
    else:
        roots = [node.module] if node.module else []
    for root in roots:
        if not root:
            continue
        candidates.add(root)
        for alias in node.names:
            if alias.name != "*":
                candidates.add(f"{root}.{alias.name}")
    return candidates


def _join_module(left: str, right: str) -> str:
    return f"{left}.{right}" if left else right


def _js_imports(item: SourceFile, repo: Repo) -> set[str]:
    known = {entry.rel for entry in repo.files}
    edges: set[str] = set()
    base_dir = posixpath.dirname(item.rel)
    for spec in JS_IMPORT_RE.findall(item.text):
        if not spec.startswith("."):
            continue
        target = posixpath.normpath(posixpath.join(base_dir, spec))
        for candidate in _js_candidates(target):
            if candidate in known and candidate != item.rel:
                edges.add(candidate)
                break
    return edges


def _js_candidates(target: str) -> list[str]:
    if Path(target).suffix:
        return [target]
    suffixes = [
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        "/index.ts",
        "/index.tsx",
        "/index.js",
        "/index.jsx",
    ]
    return [target + suffix for suffix in suffixes]


def _strongly_connected(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, set())):
            if target not in graph:
                continue
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component: list[str] = []
            while True:
                current = stack.pop()
                on_stack.discard(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(components)


def _js_functions(item: SourceFile) -> list[FunctionMetric]:
    result: list[FunctionMetric] = []
    seen: set[int] = set()
    for pattern in JS_FUNCTION_PATTERNS:
        for match in pattern.finditer(item.text):
            name = match.group(1)
            if name in JS_KEYWORDS:
                continue
            brace = item.text.find("{", match.start())
            if brace < 0 or brace in seen:
                continue
            end = _match_brace(item.text, brace)
            if end < 0:
                continue
            seen.add(brace)
            body = item.text[brace : end + 1]
            start_line = item.text.count("\n", 0, match.start()) + 1
            end_line = item.text.count("\n", 0, end) + 1
            params = [part for part in match.group(2).split(",") if part.strip()]
            result.append(
                FunctionMetric(
                    path=item.rel,
                    name=name,
                    line=start_line,
                    length=end_line - start_line + 1,
                    params=len(params),
                    branches=len(JS_BRANCH_RE.findall(body)),
                    depth=_brace_depth(body),
                    language=item.language,
                )
            )
    return result


def _match_brace(text: str, start: int) -> int:
    depth = 0
    state = "code"
    escaped = False
    index = start
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                state = "line"
                index += 2
                continue
            if char == "/" and nxt == "*":
                state = "block"
                index += 2
                continue
            if char in {"'", '"', "`"}:
                state = char
                index += 1
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
        elif state == "line":
            if char == "\n":
                state = "code"
        elif state == "block":
            if char == "*" and nxt == "/":
                state = "code"
                index += 2
                continue
        else:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == state:
                state = "code"
        index += 1
    return -1


def _brace_depth(body: str) -> int:
    depth = 0
    best = 0
    for char in body:
        if char == "{":
            depth += 1
            best = max(best, depth)
        elif char == "}":
            depth = max(0, depth - 1)
    return best
