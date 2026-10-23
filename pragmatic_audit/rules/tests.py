from __future__ import annotations

import ast
import re
from dataclasses import replace

from ..models import Finding
from ._ast import call_name
from .registry import Context, Rule, make_finding, register

ASSERT_RE = re.compile(r"\b(?:assert|expect|should|t\.Error|require\.[A-Za-z])")
TEST_HYGIENE_PATTERNS = [
    (
        "wall-clock wait",
        re.compile(r"\b(?:time\.sleep|sleep|setTimeout)\s*\("),
        "medium",
    ),
    (
        "real network call",
        re.compile(r"\b(?:requests\.|httpx\.|fetch\(|axios\.|http://|https://)"),
        "medium",
    ),
    (
        "nondeterministic input",
        re.compile(r"\b(?:random\.|Math\.random|Date\.now|uuid4|time\.time)\b"),
        "low",
    ),
]
E2E_MARKERS = (
    "e2e",
    "end_to_end",
    "end-to-end",
    "integration",
    "smoke",
    "cypress",
    "playwright",
    "selenium",
    "puppeteer",
)


def check_tests(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    tests = ctx.repo.test_files
    if not tests:
        return [
            make_finding(
                RULE_TESTS,
                ".",
                0,
                "No test files were found.",
                evidence="Add tests for the behavior you expect to keep.",
            )
        ]

    if ctx.metrics.prod_loc > 100 and ctx.metrics.test_ratio < ctx.config.thresholds.test_ratio:
        findings.append(
            make_finding(
                replace(RULE_TESTS, severity="medium"),
                ".",
                0,
                f"Test code is {ctx.metrics.test_ratio:.0%} of production code "
                f"(threshold {ctx.config.thresholds.test_ratio:.0%}).",
                evidence="Test the behavior that would be expensive to break.",
            )
        )

    for item in tests:
        if item.language == "python":
            findings.extend(_python_assertions(ctx, item))
        elif item.language in {"javascript", "typescript"} and not ASSERT_RE.search(item.text):
            findings.append(
                make_finding(
                    replace(RULE_TESTS, severity="medium"),
                    item.rel,
                    1,
                    "Test file contains no assertion.",
                    evidence="Assert the observable behavior, not just that code ran.",
                )
            )
        if len(findings) >= 15:
            break
    return findings


def _python_assertions(ctx: Context, item) -> list[Finding]:
    tree = ctx.tree(item)
    if tree is None:
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test"):
            continue
        if _has_assertion(node):
            continue
        findings.append(
            make_finding(
                replace(RULE_TESTS, severity="medium"),
                item.rel,
                node.lineno,
                f"Test `{node.name}` has no assertion.",
                evidence="Assert the observable behavior, not just that code ran.",
            )
        )
    return findings


def _has_assertion(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.Call):
            name = call_name(child.func)
            if name.startswith("assert") or name in {"fail", "raises"}:
                return True
    return False



def check_test_hygiene(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.test_files:
        for label, pattern, severity in TEST_HYGIENE_PATTERNS:
            for number, line in enumerate(item.lines, start=1):
                stripped = line.strip()
                if stripped.startswith(("#", "//", "*")):
                    continue
                if not pattern.search(line):
                    continue
                findings.append(
                    make_finding(
                        replace(RULE_TEST_HYGIENE, severity=severity),
                        item.rel,
                        number,
                        f"Test uses a {label}; results can vary by machine or time.",
                        evidence="Inject a clock, fake the boundary, or use a deterministic fixture.",
                    )
                )
                break
        if len(findings) >= 12:
            break
    return findings


def check_e2e(ctx: Context) -> list[Finding]:
    tests = ctx.repo.test_files
    if not tests:
        return []
    for item in tests:
        haystack = f"{item.rel}\n{item.text}".lower()
        if any(marker in haystack for marker in E2E_MARKERS):
            return []
    return [
        make_finding(
            RULE_E2E,
            ".",
            0,
            "Tests look unit-only; no smoke or end-to-end path was found.",
            evidence="Add one thin path that proves the layers work together.",
        )
    ]


RULE_TESTS = register(
    Rule(
        id="PP-TESTS",
        title="Test your software, or your users will",
        principle="Design to test",
        tips=(66, 67, 70, 71),
        severity="high",
        confidence="high",
        description="Finds missing tests, thin test coverage, and assertion-free tests.",
        fix="Test the behavior you expect to keep; add a failing test before a fix.",
        check=check_tests,
    )
)

RULE_TEST_HYGIENE = register(
    Rule(
        id="PP-TEST-HYGIENE",
        title="Keep tests deterministic",
        principle="A good test is a good neighbor",
        tips=(57, 66),
        severity="medium",
        confidence="medium",
        description="Finds sleeps, real network calls, and nondeterministic input in tests.",
        fix="Inject time, fake the boundary, and use deterministic fixtures.",
        check=check_test_hygiene,
    )
)

RULE_E2E = register(
    Rule(
        id="PP-E2E",
        title="Use tracer bullets",
        principle="Build end-to-end",
        tips=(20, 68),
        severity="low",
        confidence="medium",
        description="Finds test suites with no smoke or end-to-end path.",
        fix="Add one thin path that exercises every architectural layer.",
        check=check_e2e,
    )
)
