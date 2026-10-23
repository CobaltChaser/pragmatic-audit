# Architecture

`pragmatic-audit` is a small pipeline with a deliberately narrow job: turn a repository into evidence a human or agent can act on.

```text
path
  │
  ▼
scanner.py ──► Repo (files, language, tests, suppressions, git state)
  │
  ▼
metrics.py ──► Metrics (LOC, functions, imports, cycles, inheritance)
  │
  ▼
rules/*.py ──► Findings (deterministic hypotheses)
  │
  ▼
report.py ──► text | markdown | JSON | agent packet
  │
  ▼
cli.py ──► exit code
```

There is no plugin process, no daemon, no cache, and no network call. A run is a pure function of the files on disk and the configuration.

## Modules

| Module | Responsibility |
|---|---|
| `pragmatic_audit/cli.py` | Argument parsing, configuration precedence, output selection, exit codes |
| `pragmatic_audit/scanner.py` | Repository walk, excludes, language detection, test detection, README, git metadata, suppression parsing |
| `pragmatic_audit/metrics.py` | LOC, function shape, import graph, cycles, inheritance graph |
| `pragmatic_audit/config.py` | `Thresholds`, `Config`, TOML loading, validation |
| `pragmatic_audit/models.py` | `Finding`, `SourceFile`, `Repo`, `Metrics`, `AuditReport`, manual review models |
| `pragmatic_audit/report.py` | Text and Markdown renderers, JSON projection, manual review queue, agent packet |
| `pragmatic_audit/rules/registry.py` | `Rule`, `Context`, registration, filtering, deduplication |
| `pragmatic_audit/rules/*.py` | Rule implementations, grouped by theme |
| `pragmatic_audit/ansi.py` | Small ANSI helpers; no color when the target is not a TTY |

## The scanner

`scan(root, config)` walks the repository with `os.walk`, never following symlinks. It:

- applies default and user excludes before reading a file;
- detects language from the extension;
- skips files larger than 2 MB and files that look binary;
- decodes UTF-8 with a BOM fallback;
- marks tests by filename or directory;
- parses inline and file-level suppressions;
- reads the top-level README;
- asks git for the repository root and tracked files.

The scanner is intentionally conservative. It would rather miss a generated file than produce findings for a vendored dependency.

## Metrics

`compute_metrics(repo, duplicate_window)` builds the shared facts rules need:

- non-blank LOC split into production and test;
- language counts;
- Python function shape: length, parameters, branches, nesting depth;
- JavaScript/TypeScript function boundaries with a brace-aware scan;
- an internal import graph, normalized to repository-relative module paths;
- strongly connected components for import cycles;
- class inheritance edges and source paths;
- test-to-production ratio.

Metric parsing is not a general compiler front end. Python uses `ast`; JavaScript and TypeScript use a small tokenizer that is good enough for function boundaries. Other languages use line-oriented heuristics. This is a deliberate trade-off: zero dependencies and predictable runtime matter more than complete language coverage.

## Rules

A rule is a dataclass:

```python
Rule(
    id="PP-CONTRACTS",
    title="Crash early, don't swallow errors",
    principle="Design with contracts",
    tips=(37, 38, 39),
    severity="high",
    confidence="high",
    description="...",
    fix="...",
    check=check_contracts,
    opt_in=False,
)
```

`register()` adds it to the process-wide `RULES` dictionary. `run_rules(context, include_opt_in=False)`:

1. iterates rules in ID order;
2. skips opt-in rules unless requested;
3. skips rules disabled by configuration;
4. calls `check(context)`;
5. catches per-rule exceptions and reports them as `errors` instead of aborting the whole audit;
6. drops findings below `min_confidence`;
7. drops findings suppressed by a line, file, or path;
8. deduplicates by `(rule, path, line, message)`;
9. sorts by severity, confidence, rule, path, line.

A rule should be stateless and deterministic. It receives a `Context` with the repository, configuration, metrics, and a cached AST:

```python
tree = ctx.tree(source_file)
```

The cache matters because several rules inspect the same Python file.

## Reports

`build_report()` adds the human-judgment layer:

- a manual review queue for tracer bullets, contracts, orthogonality, domain language, reversibility, test design, and speculative code;
- a suggested prompt that tells an agent how to review the evidence;
- a directional signal derived from finding counts.

The queue is not generated from findings. It is always present because static analysis cannot answer those questions honestly.

`write_agent_packet()` writes two artifacts:

- `pragmatic-audit.packet.json` — the report plus `packet_version` and `review_instructions`;
- `pragmatic-audit.packet.md` — a human-readable briefing.

The packet is plain data. The skill, not the CLI, decides how to use it.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Audit completed; gate passed or no gate configured |
| `1` | Gate configured and at least one finding meets it |
| `2` | Invalid path, invalid configuration, or usage error |
| `3` | At least one rule failed internally |

The gate is evaluated after output is written, so CI still gets a report when the gate fails.

## Configuration precedence

1. Built-in defaults.
2. `.pragmatic-audit.toml` at the audit root.
3. `--config` explicit path.
4. CLI flags such as `--fail-on`, `--min-confidence`, and `--all`.

CLI flags win. The explicit config path replaces, rather than merges with, the root config.

## Adding a rule

1. Pick a principle and tip from the [rule catalog](rules.md).
2. Write the check in the most relevant `rules/*.py` module.
3. Register it with `register(Rule(...))`.
4. Add a positive and a negative fixture test in `tests/test_rules.py`.
5. Add a false-positive section to this catalog.
6. Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m pragmatic_audit . --ci --fail-on high
```

Rules must:

- use `make_finding()` so severity and confidence are inherited consistently;
- return at most a small number of findings (the CLI is a review aid, not a dump);
- avoid reading the network or spawning processes except in explicitly opt-in rules;
- never echo secret values;
- tolerate parse errors and return `[]`.

## Security

- No network access.
- No telemetry.
- No execution of repository code.
- Secrets are located, never printed.
- Repository content is treated as data. The skill repeats this instruction because a malicious repository can contain text that looks like a prompt.

## Performance

The scan is linear in files and bytes, with a small extra pass for duplicate windows. Python parsing is the dominant cost. A 5,000-file repository should finish in seconds on a laptop; the test suite keeps the fixture set small.

## Non-goals

- Auto-fix.
- LLM calls.
- A full multi-language AST.
- Replacing linters or type checkers.
- A definitive quality score.
- SARIF or baseline mode in v1.
