# pragmatic-audit: ignore-file PP-CONFIG fixtures contain fake credentials and production-looking URLs on purpose
# pragmatic-audit: ignore-file PP-BROKEN-WINDOWS fixtures contain intentional skip markers
# pragmatic-audit: ignore-file PP-COMMENTS fixtures contain intentional commented-out code
# pragmatic-audit: ignore-file PP-TEST-HYGIENE fixtures contain intentional sleeps and fake network calls
from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from pragmatic_audit.config import Config
from pragmatic_audit.metrics import compute_metrics
from pragmatic_audit.rules import Context, run_rules
from pragmatic_audit.scanner import scan


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def audit(
    files: dict[str, str],
    *,
    git: bool = False,
    config: Config | None = None,
) -> tuple[list, list[str]]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _write(root, files)
        if git:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        cfg = config or Config()
        repo = scan(root, cfg)
        metrics = compute_metrics(repo, cfg.thresholds.duplicate_window)
        context = Context(repo=repo, config=cfg, metrics=metrics)
        findings, errors = run_rules(context, include_opt_in=True)
        return findings, errors


def rule_ids(findings: list) -> set[str]:
    return {finding.rule_id for finding in findings}


class RuleTestCase(unittest.TestCase):
    def assert_rule(self, rule_id: str, files: dict[str, str], **kwargs) -> None:
        findings, errors = audit(files, **kwargs)
        self.assertEqual(errors, [])
        self.assertIn(rule_id, rule_ids(findings))

    def assert_clean(self, rule_id: str, files: dict[str, str], **kwargs) -> None:
        findings, errors = audit(files, **kwargs)
        self.assertEqual(errors, [])
        self.assertNotIn(rule_id, rule_ids(findings))


class DuplicationTests(RuleTestCase):
    def test_repeated_block(self) -> None:
        self.assert_rule(
            "PP-DRY",
            {
                "src/report.py": """
                    def first(values):
                        total = 0
                        for value in values:
                            total += value
                        label = "total"
                        return label, total

                    def second(values):
                        total = 0
                        for value in values:
                            total += value
                        label = "total"
                        return label, total
                """
            },
        )

    def test_unique_blocks(self) -> None:
        self.assert_clean(
            "PP-DRY",
            {
                "src/report.py": """
                    def first(values):
                        return sum(values)

                    def second(values):
                        return max(values)
                """
            },
        )


class ConfigurationTests(RuleTestCase):
    def test_hardcoded_secret_and_url(self) -> None:
        self.assert_rule(
            "PP-CONFIG",
            {
                "src/client.py": """
                    password = "hunter2hunter2"
                    BASE_URL = "https://api.production.example.com"
                """
            },
        )

    def test_environment_configuration(self) -> None:
        self.assert_clean(
            "PP-CONFIG",
            {
                "src/client.py": """
                    import os
                    password = os.environ["PASSWORD"]
                    base_url = os.environ["BASE_URL"]
                """
            },
        )

    def test_secret_value_is_not_echoed(self) -> None:
        secret = "hunter2-hunter2-hunter2"
        findings, _ = audit(
            {"src/client.py": f'password = "{secret}"\n'}
        )
        self.assertIn("PP-CONFIG", rule_ids(findings))
        for finding in findings:
            self.assertNotIn(secret, finding.message)
            self.assertNotIn(secret, finding.evidence)
            self.assertNotIn(secret, finding.fix)

    def test_magic_number(self) -> None:
        self.assert_rule(
            "PP-MAGIC",
            {
                "src/policy.py": """
                    def allowed(items):
                        if len(items) > 42:
                            return items[:10]
                        return items
                """
            },
        )

    def test_named_limit(self) -> None:
        self.assert_clean(
            "PP-MAGIC",
            {
                "src/policy.py": """
                    MAX_ITEMS = 42
                    PAGE_SIZE = 10

                    def allowed(items):
                        if len(items) > MAX_ITEMS:
                            return items[:PAGE_SIZE]
                        return items
                """
            },
        )


