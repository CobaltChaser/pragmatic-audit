from __future__ import annotations

import re
from dataclasses import replace

from ..gitinfo import run_git
from ..models import Finding
from .registry import Context, Rule, make_finding, register

VENDORS = {
    "Stripe": re.compile(r"\b(?:stripe)\b", re.IGNORECASE),
    "OpenAI": re.compile(r"\b(?:openai)\b", re.IGNORECASE),
    "Anthropic": re.compile(r"\b(?:anthropic)\b", re.IGNORECASE),
    "AWS": re.compile(r"\b(?:boto3|botocore)\b", re.IGNORECASE),
    "Firebase": re.compile(r"\b(?:firebase)\b", re.IGNORECASE),
    "Supabase": re.compile(r"\b(?:supabase)\b", re.IGNORECASE),
    "Twilio": re.compile(r"\b(?:twilio)\b", re.IGNORECASE),
    "SendGrid": re.compile(r"\b(?:sendgrid)\b", re.IGNORECASE),
    "Shopify": re.compile(r"\b(?:shopify)\b", re.IGNORECASE),
    "Salesforce": re.compile(r"\b(?:salesforce|simple_salesforce)\b", re.IGNORECASE),
    "HubSpot": re.compile(r"\b(?:hubspot)\b", re.IGNORECASE),
}
ADAPTER_RE = re.compile(r"(?:adapters?|gateway|provider|integration|ports?)[/._-]", re.IGNORECASE)
CONCURRENCY_RE = re.compile(
    r"\b(?:threading|asyncio|concurrent\.futures|multiprocessing|tokio|rayon)\b"
)
MODULE_STATE_RE = re.compile(r"^[A-Za-z_]\w*\s*=\s*(?:\[|\{|dict\(|list\(|set\()", re.MULTILINE)


def check_small_steps(ctx: Context) -> list[Finding]:
    if not ctx.repo.is_git:
        return []
    result = run_git(ctx.repo.root, "log", "-n", "50", "--numstat", "--format=%H")
    if result is None or result.returncode != 0:
        return []

    findings: list[Finding] = []
    commit = ""
    files = 0
    lines = 0
    for line in result.stdout.splitlines():
        if re.fullmatch(r"[0-9a-f]{40}", line.strip()):
            if commit and (files > 30 or lines > 1000):
                findings.append(_commit_finding(commit, files, lines))
            commit = line.strip()
            files = 0
            lines = 0
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            files += 1
            for value in parts[:2]:
                if value.isdigit():
                    lines += int(value)
        if len(findings) >= 3:
            return findings
    if commit and (files > 30 or lines > 1000):
        findings.append(_commit_finding(commit, files, lines))
    return findings[:3]


def _commit_finding(commit: str, files: int, lines: int) -> Finding:
    return make_finding(
        RULE_SMALL_STEPS,
        ".",
        0,
        f"Commit {commit[:8]} touched {files} files and {lines} lines.",
        evidence="Prefer smaller, reviewable steps that are easy to reverse.",
    )


def check_reversibility(ctx: Context) -> list[Finding]:
    hits: dict[str, list[str]] = {}
    for item in ctx.repo.prod_files:
        if item.is_test:
            continue
        for vendor, pattern in VENDORS.items():
            if pattern.search(item.text):
                hits.setdefault(vendor, []).append(item.rel)
    findings: list[Finding] = []
    for vendor, paths in sorted(hits.items()):
        if len(paths) < 3:
            continue
        if any(ADAPTER_RE.search(path) for path in paths):
            continue
        findings.append(
            make_finding(
                RULE_REVERSIBILITY,
                paths[0],
                1,
                f"`{vendor}` is used in {len(paths)} modules with no visible adapter boundary.",
                evidence="Isolate the vendor behind one interface so it can be replaced.",
            )
        )
    return findings[:5]


def check_shared_state(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.prod_files:
        if not CONCURRENCY_RE.search(item.text):
            continue
        match = MODULE_STATE_RE.search(item.text)
        if not match:
            continue
        line = item.text.count("\n", 0, match.start()) + 1
        findings.append(
            make_finding(
                RULE_SHARED_STATE,
                item.rel,
                line,
                "Mutable module state is used near concurrent code.",
                evidence="Pass state explicitly or keep it inside one owner.",
            )
        )
    return findings[:8]


RULE_SMALL_STEPS = register(
    Rule(
        id="PP-SMALL-STEPS",
        title="Take small steps",
        principle="Small reversible steps",
        tips=(42,),
        severity="low",
        confidence="low",
        description="Finds unusually large commits in recent history.",
        fix="Split the change into reviewable, reversible steps.",
        check=check_small_steps,
        opt_in=True,
    )
)

RULE_REVERSIBILITY = register(
    Rule(
        id="PP-REVERSIBILITY",
        title="Keep decisions reversible",
        principle="There are no final decisions",
        tips=(18,),
        severity="low",
        confidence="low",
        description="Finds vendor SDKs spread across modules without an adapter boundary.",
        fix="Put the vendor behind one interface you can replace.",
        check=check_reversibility,
        opt_in=True,
    )
)

RULE_SHARED_STATE = register(
    Rule(
        id="PP-SHARED-STATE",
        title="Shared state is incorrect state",
        principle="Avoid shared mutable state",
        tips=(57,),
        severity="medium",
        confidence="medium",
        description="Finds mutable module state in files that use concurrency.",
        fix="Give the state one owner or pass it explicitly.",
        check=check_shared_state,
        opt_in=True,
    )
)
