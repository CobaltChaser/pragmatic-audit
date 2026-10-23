from __future__ import annotations

import ast
import re

from ..models import Finding
from ._ast import function_nodes
from .registry import Context, Rule, make_finding, register

PY_SINGLE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
GENERIC_NAMES = {
    "data",
    "info",
    "tmp",
    "temp",
    "foo",
    "bar",
    "baz",
    "obj",
    "val",
    "value",
    "item",
    "thing",
    "stuff",
    "res",
    "result",
    "ret",
    "misc",
}
BOOLEAN_NAMES = {"flag", "status", "check", "condition"}
NAME_EXCEPTIONS = {
    "_",
    "self",
    "cls",
    "args",
    "kwargs",
    "i",
    "j",
    "k",
    "x",
    "y",
    "z",
}
JS_DECL_RE = re.compile(r"\b(?:let|const|var)\s+([A-Za-z_$][\w$]*)\s*=")
JS_FUNCTION_PARAMS_RE = re.compile(
    r"\b(?:function\s+[A-Za-z_$][\w$]*|(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?)"
    r"\s*\(([^)]*)\)"
)
CODE_START_RE = re.compile(
    r"^(?:def|class|function|const|let|var|if|elif|else|for|while|return|import|from|"
    r"await|async|public|private|protected|try|except|catch|switch|case|throw|print|"
    r"console\.|export|type|interface|struct|func|package|using|new)\b"
)
CODE_HINT_RE = re.compile(r"(?:=>|[A-Za-z_]\w*\s*[=(]|[;{}]\s*$)")
COMMENT_PREFIX = {
    "python": "#",
    "ruby": "#",
    "elixir": "#",
    "javascript": "//",
    "typescript": "//",
    "go": "//",
    "java": "//",
    "kotlin": "//",
    "csharp": "//",
    "swift": "//",
    "scala": "//",
    "rust": "//",
    "php": "//",
}


