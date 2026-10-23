#!/usr/bin/env python3
"""Regenerate example reports and SVG previews from real CLI output."""

from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = ROOT / "examples" / "bad-repo"
GOOD = ROOT / "examples" / "good-repo"
ASSETS = ROOT / "docs" / "assets"
REPORT = ROOT / "examples" / "report.md"

BG = "#0B1020"
CHROME = "#131D32"
PANEL = "#0E1728"
BORDER = "#26334D"
TEXT = "#D7E0EE"
DIM = "#7C8AA5"
ACCENT = "#F2B84B"
TEAL = "#7DD3C7"
RED = "#F87171"
GREEN = "#34D399"
BLUE = "#93C5FD"
PAPER = "#F7F4EB"
INK = "#152033"
MUTED = "#6B7280"

MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def run(arguments: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pragmatic_audit", *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise SystemExit(
            f"pragmatic-audit failed ({result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def load_report() -> dict:
    output = run([str(BAD), "--format", "json", "--no-color"], cwd=ROOT)
    return json.loads(output)


def collect_packet() -> str:
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        run([str(BAD), "--agent-packet", "--format", "json", "--no-color"], cwd=work, env=env)
        packet = (work / "pragmatic-audit.packet.md").read_text(encoding="utf-8")
        return packet.replace(str(BAD), "examples/bad-repo")


def write_report() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmatic_audit",
            str(BAD),
            "--format",
            "markdown",
            "--output",
            str(REPORT),
            "--no-color",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise SystemExit(result.stderr)


def terminal_lines(report: dict) -> list[list[tuple[str, str, bool]]]:
    summary = report["summary"]
    counts = summary["findings"]
    lines: list[list[tuple[str, str, bool]]] = []
    lines.append([("$ ", DIM, False), ("pragmatic-audit examples/bad-repo", TEXT, False)])
    lines.append([])
    lines.append([(f"pragmatic-audit {report['version']}", TEXT, True)])
    lines.append(
        [
            (
                f"Scanned {summary['files_scanned']} files, {summary['loc']} LOC "
                f"({summary['prod_loc']} prod, {summary['test_loc']} test) "
                f"in {report['elapsed_seconds']:.2f}s",
                DIM,
                False,
            )
        ]
    )
    lines.append([("Root: examples/bad-repo", DIM, False)])
    lines.append([])
    lines.append([(f"Signal {summary['signal']}/100  ", TEXT, True), ("heuristic, not a grade", DIM, False)])
    lines.append(
        [
            ("high ", RED, False),
            (str(counts["high"]), TEXT, True),
            ("   medium ", ACCENT, False),
            (str(counts["medium"]), TEXT, True),
            ("   low ", TEAL, False),
            (str(counts["low"]), TEXT, True),
        ]
    )
    lines.append([])
    lines.append([("Top fixes", TEXT, True)])
    for index, finding in enumerate(report["findings"][:4], start=1):
        color = {"high": RED, "medium": ACCENT, "low": TEAL}.get(finding["severity"], TEXT)
        location = finding["path"] if finding["line"] <= 0 else f"{finding['path']}:{finding['line']}"
        lines.append(
            [
                (f"  {index}. ", DIM, False),
                (finding["severity"].upper().ljust(6), color, True),
                (f"{finding['rule']}  ", TEAL, False),
                (location, DIM, False),
            ]
        )
        lines.append([(f"     {shorten(finding['message'], 84)}", TEXT, False)])
    lines.append([])
    lines.append([("Manual review queue", TEXT, True)])
    for item in report["manual_review"][:4]:
        tips = ", ".join(str(tip) for tip in item["tips"])
        lines.append([(f"  {item['principle']}", TEAL, False), (f"  tips {tips}", DIM, False)])
    lines.append([])
    lines.append([("Findings are hypotheses. Read the code before changing it.", DIM, False)])
    return lines


def packet_lines(packet: str) -> list[list[tuple[str, str, bool]]]:
    lines: list[list[tuple[str, str, bool]]] = [
        [("$ ", DIM, False), ("pragmatic-audit examples/bad-repo --agent-packet", TEXT, False)],
        [("Wrote pragmatic-audit.packet.json", DIM, False)],
        [("Wrote pragmatic-audit.packet.md", DIM, False)],
        [],
    ]
    used = 0
    for raw in packet.splitlines():
        if not raw.strip():
            if lines and lines[-1]:
                lines.append([])
            continue
        color = TEXT
        bold = False
        text = raw
        if text.startswith("# "):
            text = text[2:]
            color = ACCENT
            bold = True
        elif text.startswith("## "):
            text = text[3:]
            color = TEAL
            bold = True
        elif text.startswith("- **"):
            text = text.replace("**", "")
        elif text.startswith("  "):
            color = DIM
        lines.append([(shorten(text, 88), color, bold)])
        used += 1
        if used >= 20:
            break
    return lines[:24]


def document_preview(report: dict) -> str:
    summary = report["summary"]
    counts = summary["findings"]
    width, height = 1200, 760
    out = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">',
        "<title>Pragmatic audit report preview</title>",
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
        f'<rect x="0" y="0" width="{width}" height="14" fill="{ACCENT}"/>',
        f'<rect x="110" y="58" width="980" height="646" rx="18" fill="#FFFDF8" stroke="#DBD5C7"/>',
        f'<text x="156" y="120" fill="{MUTED}" font-family="{MONO}" font-size="12" letter-spacing="2.8">PRAGMATIC AUDIT REPORT</text>',
        f'<text x="156" y="168" fill="{INK}" font-family="{SANS}" font-size="40" font-weight="700">pragmatic-audit</text>',
        f'<text x="156" y="200" fill="{MUTED}" font-family="{MONO}" font-size="14">examples/bad-repo</text>',
        f'<text x="958" y="168" text-anchor="end" fill="{ACCENT}" font-family="{SANS}" font-size="44" font-weight="700">{summary["signal"]}</text>',
        f'<text x="958" y="190" text-anchor="end" fill="{MUTED}" font-family="{MONO}" font-size="11">SIGNAL / 100</text>',
    ]
    cards = [
        ("FILES", str(summary["files_scanned"])),
        ("PROD LOC", str(summary["prod_loc"])),
        ("TEST LOC", str(summary["test_loc"])),
        ("HIGH", str(counts["high"])),
        ("MEDIUM", str(counts["medium"])),
        ("LOW", str(counts["low"])),
    ]
    x = 156
    for label, value in cards:
        out.append(f'<rect x="{x}" y="226" width="142" height="76" rx="10" fill="#F4F0E5"/>')
        out.append(f'<text x="{x + 14}" y="252" fill="{MUTED}" font-family="{MONO}" font-size="10" letter-spacing="1.6">{label}</text>')
        out.append(f'<text x="{x + 14}" y="284" fill="{INK}" font-family="{SANS}" font-size="25" font-weight="700">{value}</text>')
        x += 154
    out.append(f'<line x1="156" y1="330" x2="1044" y2="330" stroke="#E2DCCF"/>')
    out.append(f'<text x="156" y="366" fill="{INK}" font-family="{SANS}" font-size="20" font-weight="700">Top fixes</text>')
    y = 398
    for index, finding in enumerate(report["findings"][:5], start=1):
        color = {"high": RED, "medium": "#C98A16", "low": "#0F766E"}.get(finding["severity"], INK)
        location = finding["path"] if finding["line"] <= 0 else f"{finding['path']}:{finding['line']}"
        out.append(f'<text x="156" y="{y}" fill="{MUTED}" font-family="{MONO}" font-size="13">{index}.</text>')
        out.append(f'<text x="184" y="{y}" fill="{color}" font-family="{MONO}" font-size="11" font-weight="700">{finding["severity"].upper()}</text>')
        out.append(f'<text x="252" y="{y}" fill="#0F766E" font-family="{MONO}" font-size="12">{html.escape(finding["rule"])}</text>')
        out.append(f'<text x="344" y="{y}" fill="{MUTED}" font-family="{MONO}" font-size="12">{html.escape(location)}</text>')
        out.append(f'<text x="156" y="{y + 20}" fill="{INK}" font-family="{SANS}" font-size="14">{html.escape(shorten(finding["message"], 82))}</text>')
        out.append(f'<text x="156" y="{y + 38}" fill="{MUTED}" font-family="{SANS}" font-size="12">Fix: {html.escape(shorten(finding["fix"], 86))}</text>')
        y += 62
    out.append(f'<text x="156" y="668" fill="{MUTED}" font-family="{MONO}" font-size="11">Findings are hypotheses. Read the code before changing it.</text>')
    out.append("</svg>")
    return "\n".join(out)


