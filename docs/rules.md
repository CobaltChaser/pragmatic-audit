# Rule catalog

Every finding includes a rule ID, the principle and tip it comes from, a severity, a confidence, a `file:line` location, a one-line explanation, and a one-line fix.

The scan is a heuristic. Read the code before acting on a finding. If the rule is wrong for a specific line, suppress it with a written reason:

```python
if len(items) > 42:  # pragmatic-audit: ignore PP-MAGIC limit defined by the upstream API
```

Full suppression syntax and configuration are in the [README](../README.md#tuning).

## Summary

| Rule | Principle | Tips | Default severity | Default confidence |
|---|---|---|---|---|
| `PP-DRY` | Don't repeat yourself | 15 | medium | medium |
| `PP-CONFIG` | External configuration | 55 | high | medium |
| `PP-MAGIC` | Policy is metadata | 79 | low | low |
| `PP-ORTHO` | Orthogonality | 17, 44 | medium | high |
| `PP-GLOBALS` | Avoid global data | 41, 47 | medium | medium |
| `PP-TRAINWRECK` | Decoupled code | 46 | low | low |
| `PP-INHERIT` | Composition over inheritance | 51, 52, 53 | medium | medium |
| `PP-CONTRACTS` | Design with contracts | 37, 38, 39 | high | high |
| `PP-RESOURCES` | Resource ownership | 40, 41 | medium | medium |
| `PP-COINCIDENCE` | Rely on reliable things | 62 | medium | medium |
| `PP-COMPLEXITY` | Good design is easier to change | 63, 65, 72 | medium | high |
| `PP-NAMING` | Express intent | 74 | low | low |
| `PP-COMMENTS` | Good code is its own documentation | 13, 74 | low | medium |
| `PP-BROKEN-WINDOWS` | Fix bad code when you see it | 5 | medium | medium |
| `PP-TESTS` | Design to test | 66, 67, 70, 71 | high | high |
| `PP-TEST-HYGIENE` | A good test is a good neighbor | 57, 66 | medium | medium |
| `PP-AUTOMATION` | Automate the routine | 89, 90, 95 | medium | high |
| `PP-VCS` | Version control everything | 28 | high | high |
| `PP-E2E` | Build end-to-end | 20, 68 | low | medium |
| `PP-DOCS` | Documentation lives with the code | 11, 13 | medium | high |
| `PP-SMALL-STEPS` | Small reversible steps | 42 | low | low |
| `PP-REVERSIBILITY` | There are no final decisions | 18 | low | low |
| `PP-SHARED-STATE` | Avoid shared mutable state | 57 | medium | medium |

The last three are opt-in. Enable them with `--include-history` or `--all`.

## Core rules

### PP-DRY — Don't repeat yourself

**Detects:** identical normalized blocks of six or more lines in production files, and functions with identical bodies.

**Why it matters:** duplicated knowledge means every future change has more than one place to go wrong.

**False positives:** generated tables, protocol boilerplate, test fixtures, and code that is intentionally duplicated to keep two modules independent. The scanner ignores imports and structural-only blocks.

**Tune:** change `thresholds.duplicate_window`. Ignore a path with `ignore.paths` if it is generated.

**Before / after:**

```python
# before
def subtotal(items):
    total = 0
    for item in items:
        total += item.price
    return total

def tax(items):
    total = 0
    for item in items:
        total += item.price
    return total
```

```python
# after
def subtotal(items):
    return sum(item.price for item in items)

def tax(items):
    return subtotal(items) * TAX_RATE
```

### PP-CONFIG — Parameterize configuration

**Detects:** assigned secrets, environment-specific URLs, user-specific absolute paths, and non-local IP addresses in source files. Secret values are redacted and never printed.

**Why it matters:** environment-specific values in code force a rebuild for every deployment and leak production details into version control.

**False positives:** documentation URLs, public schema identifiers, local development hosts, and examples that use `example.com`. The allowlist covers loopback addresses and the common example domains.

**Tune:** use `[ignore]` for a fixture directory, or move the value into configuration. Do not suppress a real secret; remove and rotate it.

### PP-MAGIC — Name policy values

**Detects:** integer or float literals used in comparisons, excluding `-1`, `0`, `1`, `2`, and `10`.

**Why it matters:** a bare number hides the policy it represents. Naming it makes the rule visible and gives it one place to change.

**False positives:** protocol constants, array indices, and small arithmetic that is genuinely local.

**Tune:** extract a named constant or move the value into configuration.

### PP-ORTHO — Keep components orthogonal

**Detects:** import cycles in internal Python modules and modules that import more than 15 internal modules.

**Why it matters:** a cycle means two components cannot be understood, tested, or changed independently.

**False positives:** package `__init__` re-exports and deliberate plugin registries.

**Tune:** break the cycle behind a narrower interface or move shared knowledge into a lower-level module.

### PP-GLOBALS — Avoid global data

**Detects:** module-level mutable assignments, `global` statements, and mutable default arguments.

**Why it matters:** global mutable state makes behavior depend on history and makes tests order-dependent.

**False positives:** uppercase constants, module-level registries that are the explicit owner of the state, and framework-required globals.

**Tune:** pass state explicitly, wrap it behind an API, or suppress with a note explaining why the module is the owner.

### PP-TRAINWRECK — Don't chain method calls

**Detects:** chains with three or more dots, excluding common fluent APIs and URL literals.

**Why it matters:** a long chain couples the caller to the internal shape of every object on the path.

**False positives:** builder APIs, query builders, dataframe libraries, and test assertion chains.

**Tune:** ask the owning object for the final value. Add a project-specific allowlist only if the chain is a documented public API.

### PP-INHERIT — Don't pay inheritance tax

**Detects:** Python and JavaScript inheritance depth greater than two.

**Why it matters:** deep hierarchies make behavior hard to trace and changes hard to isolate.

**False positives:** framework base classes and exception hierarchies.

**Tune:** prefer composition, interfaces, delegation, or mixins.

### PP-CONTRACTS — Crash early, don't swallow errors

**Detects:** empty `except`/`catch` blocks and handlers whose body only contains `pass` or `...`.

**Why it matters:** a swallowed error turns a visible failure into silent corruption.

**False positives:** deliberately optional cleanup where the failure is truly irrelevant, and cancellation paths.

**Tune:** handle the error, add context and re-raise, or fail fast. If the silence is intentional, suppress with a reason.

### PP-RESOURCES — Finish what you start

**Detects:** resources from `open()`, file constructors, or framework sessions that are not closed on every path.

**Why it matters:** leaked file handles, connections, and locks eventually exhaust the process.

**False positives:** resources returned to a caller who takes ownership, and framework-managed lifecycles.

**Tune:** use a context manager or `try/finally`.

### PP-COINCIDENCE — Don't program by coincidence

**Detects:** mutable default arguments, float equality, loose JavaScript equality, and `var` declarations.

**Why it matters:** code that works by accident stops working when the accident changes.

**False positives:** deliberate loose equality against `null` or `undefined`, and float comparisons against exact sentinel values.

**Tune:** use `None` plus explicit initialization, compare floats with a tolerance, use `===`, and prefer `const` or `let`.

### PP-COMPLEXITY — Refactor early, keep it simple

**Detects:** functions longer than 60 lines, nesting deeper than four, more than 12 branches, more than five parameters, and production files over 500 non-blank lines.

**Why it matters:** complexity is where bugs and review fatigue hide.

**False positives:** generated parsers, dispatch tables, and data definitions that are naturally wide.

**Tune:** extract named steps, simplify control flow, or split by responsibility. Thresholds are configurable.

### PP-NAMING — Name well; rename when needed

**Detects:** single-letter and generic names such as `data`, `info`, `tmp`, `value`, and `result`; vague boolean names such as `flag` and `status`.

**Why it matters:** a name that does not express intent forces every reader to reverse-engineer the code.

**False positives:** loop indices, coordinates, and conventional short names in tight scopes.

**Tune:** rename to the domain concept. The rule is intentionally low-confidence.

### PP-COMMENTS — Comment only what code cannot say

**Detects:** two or more consecutive commented-out code lines.

**Why it matters:** dead code in comments drifts from the real implementation and misleads readers.

**False positives:** code examples inside explanatory comments and commented configuration snippets.

**Tune:** delete the code; version control remembers it.

### PP-BROKEN-WINDOWS — Don't live with broken windows

**Detects:** skipped tests, unexplained checker suppressions, and more than three TODO/FIXME markers in one file.

**Why it matters:** visible neglect invites more neglect. A skipped test with no owner becomes permanent.

**False positives:** a skip with a linked issue or an explicit reason, and generated files with intentional `noqa` directives.

**Tune:** fix the underlying issue, or record a bounded plan. The rule treats a skip containing the word "reason" as lower severity, not as acceptable.

### PP-TESTS — Test your software, or your users will

**Detects:** no test files, test code below 30% of production code once production exceeds 100 lines, and Python or JavaScript test functions with no assertion.

**Why it matters:** tests are the executable description of the behavior you intend to keep.

**False positives:** a repository that intentionally has no tests (a docs-only project) and tests written in a framework the scanner does not understand.

**Tune:** set `thresholds.test_ratio`, or ignore the rule for a repository where it does not apply.

### PP-TEST-HYGIENE — Keep tests deterministic

**Detects:** wall-clock sleeps, real network calls, and randomness or current-time reads in test files.

**Why it matters:** nondeterministic tests train teams to ignore failures.

**False positives:** integration suites that intentionally exercise a real clock or network, usually behind an explicit marker.

**Tune:** inject a clock, fake the boundary, or use a deterministic fixture.

### PP-AUTOMATION — Automate the routine

**Detects:** no CI configuration, no task automation, and manual deployment instructions in the README.

**Why it matters:** a procedure that depends on memory will eventually be done differently, or not at all.

**False positives:** small examples and repositories that delegate CI to a parent monorepo.

**Tune:** add a CI workflow and a `Makefile`, `justfile`, or package scripts. Keep the same checks local and remote.

### PP-VCS — Version control everything

**Detects:** an audit root outside git, a missing `.gitignore`, tracked sensitive-looking files, and tracked files over 5 MB.

**Why it matters:** version control is the safety net that makes every other change reversible.

**False positives:** a repository that is intentionally a subdirectory of a larger git root. The scanner checks the git root, not just the audit root.

**Tune:** initialize git, add a `.gitignore`, remove tracked secrets, and use release artifacts for large binaries.

### PP-E2E — Build end-to-end

**Detects:** a test suite with no file path, marker, or text that suggests an end-to-end, integration, smoke, or browser test.

**Why it matters:** unit tests can all pass while the layers do not connect.

**False positives:** a library with no layers to connect, and projects that use a different word for integration tests.

**Tune:** add one thin path that exercises the real boundary, or suppress with a reason.

### PP-DOCS — Documentation lives with the code

**Detects:** no README, a README under 200 characters, and a README with no install, usage, run, or test instruction.

**Why it matters:** a new contributor cannot keep a system working if they cannot run it.

**False positives:** repositories that intentionally keep user documentation in a separate site. The rule still asks for a minimal repository README.

**Tune:** add purpose, setup, usage, and test instructions.

## Opt-in rules

### PP-SMALL-STEPS — Take small steps

**Detects:** recent commits touching more than 30 files or more than 1,000 lines.

**Why it matters:** a large change is hard to review and hard to reverse.

**False positives:** generated lockfile updates, vendored dependency upgrades, and repository-wide renames.

**Tune:** split changes before review. Enable with `--include-history`.

### PP-REVERSIBILITY — Keep decisions reversible

**Detects:** a vendor SDK used in three or more production modules without a path that looks like an adapter, gateway, provider, integration, or port.

**Why it matters:** the cost of replacing a vendor should be a module rewrite, not a repository rewrite.

**False positives:** small scripts that legitimately use one vendor everywhere, and projects that keep the adapter in a separate package.

**Tune:** isolate the vendor behind one interface. Enable with `--all`.

### PP-SHARED-STATE — Shared state is incorrect state

**Detects:** mutable module-level state in a file that also mentions threads, asyncio, multiprocessing, Tokio, or Rayon.

**Why it matters:** concurrent mutation produces failures that are hard to reproduce.

**False positives:** a module that owns a synchronized queue or cache behind a documented API.

**Tune:** give the state one owner or pass it explicitly. Enable with `--all`.

## JSON output

`--format json` returns a stable object:

```json
{
  "tool": "pragmatic-audit",
  "version": "0.1.0",
  "root": "/path/to/repo",
  "generated_at": "2026-01-01T00:00:00Z",
  "elapsed_seconds": 0.01,
  "summary": {
    "files_scanned": 12,
    "loc": 840,
    "prod_loc": 620,
    "test_loc": 220,
    "languages": {"python": 840},
    "findings": {"high": 1, "medium": 2, "low": 3},
    "signal": 80,
    "rules_triggered": 4
  },
  "findings": [
    {
      "rule": "PP-CONTRACTS",
      "title": "Crash early, don't swallow errors",
      "principle": "Design with contracts",
      "tips": [37, 38, 39],
      "severity": "high",
      "confidence": "high",
      "path": "src/load.py",
      "line": 12,
      "message": "`except Exception` swallows the error.",
      "fix": "Handle the error, add context and re-raise, or fail fast.",
      "evidence": "..."
    }
  ],
  "manual_review": [],
  "suggested_prompt": "...",
  "errors": []
}
```

The `signal` field is a directional penalty, not a grade. It starts at 100 and subtracts 6 per high, 2 per medium, and 0.5 per low finding, capped at a 85-point penalty. It exists to make trends visible, not to rank teams.
