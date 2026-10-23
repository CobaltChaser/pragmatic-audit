from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from ..models import Finding
from .registry import Context, Rule, make_finding, register

CI_PATHS = (
    ".github/workflows",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "Jenkinsfile",
    ".travis.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "cloudbuild.yaml",
    ".drone.yml",
)
AUTOMATION_FILES = (
    "Makefile",
    "makefile",
    "justfile",
    "Justfile",
    "Taskfile.yml",
    "Taskfile.yaml",
    "tox.ini",
    "noxfile.py",
    "Rakefile",
)
MANUAL_DEPLOY_RE = re.compile(
    r"(?i)\b(?:ssh|scp|rsync|ftp)\b|manual(?:ly)?\s+deploy"
)


def check_automation(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    if not _has_ci(ctx):
        findings.append(
            make_finding(
                replace(RULE_AUTOMATION, severity="medium"),
                ".",
                0,
                "No CI configuration was found.",
                evidence="Run tests and the audit on every push and pull request.",
            )
        )
    if not _has_automation(ctx):
        findings.append(
            make_finding(
                replace(RULE_AUTOMATION, severity="low"),
                ".",
                0,
                "No test, lint, or task automation was found.",
                evidence="Add a make target, task file, or package scripts that run the checks.",
            )
        )
    if ctx.repo.readme_text and MANUAL_DEPLOY_RE.search(ctx.repo.readme_text):
        findings.append(
            make_finding(
                replace(RULE_AUTOMATION, severity="low"),
                ctx.repo.readme_path.name if ctx.repo.readme_path else "README",
                1,
                "README contains manual deployment instructions.",
                evidence="Script the procedure and run it the same way every time.",
            )
        )
    return findings


def _has_ci(ctx: Context) -> bool:
    roots = [ctx.repo.root]
    if ctx.repo.git_root and ctx.repo.git_root != ctx.repo.root:
        roots.append(ctx.repo.git_root)
    for root in roots:
        for rel in CI_PATHS:
            path = root / rel
            if path.is_dir() and (
                any(path.glob("*.yml")) or any(path.glob("*.yaml"))
            ):
                return True
            if path.is_file():
                return True
    return False


def _has_automation(ctx: Context) -> bool:
    roots = [ctx.repo.root]
    if ctx.repo.git_root and ctx.repo.git_root != ctx.repo.root:
        roots.append(ctx.repo.git_root)
    for root in roots:
        for rel in AUTOMATION_FILES:
            if (root / rel).is_file():
                return True
        package = root / "package.json"
        if package.is_file():
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            if isinstance(scripts, dict) and any(
                key in scripts for key in ("test", "lint", "check", "ci")
            ):
                return True
    return False


RULE_AUTOMATION = register(
    Rule(
        id="PP-AUTOMATION",
        title="Automate everything you repeat",
        principle="Automate the routine",
        tips=(89, 90, 95),
        severity="medium",
        confidence="high",
        description="Finds missing CI, task automation, and manual deployment steps.",
        fix="Script the checks and run them the same way on every change.",
        check=check_automation,
    )
)
