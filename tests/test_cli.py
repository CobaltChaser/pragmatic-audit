from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from pragmatic_audit.cli import main

README = """\
# Sample project

This sample project exists to exercise the pragmatic-audit command line.

## Install

Run `python3 -m pip install -e .`.

## Usage

Run `python3 -m sample`.

## Test

Run `python3 -m unittest`.
"""

CLEAN_SOURCE = """\
MAX_ITEMS = 100

def add(first, second):
    return first + second

def take(items):
    return items[:MAX_ITEMS]
"""

CLEAN_TEST = """\
from sample import add

def test_add():
    assert add(1, 2) == 3
"""

BAD_SOURCE = """\
def load(path):
    try:
        return open(path).read()
    except Exception:
        pass
"""


def make_repo(root: Path, *, bad: bool = False) -> None:
    files = {
        "README.md": README,
        "src/sample.py": BAD_SOURCE if bad else CLEAN_SOURCE,
        "tests/test_sample.py": CLEAN_TEST,
        "tests/e2e/test_flow.py": "def test_flow():\n    assert True\n",
        ".gitignore": "__pycache__/\n",
        "Makefile": "test:\n\tpython3 -m unittest\n",
        ".github/workflows/ci.yml": "name: ci\non: [push]\n",
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def invoke(arguments: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(arguments)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTests(unittest.TestCase):
    def test_json_report_passes_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_repo(root)
            code, stdout, stderr = invoke(
                [str(root), "--format", "json", "--fail-on", "high", "--ci"]
            )
            self.assertEqual(code, 0, stderr)
            data = json.loads(stdout)
            self.assertEqual(data["summary"]["files_scanned"], 3)
            self.assertIn("findings", data)
            self.assertIn("manual_review", data)

    def test_gate_fails_on_high_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_repo(root, bad=True)
            code, stdout, stderr = invoke(
                [str(root), "--format", "json", "--fail-on", "high", "--ci"]
            )
            self.assertEqual(code, 1, stderr)
            data = json.loads(stdout)
            self.assertTrue(any(item["rule"] == "PP-CONTRACTS" for item in data["findings"]))

    def test_agent_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary) / "repo"
            repo_root.mkdir()
            make_repo(repo_root)
            work = Path(temporary) / "work"
            work.mkdir()
            previous = Path.cwd()
            os.chdir(work)
            try:
                code, _, stderr = invoke(
                    [str(repo_root), "--agent-packet", "--format", "json", "--ci"]
                )
                self.assertEqual(code, 0, stderr)
                packet = json.loads((work / "pragmatic-audit.packet.json").read_text())
                self.assertEqual(packet["packet_version"], 1)
                self.assertIn("review_instructions", packet)
                self.assertTrue((work / "pragmatic-audit.packet.md").is_file())
            finally:
                os.chdir(previous)

    def test_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_repo(root)
            output = root / "reports" / "audit.md"
            code, _, stderr = invoke(
                [str(root), "--format", "markdown", "--output", str(output), "--ci"]
            )
            self.assertEqual(code, 0, stderr)
            self.assertIn("# Pragmatic Audit Report", output.read_text())

    def test_missing_path(self) -> None:
        code, _, stderr = invoke(["/path/that/does/not/exist"])
        self.assertEqual(code, 2)
        self.assertIn("pragmatic-audit:", stderr)

    def test_list_rules(self) -> None:
        code, stdout, _ = invoke(["--list-rules"])
        self.assertEqual(code, 0)
        self.assertIn("PP-DRY", stdout)
        self.assertIn("PP-AUTOMATION", stdout)


if __name__ == "__main__":
    unittest.main()
