# Rule catalog for agents

Every finding is a hypothesis. Open the file, read the context, and decide whether the rule is right for this code.

## Core rules

| Rule | Detects | Common false positives | Smallest fix |
|---|---|---|---|
| `PP-DRY` | Six-line normalized duplicates and identical function bodies | Generated tables, protocol boilerplate, intentionally independent modules | Extract the shared knowledge, not just the text |
| `PP-CONFIG` | Assigned secrets, production URLs, absolute paths, non-local IPs | Docs URLs, schema identifiers, local dev hosts | Move the value to configuration or a secret store |
| `PP-MAGIC` | Numeric literals in comparisons, excluding -1, 0, 1, 2, 10 | Protocol constants, array indices | Name the policy and give it one home |
| `PP-ORTHO` | Import cycles and modules with more than 15 internal imports | Package re-exports, plugin registries | Break the cycle behind a narrower interface |
| `PP-GLOBALS` | Module-level mutable state, `global`, mutable defaults | Uppercase constants, explicit state owners | Pass state explicitly or wrap it in an API |
| `PP-TRAINWRECK` | Chains with three or more dots | Builders, query DSLs, assertion chains, URLs | Ask the owner for the final value |
| `PP-INHERIT` | Inheritance depth over two | Framework bases, exception hierarchies | Prefer composition, interfaces, or delegation |
| `PP-CONTRACTS` | Empty catches and handlers containing only `pass` or `...` | Deliberate optional cleanup, cancellation | Handle, add context and re-raise, or fail fast |
| `PP-RESOURCES` | Open files, connections, or sessions without a guaranteed close | Ownership transferred to the caller | Use `with` or `try/finally` |
| `PP-COINCIDENCE` | Mutable defaults, float equality, loose JS equality, `var` | Loose null checks, exact sentinels | Make the behavior explicit |
| `PP-COMPLEXITY` | Long functions, deep nesting, many branches, many parameters, huge files | Generated parsers, dispatch tables, data definitions | Extract named steps or split by responsibility |
| `PP-NAMING` | Single-letter and generic names, vague boolean names | Loop indices, coordinates, tight scopes | Rename to the domain concept |
| `PP-COMMENTS` | Two or more consecutive commented-out code lines | Examples inside explanatory comments | Delete it; version control remembers |
| `PP-BROKEN-WINDOWS` | Skipped tests, unexplained suppressions, TODO density | Skips with an issue link or explicit reason | Fix it or record a bounded plan |
| `PP-TESTS` | No tests, thin test ratio, assertion-free tests | Docs-only repos, unsupported test frameworks | Test the behavior you intend to keep |
| `PP-TEST-HYGIENE` | Sleeps, real network calls, randomness, clock reads in tests | Intentional integration suites behind a marker | Inject time, fake the boundary, use fixtures |
| `PP-AUTOMATION` | No CI, no task automation, manual deploy instructions | Examples, parent-monorepo CI | Add a CI workflow and a local task |
| `PP-VCS` | Not git, missing `.gitignore`, tracked secrets or large files | Intentional subdirectory of a larger repo | Initialize git, ignore local files, remove secrets |
| `PP-E2E` | No end-to-end, integration, smoke, or browser marker | Libraries with no layers to connect | Add one thin path through the real boundary |
| `PP-DOCS` | Missing or unhelpful README | Docs site lives elsewhere | Add purpose, install, usage, and test instructions |

## Opt-in rules

| Rule | Detects | Common false positives | Smallest fix |
|---|---|---|---|
| `PP-SMALL-STEPS` | Recent commits over 30 files or 1,000 lines | Lockfile updates, generated changes, mass renames | Split the change into reviewable steps |
| `PP-REVERSIBILITY` | A vendor SDK in 3+ production modules with no adapter path | Small scripts, adapter in another package | Isolate the vendor behind one interface |
| `PP-SHARED-STATE` | Mutable module state near threads, async, or multiprocessing | A synchronized queue or documented state owner | Give the state one owner or pass it explicitly |

## Interpreting severity and confidence

- **High severity** means the failure mode is expensive: silent errors, leaked secrets, missing safety net.
- **Medium severity** means the code will be harder to change or test.
- **Low severity** means a readability or consistency issue.

Confidence is the scanner's certainty that the pattern is present, not the certainty that it is wrong for this code. A high-confidence finding can still be the right exception.

## Triage format

```text
Confirmed
- PP-CONTRACTS src/load.py:12 — the handler ignores a parse failure; callers receive None.
  Fix: raise a typed LoadError with the path and cause.

Dismissed
- PP-TRAINWRECK src/query.py:44 — this is a documented builder API; the chain is the interface.

Judgment call
- PP-REVERSIBILITY — the vendor appears in three modules, but they share one package.
  Inspect whether the package is the intended boundary.
```

Do not report a finding without a file and line. Do not report a rule name without explaining the actual problem in the code.
