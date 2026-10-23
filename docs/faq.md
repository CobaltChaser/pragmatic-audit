# FAQ

### Why not just use a linter?

Linters enforce syntax, style, and language-specific correctness. They do not ask whether one piece of knowledge has one home, whether a boundary fails loudly, or whether a change stays local. `pragmatic-audit` checks design habits that cross languages and frameworks. Run both.

### Why no auto-fix?

Most of these findings need context. Extracting a shared function from two similar blocks can be wrong if the two blocks represent different business rules. Moving a value into configuration can be wrong if it is a protocol constant. An auto-fix would make the tool feel productive while creating worse code. The CLI gives you a location and a fix suggestion; a human or agent decides.

### Why no LLM call inside the CLI?

The audit must be deterministic, fast, offline, and cheap. An LLM inside the CLI would add latency, cost, privacy risk, and non-reproducible results. The hybrid design puts judgment in the agent session, where the human already is, and keeps the scanner trustworthy.

### Why is the score called "signal" and not a grade?

Because it is not a grade. It is a directional penalty based only on finding counts. It is useful for watching a trend and useless for comparing teams. The README and every report label it as a heuristic.

### Why does it flag my framework code?

The rules are language-level heuristics, not framework-aware analyzers. A test assertion chain, a query builder, a framework base class, or a generated migration can look exactly like a problem. Suppress it with a written reason, ignore a path, or tune the rule.

### How do I suppress a finding?

Inline:

```python
if len(items) > 42:  # pragmatic-audit: ignore PP-MAGIC pagination boundary from the API contract
```

File-level:

```python
# pragmatic-audit: ignore-file PP-GLOBALS this module is the state owner
```

Project-level, in `.pragmatic-audit.toml`:

```toml
[ignore]
rules = ["PP-MAGIC"]
paths = ["migrations/**"]
```

A suppression should explain why. A bare suppression is itself a broken window.

### Does it send my code anywhere?

No. There is no network access, no telemetry, and no hidden upload. The CLI reads files, writes the report you ask for, and exits.

### Does it echo secrets?

No. The config rule reports the file and line, and redacts the value. If you find a real secret in a tracked file, remove it from the index and rotate it. A report is not a remediation.

### What languages are supported?

Structural parsing: Python (`ast`), JavaScript and TypeScript (a conservative tokenizer). Line-oriented heuristics: Go, Java, Kotlin, Rust, Ruby, PHP, C#, Swift, Scala, and Elixir for several rules. The scanner is intentionally conservative outside Python and JavaScript.

### Why does it say my repository is not under version control when it is?

The scanner starts at the path you pass. If that path is a subdirectory of a git repository, `git -C <path> rev-parse --show-toplevel` should still find the root. If it does not, the directory may be a copy without `.git`, or git may be unavailable in the environment. Run `git -C <path> rev-parse --show-toplevel` to check.

### Why does `--fail-on high` fail when I have no high findings?

It should not. Check the JSON output and the exit code. Exit `3` means a rule failed internally, not that the gate failed. Exit `2` means invalid usage or an unreadable path.

### Can I use it in a monorepo?

Yes. Point it at the package directory, or use `scan.exclude` to skip unrelated packages. If the package is inside a larger git repository, the VCS rule uses the repository root.

### Can I use it commercially?

Yes. Apache-2.0 allows commercial and closed-source use. Keep the copyright, license, and `NOTICE`, and state significant changes. See [LICENSE](../LICENSE).

### Is this affiliated with the authors of The Pragmatic Programmer?

No. It is an independent, unofficial tool. Tip names and numbers are referenced descriptively with attribution. No book text is reproduced.

### How do I propose a rule?

Open a rule proposal issue using the template. Include the principle and tip, what the rule detects, likely false positives, a before/after example, and at least one fixture. See [CONTRIBUTING](../CONTRIBUTING.md).

### Why does the agent packet exist if the CLI already prints findings?

Because an agent needs a different artifact than a human. The packet includes the manual review queue, the files worth opening, the questions to answer, and a prompt with explicit guardrails. It is evidence, not a verdict.