def terminal_svg(lines: list[list[tuple[str, str, bool]]], title: str) -> str:
    width, height = 1200, 760
    line_height = 25
    font_size = 14
    start_y = 132
    out = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">',
        f"<title>{html.escape(title)}</title>",
        f'<rect width="{width}" height="{height}" fill="{BG}"/>',
        f'<rect x="34" y="34" width="1132" height="692" rx="16" fill="{PANEL}" stroke="{BORDER}"/>',
        f'<rect x="34" y="34" width="1132" height="52" rx="16" fill="{CHROME}"/>',
        f'<rect x="34" y="70" width="1132" height="16" fill="{CHROME}"/>',
        f'<circle cx="64" cy="60" r="6" fill="{RED}"/>',
        f'<circle cx="86" cy="60" r="6" fill="{ACCENT}"/>',
        f'<circle cx="108" cy="60" r="6" fill="{GREEN}"/>',
        f'<text x="1136" y="65" text-anchor="end" fill="{DIM}" font-family="{MONO}" font-size="12">pragmatic-audit</text>',
    ]
    y = start_y
    for line in lines:
        segments = line or [("", TEXT, False)]
        parts = []
        for text, color, bold in segments:
            weight = ' font-weight="700"' if bold else ""
            parts.append(
                f'<tspan fill="{color}"{weight}>{html.escape(text)}</tspan>'
            )
        out.append(
            f'<text x="68" y="{y}" font-family="{MONO}" font-size="{font_size}" xml:space="preserve">{"".join(parts)}</text>'
        )
        y += line_height
    out.append("</svg>")
    return "\n".join(out)


def shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    report = load_report()
    write_report()
    packet = collect_packet()

    (ASSETS / "terminal-audit.svg").write_text(
        terminal_svg(terminal_lines(report), "pragmatic-audit terminal output"),
        encoding="utf-8",
    )
    (ASSETS / "terminal-packet.svg").write_text(
        terminal_svg(packet_lines(packet), "pragmatic-audit agent packet"),
        encoding="utf-8",
    )
    (ASSETS / "report-preview.svg").write_text(document_preview(report), encoding="utf-8")
    print(f"Wrote {ASSETS / 'terminal-audit.svg'}")
    print(f"Wrote {ASSETS / 'terminal-packet.svg'}")
    print(f"Wrote {ASSETS / 'report-preview.svg'}")
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