class CouplingTests(RuleTestCase):
    def test_import_cycle(self) -> None:
        self.assert_rule(
            "PP-ORTHO",
            {
                "src/a.py": "from . import b\n",
                "src/b.py": "from . import a\n",
            },
        )

    def test_one_way_import(self) -> None:
        self.assert_clean(
            "PP-ORTHO",
            {
                "src/a.py": "from . import b\n",
                "src/b.py": "VALUE = 1\n",
            },
        )

    def test_mutable_global(self) -> None:
        self.assert_rule("PP-GLOBALS", {"src/cache.py": "cache = {}\n"})

    def test_named_constant(self) -> None:
        self.assert_clean("PP-GLOBALS", {"src/cache.py": "CACHE = {}\n"})

    def test_trainwreck(self) -> None:
        self.assert_rule(
            "PP-TRAINWRECK",
            {
                "src/view.py": """
                    def header(config):
                        return config.client.session.headers
                """
            },
        )

    def test_short_chain(self) -> None:
        self.assert_clean(
            "PP-TRAINWRECK",
            {
                "src/view.py": """
                    def header(config):
                        return config.client
                """
            },
        )

    def test_deep_inheritance(self) -> None:
        self.assert_rule(
            "PP-INHERIT",
            {
                "src/models.py": """
                    class A:
                        pass

                    class B(A):
                        pass

                    class C(B):
                        pass
                """
            },
        )

    def test_shallow_inheritance(self) -> None:
        self.assert_clean(
            "PP-INHERIT",
            {
                "src/models.py": """
                    class A:
                        pass

                    class B(A):
                        pass
                """
            },
        )


class ContractTests(RuleTestCase):
    def test_swallowed_error(self) -> None:
        self.assert_rule(
            "PP-CONTRACTS",
            {
                "src/load.py": """
                    def load(path):
                        try:
                            return open(path).read()
                        except Exception:
                            pass
                """
            },
        )

    def test_error_with_context(self) -> None:
        self.assert_clean(
            "PP-CONTRACTS",
            {
                "src/load.py": """
                    def load(path):
                        try:
                            with open(path) as handle:
                                return handle.read()
                        except OSError as exc:
                            raise RuntimeError(f"could not read {path}") from exc
                """
            },
        )

    def test_unclosed_resource(self) -> None:
        self.assert_rule(
            "PP-RESOURCES",
            {
                "src/load.py": """
                    def load(path):
                        handle = open(path)
                        return handle.read()
                """
            },
        )

    def test_context_manager(self) -> None:
        self.assert_clean(
            "PP-RESOURCES",
            {
                "src/load.py": """
                    def load(path):
                        with open(path) as handle:
                            return handle.read()
                """
            },
        )

    def test_mutable_default(self) -> None:
        self.assert_rule(
            "PP-COINCIDENCE",
            {
                "src/collect.py": """
                    def collect(items=[]):
                        items.append(1)
                        return items
                """
            },
        )

    def test_safe_default(self) -> None:
        self.assert_clean(
            "PP-COINCIDENCE",
            {
                "src/collect.py": """
                    def collect(items=None):
                        items = [] if items is None else items
                        items.append(1)
                        return items
                """
            },
        )


class ComplexityTests(RuleTestCase):
    def test_long_function(self) -> None:
        body = "\n".join(f"    value += {index}" for index in range(65))
        self.assert_rule(
            "PP-COMPLEXITY",
            {"src/metrics.py": f"def total():\n    value = 0\n{body}\n    return value\n"},
        )

    def test_short_function(self) -> None:
        self.assert_clean(
            "PP-COMPLEXITY",
            {"src/metrics.py": "def total(values):\n    return sum(values)\n"},
        )

    def test_generic_names(self) -> None:
        self.assert_rule(
            "PP-NAMING",
            {"src/thing.py": "def f(data):\n    return data\n"},
        )

    def test_intent_revealing_names(self) -> None:
        self.assert_clean(
            "PP-NAMING",
            {
                "src/order.py": """
                    def calculate_order_total(order):
                        return order.total
                """
            },
        )

    def test_commented_out_code(self) -> None:
        self.assert_rule(
            "PP-COMMENTS",
            {
                "src/old.py": """
                    def run():
                        # if enabled:
                        #     return 1
                        return 0
                """
            },
        )

    def test_prose_comment(self) -> None:
        self.assert_clean(
            "PP-COMMENTS",
            {
                "src/current.py": """
                    def run():
                        # The scheduler calls this once per minute.
                        return 0
                """
            },
        )


