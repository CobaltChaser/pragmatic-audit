from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pragmatic_audit.config import Config


class ConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = Config()
        self.assertIn(".git", config.excludes)
        self.assertEqual(config.thresholds.long_function, 60)
        self.assertEqual(config.fail_on, "none")

    def test_from_dict(self) -> None:
        config = Config.from_dict(
            {
                "scan": {"exclude": ["generated"], "languages": ["python"]},
                "thresholds": {"long_function": 30, "deep_nesting": 3},
                "ignore": {"rules": ["pp-magic"], "paths": ["tests/**"]},
                "ci": {"fail_on": "high", "min_confidence": "medium"},
            }
        )
        self.assertIn("generated", config.excludes)
        self.assertEqual(config.languages, ["python"])
        self.assertEqual(config.thresholds.long_function, 30)
        self.assertEqual(config.thresholds.deep_nesting, 3)
        self.assertIn("PP-MAGIC", config.ignore_rules)
        self.assertTrue(config.is_ignored("PP-MAGIC", "src/policy.py"))
        self.assertTrue(config.is_ignored("PP-DRY", "tests/test_one.py"))
        self.assertEqual(config.fail_on, "high")

    def test_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            Config.from_dict({"thresholds": {"long_function": 0}})

    def test_invalid_ratio(self) -> None:
        with self.assertRaises(ValueError):
            Config.from_dict({"thresholds": {"test_ratio": 1.5}})

    def test_invalid_fail_on(self) -> None:
        with self.assertRaises(ValueError):
            Config.from_dict({"ci": {"fail_on": "sometimes"}})

    def test_missing_explicit_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                Config.load(Path(temporary), Path(temporary) / "missing.toml")

    def test_excludes(self) -> None:
        config = Config()
        self.assertTrue(config.should_exclude("node_modules/react/index.js"))
        self.assertTrue(config.should_exclude("dist/app.js"))
        self.assertFalse(config.should_exclude("src/app.py"))


if __name__ == "__main__":
    unittest.main()
