from __future__ import annotations

import ast
import hashlib
import re
from collections import defaultdict

from ..models import Finding, SourceFile
from .registry import Context, Rule, make_finding, register

COMMENT_RE = re.compile(r"(?://|#).*$")
IMPORT_PREFIXES = (
    "import ",
    "from ",
    "require(",
    "using ",
    "package ",
    "export ",
    "#include",
)
STRUCTURAL = {"{", "}", "(", ")", "[", "]", ");", "},", "};", "end"}


def check_dry(ctx: Context) -> list[Finding]:
    rule = RULE
    window = ctx.config.thresholds.duplicate_window
    buckets: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for item in ctx.repo.prod_files:
        if item.is_test:
            continue
        normalized = [
            (number, _normalize(line))
            for number, line in enumerate(item.lines, start=1)
        ]
        normalized = [(number, line) for number, line in normalized if line]
        for index in range(max(0, len(normalized) - window + 1)):
            chunk = normalized[index : index + window]
            if _boring([line for _, line in chunk]):
                continue
            key = hashlib.sha1("\n".join(line for _, line in chunk).encode()).hexdigest()
            buckets[key].append((item.rel, chunk[0][0]))

    findings: list[Finding] = []
    reported: set[tuple[str, int]] = set()
    for locations in buckets.values():
        unique = _dedupe_locations(locations, window)
        if len(unique) < 2:
            continue
        origin = unique[0]
        for location in unique[1:]:
            if location in reported:
                continue
            if len(findings) >= 8:
                break
            reported.add(location)
            findings.append(
                make_finding(
                    rule,
                    location[0],
                    location[1],
                    f"Duplicated {window}-line block; also at {origin[0]}:{origin[1]}.",
                    evidence="Extract the shared knowledge or call the existing implementation.",
                )
            )
        if len(findings) >= 8:
            break

    findings.extend(_duplicate_functions(ctx))
    return findings


def _duplicate_functions(ctx: Context) -> list[Finding]:
    groups: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for item in ctx.repo.prod_files:
        tree = ctx.tree(item)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if len(node.body) < 4:
                continue
            body = ast.Module(body=node.body, type_ignores=[])
            digest = hashlib.sha1(
                ast.dump(body, annotate_fields=False, include_attributes=False).encode()
            ).hexdigest()
            groups[digest].append((item.rel, node.lineno, node.name))

    findings: list[Finding] = []
    for functions in groups.values():
        unique = {(path, line): (path, line, name) for path, line, name in functions}
        if len(unique) < 2:
            continue
        origin = min(unique.values())
        for path, line, name in sorted(unique.values())[1:]:
            findings.append(
                make_finding(
                    RULE,
                    path,
                    line,
                    f"Function `{name}` duplicates `{origin[2]}` at {origin[0]}:{origin[1]}.",
                    evidence="Keep one authoritative implementation.",
                )
            )
            if len(findings) >= 6:
                return findings
    return findings


def _normalize(line: str) -> str:
    line = COMMENT_RE.sub("", line)
    return re.sub(r"\s+", " ", line).strip()


def _boring(lines: list[str]) -> bool:
    if all(line in STRUCTURAL for line in lines):
        return True
    return all(line.startswith(IMPORT_PREFIXES) for line in lines)


def _dedupe_locations(
    locations: list[tuple[str, int]], window: int
) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for path, line in sorted(locations):
        if any(path == other_path and abs(line - other_line) < window
               for other_path, other_line in result):
            continue
        result.append((path, line))
    return result


RULE = register(
    Rule(
        id="PP-DRY",
        title="Don't repeat yourself",
        principle="DRY",
        tips=(15,),
        severity="medium",
        confidence="medium",
        description="Finds repeated code blocks and duplicate function bodies.",
        fix="Keep one authoritative representation and reuse it.",
        check=check_dry,
    )
)