class TestDisciplineTests(RuleTestCase):
    def test_missing_tests(self) -> None:
        self.assert_rule("PP-TESTS", {"src/app.py": "def run():\n    return 1\n"})

    def test_assertion_free_test(self) -> None:
        self.assert_rule(
            "PP-TESTS",
            {"tests/test_app.py": "def test_run():\n    print('ran')\n"},
        )

    def test_asserting_test(self) -> None:
        self.assert_clean(
            "PP-TESTS",
            {
                "src/app.py": "def run():\n    return 1\n",
                "tests/test_app.py": """
                    from app import run

                    def test_run():
                        assert run() == 1
                """,
            },
        )

    def test_sleep_in_test(self) -> None:
        self.assert_rule(
            "PP-TEST-HYGIENE",
            {
                "tests/test_flow.py": """
                    import time

                    def test_flow():
                        time.sleep(1)
                        assert True
                """
            },
        )

    def test_deterministic_test(self) -> None:
        self.assert_clean(
            "PP-TEST-HYGIENE",
            {
                "tests/test_flow.py": """
                    def test_flow():
                        assert 1 + 1 == 2
                """
            },
        )

    def test_unit_only_tests(self) -> None:
        self.assert_rule(
            "PP-E2E",
            {"tests/test_unit.py": "def test_one():\n    assert 1 == 1\n"},
        )

    def test_e2e_test(self) -> None:
        self.assert_clean(
            "PP-E2E",
            {"tests/e2e/test_flow.py": "def test_flow():\n    assert True\n"},
        )

    def test_skipped_test(self) -> None:
        self.assert_rule(
            "PP-BROKEN-WINDOWS",
            {
                "tests/test_skip.py": """
                    import pytest

                    @pytest.mark.skip
                    def test_later():
                        assert True
                """
            },
        )

    def test_no_broken_windows(self) -> None:
        self.assert_clean(
            "PP-BROKEN-WINDOWS",
            {"tests/test_ok.py": "def test_ok():\n    assert True\n"},
        )


class RepositoryTests(RuleTestCase):
    def test_missing_readme(self) -> None:
        self.assert_rule("PP-DOCS", {"src/app.py": "VALUE = 1\n"})

    def test_documented_readme(self) -> None:
        self.assert_clean(
            "PP-DOCS",
            {
                "src/app.py": "VALUE = 1\n",
                "README.md": """
                    # Sample app

                    This project demonstrates a small, documented application.

                    ## Install

                    Run `python3 -m pip install -e .` to install it.

                    ## Usage

                    Run `python3 -m sample` to start it.

                    ## Test

                    Run `python3 -m unittest` to run the test suite.

                    ## License

                    Apache-2.0.
                """,
            },
        )

    def test_missing_automation(self) -> None:
        self.assert_rule("PP-AUTOMATION", {"src/app.py": "VALUE = 1\n"})

    def test_ci_and_makefile(self) -> None:
        self.assert_clean(
            "PP-AUTOMATION",
            {
                "src/app.py": "VALUE = 1\n",
                "Makefile": "test:\n\tpython3 -m unittest\n",
                ".github/workflows/ci.yml": "name: ci\non: [push]\n",
            },
        )

    def test_not_a_git_repository(self) -> None:
        self.assert_rule("PP-VCS", {"src/app.py": "VALUE = 1\n"})

    def test_git_repository(self) -> None:
        self.assert_clean(
            "PP-VCS",
            {"src/app.py": "VALUE = 1\n", ".gitignore": "__pycache__/\n"},
            git=True,
        )


class OptionalRuleTests(RuleTestCase):
    def test_vendor_without_adapter(self) -> None:
        self.assert_rule(
            "PP-REVERSIBILITY",
            {
                "src/uploads.py": "import boto3\n",
                "src/images.py": "import boto3\n",
                "src/backups.py": "import boto3\n",
            },
        )

    def test_vendor_behind_adapter(self) -> None:
        self.assert_clean(
            "PP-REVERSIBILITY",
            {
                "src/uploads.py": "import boto3\n",
                "src/images.py": "import boto3\n",
                "src/adapters/aws.py": "import boto3\n",
            },
        )

    def test_shared_state_near_concurrency(self) -> None:
        self.assert_rule(
            "PP-SHARED-STATE",
            {"src/worker.py": "import threading\nqueue = []\n"},
        )

    def test_state_inside_owner(self) -> None:
        self.assert_clean(
            "PP-SHARED-STATE",
            {
                "src/worker.py": """
                    import threading

                    class Queue:
                        def __init__(self):
                            self.items = []
                """
            },
        )


class SuppressionTests(RuleTestCase):
    def test_inline_suppression(self) -> None:
        self.assert_clean(
            "PP-MAGIC",
            {
                "src/policy.py": """
                    def allowed(items):
                        if len(items) > 42:  # pragmatic-audit: ignore PP-MAGIC reason
                            return items
                        return items
                """
            },
        )

    def test_file_suppression(self) -> None:
        self.assert_clean(
            "PP-GLOBALS",
            {
                "src/cache.py": """
                    # pragmatic-audit: ignore-file PP-GLOBALS cache is the owner
                    cache = {}
                """
            },
        )


if __name__ == "__main__":
    unittest.main()
