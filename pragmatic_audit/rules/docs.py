from __future__ import annotations

import re
from dataclasses import replace

from ..models import Finding
from .registry import Context, Rule, make_finding, register

TODO_RE = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
SKIP_PATTERNS = (
    re.compile(r"@pytest\.mark\.skip"),
    re.compile(r"@unittest\.skip"),
    re.compile(r"\bpytest\.skip\s*\("),
    re.compile(r"\b(?:it|test|describe)\.skip\s*\("),
    re.compile(r"\b(?:xit|xdescribe)\s*\("),
    re.compile(r"\bt\.Skip\s*\("),
    re.compile(r"@Ignore\b"),
)
IGNORE_PATTERNS = (
    re.compile(r"#\s*type:\s*ignore(?!\[)"),
    re.compile(r"#\s*noqa(?!\s*:)"),
    re.compile(r"@ts-ignore\b"),
    re.compile(r"@ts-expect-error\b"),
    re.compile(r"eslint-disable(?!-next-line\s+--|\s+--|\s+[a-z@])"),
)
README_HINTS = ("install", "usage", "quick start", "getting started", "run", "test")


def check_docs(ctx: Context) -> list[Finding]:
    if not ctx.repo.readme_path:
        return [
            make_finding(
                replace(RULE_DOCS, severity="medium"),
                ".",
                0,
                "No README was found.",
                evidence="Document what the project does, how to run it, and how to test it.",
            )
        ]
    findings: list[Finding] = []
    text = ctx.repo.readme_text
    if len(text.strip()) < 200:
        findings.append(
            make_finding(
                replace(RULE_DOCS, severity="low"),
                ctx.repo.readme_path.name,
                1,
                "README is very short.",
                evidence="Add purpose, setup, usage, and test instructions.",
            )
        )
    lowered = text.lower()
    if not any(hint in lowered for hint in README_HINTS):
        findings.append(
            make_finding(
                replace(RULE_DOCS, severity="low"),
                ctx.repo.readme_path.name,
                1,
                "README does not explain how to run or test the project.",
                evidence="Add a short quick start with copyable commands.",
            )
        )
    return findings


def check_broken_windows(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    total_todos = 0
    for item in ctx.repo.files:
        todos = sum(1 for line in item.lines if TODO_RE.search(line))
        total_todos += todos
        if todos > 3:
            findings.append(
                make_finding(
                    replace(RULE_BROKEN_WINDOWS, severity="low"),
                    item.rel,
                    1,
                    f"{todos} unresolved TODO/FIXME markers in one file.",
                    evidence="Fix the issue, turn it into a tracked task, or delete the marker.",
                )
            )
        for number, line in enumerate(item.lines, start=1):
            if "re.compile" in line or line.lstrip().startswith(("r\"", "r'")):
                continue
            for pattern in SKIP_PATTERNS:
                if not pattern.search(line):
                    continue
                severity = "low" if "reason" in line.lower() else "medium"
                findings.append(
                    make_finding(
                        replace(RULE_BROKEN_WINDOWS, severity=severity),
                        item.rel,
                        number,
                        "Test is skipped or ignored.",
                        evidence="Fix the test, or record why the skip is temporary.",
                    )
                )
                break
            for pattern in IGNORE_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        make_finding(
                            replace(RULE_BROKEN_WINDOWS, severity="low"),
                            item.rel,
                            number,
                            "Checker suppression has no explanation.",
                            evidence="Fix the underlying issue or explain the exception.",
                        )
                    )
                    break
            if len(findings) >= 20:
                return findings
    if total_todos > 20:
        findings.append(
            make_finding(
                replace(RULE_BROKEN_WINDOWS, severity="low"),
                ".",
                0,
                f"{total_todos} unresolved TODO/FIXME markers across the repository.",
                evidence="Reduce the backlog or move it into an issue tracker.",
            )
        )
    return findings


RULE_DOCS = register(
    Rule(
        id="PP-DOCS",
        title="Build documentation in",
        principle="Documentation lives with the code",
        tips=(11, 13),
        severity="medium",
        confidence="high",
        description="Finds missing or unhelpful README documentation.",
        fix="Document purpose, setup, usage, and tests next to the code.",
        check=check_docs,
    )
)

RULE_BROKEN_WINDOWS = register(
    Rule(
        id="PP-BROKEN-WINDOWS",
        title="Don't live with broken windows",
        principle="Fix bad code when you see it",
        tips=(5,),
        severity="medium",
        confidence="medium",
        description="Finds skipped tests, unexplained suppressions, and marker buildup.",
        fix="Fix it now, or record a bounded, visible plan to fix it.",
        check=check_broken_windows,
    )
)
