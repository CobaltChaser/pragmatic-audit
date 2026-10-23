from __future__ import annotations

import ast
import ipaddress
import re
from urllib.parse import urlparse

from ..models import Finding
from .registry import Context, Rule, make_finding, register

SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "assigned secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token)"
            r"\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
        ),
    ),
]
SECRET_PLACEHOLDERS = (
    "changeme",
    "change-me",
    "placeholder",
    "example",
    "dummy",
    "fake",
    "test",
    "your_",
    "your-",
    "xxxx",
    "****",
    "os.environ",
    "process.env",
    "${",
    "{{",
    "getenv",
)
URL_ASSIGN_RE = re.compile(
    r"(?i)\b[\w.]*(?:url|endpoint|host|base|api)[\w.]*\s*[:=]\s*['\"]"
    r"(https?://[^'\"]+)"
)
URL_CALL_RE = re.compile(
    r"(?i)(?:fetch|requests\.(?:get|post|put|delete|patch)|axios\.(?:get|post|put|delete)"
    r"|client\.(?:get|post|put|delete))\(\s*['\"](https?://[^'\"]+)"
)
ALLOWED_URL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "example.com",
    "example.org",
    "example.net",
    "schema.org",
    "json-schema.org",
    "www.w3.org",
    "w3.org",
}
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![\w.])(?:/(?:Users|home)/[A-Za-z0-9._-]+|[A-Za-z]:\\\\Users\\\\[^\\\s]+)"
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAGIC_COMPARE_RE = re.compile(
    r"(?:===|!==|==|!=|>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\b"
)
MAGIC_ALLOWED = {-1.0, 0.0, 1.0, 2.0, 10.0}


def check_config(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.repo.files:
        if item.language not in {"python", "javascript", "typescript", "go", "java", "ruby", "php", "rust"}:
            continue
        for number, line in enumerate(item.lines, start=1):
            stripped = line.strip()
            is_comment = stripped.startswith(("#", "//", "*", "/*"))
            for label, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if label == "assigned secret":
                    value = match.group(2).lower()
                    if any(token in value for token in SECRET_PLACEHOLDERS):
                        continue
                findings.append(
                    _config_finding(
                        item.rel,
                        number,
                        f"Possible hardcoded secret ({label}). Value redacted.",
                        "Move the value to an environment variable or secret store.",
                    )
                )
                break
            if is_comment:
                continue
            for pattern in (URL_ASSIGN_RE, URL_CALL_RE):
                for match in pattern.finditer(line):
                    if _allowed_url(match.group(1)):
                        continue
                    findings.append(
                        _config_finding(
                            item.rel,
                            number,
                            "Environment-specific URL is hardcoded.",
                            "Move the base URL and hosts into configuration.",
                        )
                    )
                    break
            if ABSOLUTE_PATH_RE.search(line):
                findings.append(
                    _config_finding(
                        item.rel,
                        number,
                        "User-specific absolute path is hardcoded.",
                        "Resolve paths from configuration or the project root.",
                    )
                )
            for match in IP_RE.finditer(line):
                value = match.group(0)
                if _allowed_ip(value):
                    continue
                findings.append(
                    _config_finding(
                        item.rel,
                        number,
                        "Hardcoded IP address.",
                        "Move the host into configuration.",
                    )
                )
                break
            if len(findings) >= 40:
                return findings
    return findings


def _config_finding(path: str, line: int, message: str, evidence: str) -> Finding:
    return make_finding(RULE, path, line, message, evidence=evidence)


def check_magic_numbers(ctx: Context) -> list[Finding]:
    rule = RULE_MAGIC
    findings: list[Finding] = []
    for item in ctx.scope_files(include_tests=False):
        if item.is_test:
            continue
        hits = _python_magic(ctx, item) if item.language == "python" else _regex_magic(item)
        for line in hits[:3]:
            findings.append(
                make_finding(
                    rule,
                    item.rel,
                    line,
                    "Numeric literal is used as policy or a threshold.",
                    evidence="Name the value as a constant or move it into configuration.",
                )
            )
    return findings


def _python_magic(ctx: Context, item) -> list[int]:
    tree = ctx.tree(item)
    if tree is None:
        return []
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for value in [node.left, *node.comparators]:
            if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)):
                if not isinstance(value.value, bool) and float(value.value) not in MAGIC_ALLOWED:
                    lines.append(value.lineno)
    return sorted(set(lines))


def _regex_magic(item) -> list[int]:
    lines: list[int] = []
    for number, line in enumerate(item.lines, start=1):
        if line.lstrip().startswith(("#", "//", "*")):
            continue
        for match in MAGIC_COMPARE_RE.finditer(line):
            value = float(match.group(1))
            if value not in MAGIC_ALLOWED:
                lines.append(number)
                break
    return lines


def _allowed_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return True
    if host in ALLOWED_URL_HOSTS:
        return True
    return host.endswith(".localhost")


def _allowed_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True
    return address.is_loopback or address.is_unspecified


RULE = register(
    Rule(
        id="PP-CONFIG",
        title="Parameterize configuration",
        principle="External configuration",
        tips=(55,),
        severity="high",
        confidence="medium",
        description="Finds hardcoded secrets, environment-specific URLs, paths, and IPs.",
        fix="Move environment-specific values into configuration or a secret store.",
        check=check_config,
    )
)

RULE_MAGIC = register(
    Rule(
        id="PP-MAGIC",
        title="Name policy values",
        principle="Policy is metadata",
        tips=(79,),
        severity="low",
        confidence="low",
        description="Finds unexplained numeric thresholds in comparisons.",
        fix="Name the value and keep policy outside the branching logic.",
        check=check_magic_numbers,
    )
)
