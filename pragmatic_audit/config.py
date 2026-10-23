from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ is required
    tomllib = None  # type: ignore[assignment]

DEFAULT_EXCLUDES = [
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "dist",
    "build",
    "target",
    "out",
    "vendor",
    "third_party",
    ".next",
    ".nuxt",
    ".turbo",
    ".parcel-cache",
    "coverage",
    "htmlcov",
    "Pods",
    "DerivedData",
    "obj",
]

CONFIG_NAME = ".pragmatic-audit.toml"
VALID_LEVELS = {"none", "low", "medium", "high"}


@dataclass
class Thresholds:
    long_function: int = 60
    deep_nesting: int = 4
    max_params: int = 5
    test_ratio: float = 0.3
    duplicate_window: int = 6


@dataclass
class Config:
    excludes: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    languages: list[str] | None = None
    thresholds: Thresholds = field(default_factory=Thresholds)
    ignore_rules: set[str] = field(default_factory=set)
    ignore_paths: list[str] = field(default_factory=list)
    fail_on: str = "none"
    min_confidence: str = "low"
    include_history: bool = False

    def should_exclude(self, rel: str) -> bool:
        rel = rel.replace("\\", "/")
        parts = rel.split("/")
        for pattern in self.excludes:
            normalized = pattern.replace("\\", "/").strip("/")
            if not normalized:
                continue
            if fnmatch.fnmatch(rel, normalized) or fnmatch.fnmatch(rel, f"{normalized}/*"):
                return True
            if any(fnmatch.fnmatch(part, normalized) for part in parts):
                return True
        return False

    def is_ignored_path(self, rel: str) -> bool:
        rel = rel.replace("\\", "/")
        for pattern in self.ignore_paths:
            normalized = pattern.replace("\\", "/").strip("/")
            if normalized and (
                fnmatch.fnmatch(rel, normalized)
                or fnmatch.fnmatch(rel, f"{normalized}/*")
                or rel == normalized
            ):
                return True
        return False

    def is_ignored(self, rule_id: str, rel: str) -> bool:
        return rule_id in self.ignore_rules or "*" in self.ignore_rules or self.is_ignored_path(rel)

    @classmethod
    def load(cls, root: Path, explicit: Path | None = None) -> "Config":
        path = explicit or (root / CONFIG_NAME)
        if explicit is not None and not explicit.exists():
            raise ValueError(f"config file not found: {explicit}")
        if not path.exists():
            return cls()
        if tomllib is None:
            raise RuntimeError("tomllib is required; use Python 3.11 or newer")
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        scan = data.get("scan", {}) or {}
        thresholds = data.get("thresholds", {}) or {}
        ignore = data.get("ignore", {}) or {}
        ci = data.get("ci", {}) or {}

        excludes = list(DEFAULT_EXCLUDES)
        for item in scan.get("exclude", []) or []:
            if isinstance(item, str) and item not in excludes:
                excludes.append(item)

        languages = scan.get("languages")
        if languages is not None and not isinstance(languages, list):
            raise ValueError("scan.languages must be a list of strings")

        config = cls(
            excludes=excludes,
            languages=[str(item) for item in languages] if languages else None,
            thresholds=Thresholds(
                long_function=_positive_int(thresholds, "long_function", 60),
                deep_nesting=_positive_int(thresholds, "deep_nesting", 4),
                max_params=_positive_int(thresholds, "max_params", 5),
                test_ratio=_ratio(thresholds, "test_ratio", 0.3),
                duplicate_window=_positive_int(thresholds, "duplicate_window", 6),
            ),
            ignore_rules={str(item).upper() for item in (ignore.get("rules") or [])},
            ignore_paths=[str(item) for item in (ignore.get("paths") or [])],
            fail_on=str(ci.get("fail_on", "none")).lower(),
            min_confidence=str(ci.get("min_confidence", "low")).lower(),
            include_history=bool(ci.get("include_history", False)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.fail_on not in VALID_LEVELS:
            raise ValueError(f"ci.fail_on must be one of {sorted(VALID_LEVELS)}")
        if self.min_confidence not in {"low", "medium", "high"}:
            raise ValueError("ci.min_confidence must be low, medium, or high")
        if not 0 <= self.thresholds.test_ratio <= 1:
            raise ValueError("thresholds.test_ratio must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "excludes": self.excludes,
            "languages": self.languages,
            "thresholds": {
                "long_function": self.thresholds.long_function,
                "deep_nesting": self.thresholds.deep_nesting,
                "max_params": self.thresholds.max_params,
                "test_ratio": self.thresholds.test_ratio,
                "duplicate_window": self.thresholds.duplicate_window,
            },
            "ignore_rules": sorted(self.ignore_rules),
            "ignore_paths": self.ignore_paths,
            "fail_on": self.fail_on,
            "min_confidence": self.min_confidence,
            "include_history": self.include_history,
        }


def _positive_int(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"thresholds.{key} must be a positive integer")
    return value


def _ratio(data: dict[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        raise ValueError(f"thresholds.{key} must be between 0 and 1")
    return float(value)
