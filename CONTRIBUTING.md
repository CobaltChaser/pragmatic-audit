# Contributing

**PRs are open.** This project gets better when more people encode the principles they actually use.

Rule proposals, false-positive reports, new language patterns, docs fixes, and examples are welcome. You do not need permission to open an issue. For a large change, open an issue first so the design does not surprise anyone.

## Setup

Requirements: Python 3.11 or newer. There are no third-party runtime dependencies.

```bash
git clone https://github.com/CobaltChaser/pragmatic-audit.git
cd pragmatic-audit
python3 -m unittest discover -s tests -v
python3 -m compileall pragmatic_audit
python3 -m pragmatic_audit . --ci --fail-on high
```

The last command audits the repository against itself. Medium and low findings are allowed; high findings block the gate.

## Ways to contribute

### Report a false positive

Open a bug report with:

- the rule ID;
- a minimal code sample that triggers it;
- why the code is correct in this context;
- the language and framework, if relevant.

A good false-positive report is more valuable than a new rule. It makes the existing rule honest.

### Propose a rule

Open a rule proposal with:

- the principle and tip number;
- what the rule detects;
- at least two false positives you expect;
- a before/after example;
- a positive fixture and a negative fixture;
- the languages it should apply to.

Rules that need whole-program analysis, a network call, or a framework-specific plugin are out of scope for v1.

### Add a language pattern

Start with an existing rule and extend its detector. Add a positive and a negative fixture. Keep the heuristic conservative: a missed finding is cheaper than a noisy one.

### Improve docs

Every behavior claim needs a code link or a test. Keep examples copyable. Do not add marketing language.

## Adding a rule

1. Choose the module in `pragmatic_audit/rules/` that fits the principle.
2. Write a `check_*` function that returns a small list of findings.
3. Use `make_finding()` so severity and confidence are inherited.
4. Register the rule with `register(Rule(...))`.
5. Add a positive test and a negative test in `tests/test_rules.py`.
6. Add the rule to `docs/rules.md` with a false-positive section.
7. Add the rule to the summary table in the README if it is a core rule.
8. Run the full suite and the self-audit.

A rule must:

- be deterministic;
- tolerate parse errors;
- never read the network;
- never execute repository code;
- never print a secret value;
- return at most a small number of findings.

## Pull request checklist

- [ ] Tests pass: `python3 -m unittest discover -s tests -v`
- [ ] Package compiles: `python3 -m compileall pragmatic_audit`
- [ ] Self-audit has no new high findings: `python3 -m pragmatic_audit . --ci --fail-on high`
- [ ] New rule has positive and negative fixtures
- [ ] Docs updated, including false positives
- [ ] No new runtime dependencies
- [ ] No secrets, credentials, or personal paths in the diff
- [ ] The PR explains the behavior change and the evidence

## Style

- Python 3.11+, standard library only.
- Type hints on public functions.
- Small functions with clear names.
- No comments that restate the code.
- Prefer explicit behavior over clever shortcuts.
- Keep user-facing messages short and concrete.

## Commit messages

Use a short imperative subject, then a body that explains why the change exists.

```text
fix: skip URL literals in trainwreck rule

A production URL contains dots and was being reported as a long call chain.
The rule now ignores lines containing http:// or https://.
```

## Code of conduct

By participating, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Report unacceptable behavior through the contact path described there.

## Security

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contribution is licensed under Apache-2.0, the same license as the project.
