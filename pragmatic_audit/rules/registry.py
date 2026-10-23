from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Callable, Iterable

from ..config import Config
from ..models import CONFIDENCE_ORDER, Finding, Metrics, Repo, SourceFile

RuleCheck = Callable[["Context"], Iterable[Finding]]


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    principle: str
    tips: tuple[int, ...]
    severity: str
    confidence: str
    description: str
    fix: str
    check: RuleCheck
    opt_in: bool = False


@dataclass
class Context:
    repo: Repo
    config: Config
    metrics: Metrics
    _trees: dict[str, ast.AST | None] = field(default_factory=dict)

    def tree(self, item: SourceFile) -> ast.AST | None:
        if item.rel not in self._trees:
            if item.language != "python":
                self._trees[item.rel] = None
            else:
                try:
                    self._trees[item.rel] = ast.parse(item.text, filename=item.rel)
                except (SyntaxError, ValueError):
                    self._trees[item.rel] = None
        return self._trees[item.rel]

    @property
    def prod_files(self) -> list[SourceFile]:
        return list(self.repo.prod_files)

    @property
    def test_files(self) -> list[SourceFile]:
        return list(self.repo.test_files)

    def scope_files(self, include_tests: bool = False) -> list[SourceFile]:
        return list(self.repo.files if include_tests else self.repo.prod_files)


RULES: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    if rule.id in RULES:
        raise ValueError(f"duplicate rule id: {rule.id}")
    RULES[rule.id] = rule
    return rule


def make_finding(
    rule: Rule,
    path: str,
    line: int,
    message: str,
    evidence: str = "",
) -> Finding:
    return Finding(
        rule_id=rule.id,
        title=rule.title,
        principle=rule.principle,
        tips=rule.tips,
        severity=rule.severity,
        confidence=rule.confidence,
        path=path,
        line=line,
        message=message,
        fix=rule.fix,
        evidence=evidence,
    )


def run_rules(
    ctx: Context, include_opt_in: bool = False
) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    errors: list[str] = []
    for rule in sorted(RULES.values(), key=lambda item: item.id):
        if rule.opt_in and not include_opt_in:
            continue
        try:
            findings.extend(rule.check(ctx))
        except Exception as exc:  # noqa: BLE001 - one broken rule must not stop the audit
            errors.append(f"{rule.id}: {type(exc).__name__}: {exc}")
    return apply_filters(findings, ctx), errors


def apply_filters(findings: list[Finding], ctx: Context) -> list[Finding]:
    by_rel = {item.rel: item for item in ctx.repo.files}
    min_rank = CONFIDENCE_ORDER.get(ctx.config.min_confidence, 2)
    seen: set[tuple[str, str, int, str]] = set()
    result: list[Finding] = []
    for finding in findings:
        if ctx.config.is_ignored(finding.rule_id, finding.path):
            continue
        if CONFIDENCE_ORDER.get(finding.confidence, 9) > min_rank:
            continue
        item = by_rel.get(finding.path)
        if item is not None and item.suppressed(finding.rule_id, finding.line):
            continue
        key = (finding.rule_id, finding.path, finding.line, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    result.sort(key=lambda finding: finding.sort_key())
    return result
