from __future__ import annotations

import fnmatch
from dataclasses import replace
from pathlib import Path

from ..models import Finding
from .registry import Context, Rule, make_finding, register

SENSITIVE_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
    ".aws/credentials",
)
SAFE_ENV = {".env.example", ".env.sample", ".env.template"}
MAX_TRACKED_BYTES = 5_000_000


def check_vcs(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    if not ctx.repo.is_git:
        findings.append(
            make_finding(
                RULE_VCS,
                ".",
                0,
                "The audit root is not inside a git repository.",
                evidence="Put the code under version control before changing it.",
            )
        )
        return findings

    if not _has_gitignore(ctx):
        findings.append(
            make_finding(
                replace(RULE_VCS, severity="medium"),
                ".",
                0,
                "No .gitignore file was found.",
                evidence="Ignore build output, local environments, and secrets.",
            )
        )

    for rel in ctx.repo.tracked_files:
        name = Path(rel).name
        if name in SAFE_ENV:
            continue
        if any(
            fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern)
            for pattern in SENSITIVE_PATTERNS
        ):
            findings.append(
                make_finding(
                    RULE_VCS,
                    rel,
                    1,
                    "Sensitive-looking file is tracked by git.",
                    evidence="Remove it from the index, rotate any exposed value, and ignore it.",
                )
            )

    for rel in ctx.repo.tracked_files:
        path = _tracked_path(ctx, rel)
        if path is None:
            continue
        try:
            if path.stat().st_size <= MAX_TRACKED_BYTES:
                continue
        except OSError:
            continue
        findings.append(
            make_finding(
                replace(RULE_VCS, severity="low"),
                rel,
                1,
                "Large file is tracked by git.",
                evidence="Store large assets outside the repository or use a release artifact.",
            )
        )
        if len(findings) >= 12:
            break
    return findings


def _has_gitignore(ctx: Context) -> bool:
    roots = [ctx.repo.root]
    if ctx.repo.git_root and ctx.repo.git_root != ctx.repo.root:
        roots.append(ctx.repo.git_root)
    return any((root / ".gitignore").is_file() for root in roots)


def _tracked_path(ctx: Context, rel: str) -> Path | None:
    for root in (ctx.repo.root, ctx.repo.git_root):
        if root is None:
            continue
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return None


RULE_VCS = register(
    Rule(
        id="PP-VCS",
        title="Always use version control",
        principle="Version control everything",
        tips=(28,),
        severity="high",
        confidence="high",
        description="Finds missing git, missing ignores, and tracked secrets or large files.",
        fix="Track the code, ignore local and sensitive files, and never commit secrets.",
        check=check_vcs,
    )
)
