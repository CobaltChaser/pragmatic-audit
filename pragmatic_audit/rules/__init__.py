"""Rule registry and built-in rules."""

from __future__ import annotations

from . import (  # noqa: F401 - imports register rules
    automation,
    complexity,
    config_values,
    contracts,
    coupling,
    docs,
    duplication,
    optional,
    tests,
    vcs,
)
from .registry import RULES, Context, Rule, run_rules

__all__ = ["RULES", "Context", "Rule", "run_rules"]
