# Code review checklist

Use this for a diff, a pull request, or an agent-written change. Answer the questions that apply. Cite a file and line for every issue.

## 1. What is the change supposed to make possible?

State the user-visible or system-visible outcome. If the diff does not serve that outcome, stop and ask.

## 2. Is there one thin end-to-end path?

For a new feature, can you trace input to output through the real layers? If every layer was built separately and never connected, the architecture is still a guess.

## 3. Where is the authoritative knowledge?

If a rule, formula, schema, or policy appears in more than one place, which copy is authoritative? Extract the knowledge, not just the text.

```python
# suspicious: two copies of the same policy
if order.total > 500:
    discount = 0.1
...
if invoice.total > 500:
    discount = 0.1
```

## 4. Does a change stay local?

Pick one concept in the diff. How many unrelated modules would change if the concept changed? If the answer is "many", the boundary is wrong.

## 5. Are the boundaries explicit?

Look at public functions and API handlers. Do they validate input? Do they state what they return? What happens on invalid input — an exception, a typed error, or a plausible-looking default?

## 6. Who owns each resource?

For every file, connection, lock, transaction, and temporary directory, find the release path. Is it guaranteed on exceptions and early returns?

## 7. Is configuration outside the code?

Search the diff for hosts, ports, credentials, user paths, and policy numbers. Could a staging deployment use the same artifact?

## 8. Do the names match the domain?

Read the names aloud. Would a domain expert recognize them? Is the same concept called two different things? Is a vague name hiding a missing concept?

## 9. Do the tests describe behavior?

A good test fails when behavior changes and passes when implementation details change. Look for tests that assert private calls, sleeps, network access, random data, or the current time.

## 10. Is the error path tested?

The happy path is the easy part. Is there a test for invalid input, a missing record, a timeout, a partial failure, or a retry?

## 11. Is the diff reversible?

Could this be deployed and rolled back without a data migration that cannot be undone? If not, what is the rollback plan?

## 12. What is the smallest useful next step?

If the change is too large, propose the first slice that produces evidence. Do not ask for a rewrite when a smaller move would answer the question.

## Review output

```text
Verdict: <one sentence>

Must fix
1. <file>:<line> — <problem>
   Why: <one sentence>
   Fix: <smallest safe change>

Should fix
1. <file>:<line> — <problem>
   Why: <one sentence>
   Fix: <smallest safe change>

Questions
- <question tied to a specific file or behavior>

Verified
- Tests run: <command>
- Audit run: <command or "not available">
```

Do not fill every section. An empty section is a valid result.

## Common failure modes

- A review that lists every scanner finding without reading the code.
- A review that proposes a framework or abstraction before the problem is understood.
- A review that treats style preferences as design defects.
- A review that says "add tests" without naming the behavior to test.
- A review that claims performance or security properties without measurement.
