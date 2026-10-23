from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .ansi import BOLD, DIM, paint, supports_color
from .config import Config
from .metrics import compute_metrics
from .models import SEVERITY_ORDER
from .report import build_report, to_json, to_markdown, to_text, write_agent_packet
from .rules import RULES, Context, run_rules
from .scanner import scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pragmatic-audit",
        description="Audit a repository against The Pragmatic Programmer.",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository or directory to audit")
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument("--output", type=Path, help="write the report to a file")
    parser.add_argument(
        "--agent-packet",
        action="store_true",
        help="write pragmatic-audit.packet.json and .md for an agent review",
    )
    parser.add_argument("--config", type=Path, help="path to .pragmatic-audit.toml")
    parser.add_argument(
        "--min-confidence",
        choices=("low", "medium", "high"),
        help="drop findings below this confidence",
    )
    parser.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        help="exit 1 when a finding at this severity or higher exists",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="disable color and use stable output for CI",
    )
    parser.add_argument(
        "--include-history",
        action="store_true",
        help="enable opt-in git history rules",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="enable all opt-in rules",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI color",
    )
    parser.add_argument("--list-rules", action="store_true", help="list rules and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        _print_rules()
        return 0

    root = Path(args.path).expanduser().resolve()
    try:
        config_path = args.config.expanduser().resolve() if args.config else None
        config = Config.load(root, config_path)
        if args.min_confidence:
            config.min_confidence = args.min_confidence
        if args.fail_on:
            config.fail_on = args.fail_on
        if args.include_history or args.all:
            config.include_history = True
        config.validate()

        started = time.perf_counter()
        repo = scan(root, config)
        metrics = compute_metrics(repo, config.thresholds.duplicate_window)
        context = Context(repo=repo, config=config, metrics=metrics)
        findings, errors = run_rules(
            context, include_opt_in=config.include_history or args.all
        )
        report = build_report(
            repo,
            metrics,
            findings,
            elapsed=time.perf_counter() - started,
            errors=errors,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"pragmatic-audit: {exc}", file=sys.stderr)
        return 2

    color = not args.no_color and not args.ci and supports_color()

    if args.format == "json":
        rendered = to_json(report)
    elif args.format == "markdown":
        rendered = to_markdown(report)
    else:
        rendered = to_text(report, color=color)

    if args.output:
        output = args.output.expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8")
        print(f"Wrote {output}", file=sys.stderr)
    else:
        print(rendered)

    if args.agent_packet:
        json_path, md_path = write_agent_packet(report)
        print(f"Wrote {json_path}", file=sys.stderr)
        print(f"Wrote {md_path}", file=sys.stderr)

    if errors:
        return 3

    if config.fail_on != "none":
        limit = SEVERITY_ORDER[config.fail_on]
        if any(SEVERITY_ORDER.get(item.severity, 9) <= limit for item in report.findings):
            return 1
    return 0


def _print_rules() -> None:
    color = supports_color()
    print(paint("pragmatic-audit rule catalog", BOLD, color))
    print("")
    for rule in sorted(RULES.values(), key=lambda item: item.id):
        marker = " (opt-in)" if rule.opt_in else ""
        print(f"{paint(rule.id, BOLD, color)}{marker}  {rule.title}")
        print(f"  {paint(rule.description, DIM, color)}")
        print(f"  Tips: {', '.join(map(str, rule.tips))}  Severity: {rule.severity}  Confidence: {rule.confidence}")
        print(f"  Fix: {rule.fix}")
        print("")
