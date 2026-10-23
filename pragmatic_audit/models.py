from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    principle: str
    tips: tuple[int, ...]
    severity: str
    confidence: str
    path: str
    line: int
    message: str
    fix: str
    evidence: str = ""

    def sort_key(self) -> tuple[int, int, str, str, int]:
        return (
            SEVERITY_ORDER.get(self.severity, 9),
            CONFIDENCE_ORDER.get(self.confidence, 9),
            self.rule_id,
            self.path,
            self.line,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule_id,
            "title": self.title,
            "principle": self.principle,
            "tips": list(self.tips),
            "severity": self.severity,
            "confidence": self.confidence,
            "path": self.path,
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
            "evidence": self.evidence,
        }


@dataclass
class SourceFile:
    path: Path
    rel: str
    language: str
    text: str
    lines: list[str]
    is_test: bool = False
    suppressions: dict[int, set[str]] = field(default_factory=dict)
    file_suppressions: set[str] = field(default_factory=set)

    def line(self, number: int) -> str:
        if 1 <= number <= len(self.lines):
            return self.lines[number - 1]
        return ""

    def suppressed(self, rule_id: str, line: int) -> bool:
        if "*" in self.file_suppressions or rule_id in self.file_suppressions:
            return True
        for candidate in (line, line - 1):
            rules = self.suppressions.get(candidate, set())
            if "*" in rules or rule_id in rules:
                return True
        return False


@dataclass
class Repo:
    root: Path
    files: list[SourceFile]
    is_git: bool
    git_root: Path | None
    tracked_files: list[str]
    readme_path: Path | None = None
    readme_text: str = ""

    def by_rel(self) -> dict[str, SourceFile]:
        return {item.rel: item for item in self.files}

    @property
    def prod_files(self) -> list[SourceFile]:
        return [item for item in self.files if not item.is_test]

    @property
    def test_files(self) -> list[SourceFile]:
        return [item for item in self.files if item.is_test]

    def file(self, rel: str) -> SourceFile | None:
        for item in self.files:
            if item.rel == rel:
                return item
        return None


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    name: str
    line: int
    length: int
    params: int
    branches: int
    depth: int
    language: str


@dataclass
class Metrics:
    loc: int
    prod_loc: int
    test_loc: int
    languages: dict[str, int]
    functions: list[FunctionMetric]
    imports: dict[str, set[str]]
    cycles: list[list[str]]
    class_bases: dict[str, set[str]]
    class_paths: dict[str, str]
    test_ratio: float


@dataclass
class ManualReviewItem:
    principle: str
    tips: tuple[int, ...]
    why: str
    questions: list[str]
    files: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "principle": self.principle,
            "tips": list(self.tips),
            "why": self.why,
            "questions": list(self.questions),
            "files": list(self.files),
        }


@dataclass
class AuditReport:
    tool: str
    version: str
    root: str
    generated_at: str
    elapsed_seconds: float
    files_scanned: int
    loc: int
    prod_loc: int
    test_loc: int
    languages: dict[str, int]
    findings: list[Finding]
    manual_review: list[ManualReviewItem]
    suggested_prompt: str
    errors: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        result = {"high": 0, "medium": 0, "low": 0}
        for finding in self.findings:
            result[finding.severity] = result.get(finding.severity, 0) + 1
        return result

    @property
    def signal(self) -> int:
        penalty = 0.0
        for finding in self.findings:
            if finding.severity == "high":
                penalty += 6.0
            elif finding.severity == "medium":
                penalty += 2.0
            else:
                penalty += 0.5
        return max(0, round(100 - min(85.0, penalty)))

    @property
    def rules_triggered(self) -> int:
        return len({finding.rule_id for finding in self.findings})

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "version": self.version,
            "root": self.root,
            "generated_at": self.generated_at,
            "elapsed_seconds": self.elapsed_seconds,
            "summary": {
                "files_scanned": self.files_scanned,
                "loc": self.loc,
                "prod_loc": self.prod_loc,
                "test_loc": self.test_loc,
                "languages": self.languages,
                "findings": self.counts,
                "signal": self.signal,
                "rules_triggered": self.rules_triggered,
            },
            "findings": [finding.to_dict() for finding in self.findings],
            "manual_review": [item.to_dict() for item in self.manual_review],
            "suggested_prompt": self.suggested_prompt,
            "errors": self.errors,
        }