def check_complexity(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    thresholds = ctx.config.thresholds
    test_paths = {item.rel for item in ctx.repo.test_files}
    for function in ctx.metrics.functions:
        if function.path in test_paths:
            continue
        reasons = []
        if function.length > thresholds.long_function:
            reasons.append(f"{function.length} lines")
        if function.depth > thresholds.deep_nesting:
            reasons.append(f"nesting depth {function.depth}")
        if function.branches > 12:
            reasons.append(f"{function.branches} branches")
        if function.params > thresholds.max_params:
            reasons.append(f"{function.params} parameters")
        if not reasons:
            continue
        findings.append(
            make_finding(
                RULE_COMPLEXITY,
                function.path,
                function.line,
                f"`{function.name}` is hard to change: {', '.join(reasons)}.",
                evidence="Extract a named step or simplify the control flow.",
            )
        )
        if len(findings) >= 15:
            return findings

    for item in ctx.repo.prod_files:
        if item.is_test:
            continue
        nonblank = sum(1 for line in item.lines if line.strip())
        if nonblank > 500:
            findings.append(
                make_finding(
                    RULE_COMPLEXITY,
                    item.rel,
                    1,
                    f"File has {nonblank} non-blank lines.",
                    evidence="Split by responsibility and keep the public surface small.",
                )
            )
        if len(findings) >= 20:
            break
    return findings


def check_naming(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.prod_files:
        if item.is_test:
            continue
        if item.language == "python":
            findings.extend(_python_naming(ctx, item))
        elif item.language in {"javascript", "typescript"}:
            findings.extend(_js_naming(item))
        if len(findings) >= 15:
            return findings
    return findings


def _python_naming(ctx: Context, item) -> list[Finding]:
    findings: list[Finding] = []
    for node in function_nodes(ctx.tree(item)):
        if _bad_name(node.name):
            findings.append(
                make_finding(
                    RULE_NAMING,
                    item.rel,
                    node.lineno,
                    f"Function name `{node.name}` does not express intent.",
                    evidence="Rename it to say what it does.",
                )
            )
        for arg in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]:
            if _bad_name(arg.arg):
                findings.append(
                    make_finding(
                        RULE_NAMING,
                        item.rel,
                        arg.lineno,
                        f"Parameter name `{arg.arg}` does not express intent.",
                        evidence="Rename it to the domain concept it carries.",
                    )
                )
            elif arg.arg.lower() in BOOLEAN_NAMES:
                findings.append(
                    make_finding(
                        RULE_NAMING,
                        item.rel,
                        arg.lineno,
                        f"Boolean-like parameter `{arg.arg}` is vague.",
                        evidence="Use a name that states the condition, such as `is_active`.",
                    )
                )
    return findings


def _js_naming(item) -> list[Finding]:
    findings: list[Finding] = []
    for regex, group in ((JS_DECL_RE, 1), (JS_FUNCTION_PARAMS_RE, 1)):
        for match in regex.finditer(item.text):
            raw = match.group(group)
            names = [raw] if regex is JS_DECL_RE else [part.strip() for part in raw.split(",")]
            for name in names:
                name = name.split("=")[0].strip()
                if not name or not re.match(r"^[A-Za-z_$][\w$]*$", name):
                    continue
                if _bad_name(name):
                    line = item.text.count("\n", 0, match.start()) + 1
                    findings.append(
                        make_finding(
                            RULE_NAMING,
                            item.rel,
                            line,
                            f"Name `{name}` does not express intent.",
                            evidence="Rename it to the domain concept it carries.",
                        )
                    )
    return findings


def _bad_name(name: str) -> bool:
    if name in NAME_EXCEPTIONS or name.startswith("__"):
        return False
    if len(name) == 1 and name in PY_SINGLE:
        return True
    return name.lower() in GENERIC_NAMES or name.lower() in BOOLEAN_NAMES


def check_commented_code(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.files:
        prefix = COMMENT_PREFIX.get(item.language)
        if not prefix:
            continue
        group: list[tuple[int, str]] = []
        for number, line in enumerate(item.lines, start=1):
            stripped = line.strip()
            if stripped.startswith(prefix):
                content = stripped[len(prefix) :].strip()
                if _looks_like_code(content):
                    group.append((number, content))
                    continue
            if group:
                findings.extend(_comment_group(item, group))
                group = []
            if len(findings) >= 10:
                return findings
        if group:
            findings.extend(_comment_group(item, group))
    return findings[:10]


def _comment_group(item, group: list[tuple[int, str]]) -> list[Finding]:
    if len(group) < 2:
        return []
    first_line, first_text = group[0]
    return [
        make_finding(
            RULE_COMMENTS,
            item.rel,
            first_line,
            f"{len(group)} lines of commented-out code.",
            evidence=f"Delete it; version control already remembers. First line: {first_text[:80]}",
        )
    ]


def _looks_like_code(content: str) -> bool:
    lowered = content.lower()
    if any(token in lowered for token in ("todo", "fixme", "hack", "xxx")):
        return False
    if not content:
        return False
    return bool(CODE_START_RE.match(content) or CODE_HINT_RE.search(content))


RULE_COMPLEXITY = register(
    Rule(
        id="PP-COMPLEXITY",
        title="Refactor early, keep it simple",
        principle="Good design is easier to change",
        tips=(63, 65, 72),
        severity="medium",
        confidence="high",
        description="Finds long functions, deep nesting, many branches, and oversized files.",
        fix="Extract named steps or simplify the control flow before adding more.",
        check=check_complexity,
    )
)

RULE_NAMING = register(
    Rule(
        id="PP-NAMING",
        title="Name well; rename when needed",
        principle="Express intent",
        tips=(74,),
        severity="low",
        confidence="low",
        description="Finds single-letter and generic names that hide intent.",
        fix="Rename the value to the domain concept it carries.",
        check=check_naming,
    )
)

RULE_COMMENTS = register(
    Rule(
        id="PP-COMMENTS",
        title="Comment only what code cannot say",
        principle="Good code is its own documentation",
        tips=(13, 74),
        severity="low",
        confidence="medium",
        description="Finds blocks of commented-out code.",
        fix="Delete it; version control already remembers.",
        check=check_commented_code,
    )
)
