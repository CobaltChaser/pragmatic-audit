## What changed

<!-- One short paragraph. Explain the behavior change, not the file list. -->

## Why

<!-- The problem this solves. Link the issue if there is one. -->

## Evidence

<!-- Commands you ran and what they returned. -->

```text
python3 -m unittest discover -s tests -v
python3 -m compileall pragmatic_audit
python3 -m pragmatic_audit . --ci --fail-on high
```

## Checklist

- [ ] Tests pass
- [ ] New or changed behavior has a test
- [ ] New rule has positive and negative fixtures
- [ ] Docs updated, including false positives
- [ ] Self-audit has no new high findings
- [ ] No new runtime dependencies
- [ ] No secrets, credentials, or personal paths in the diff
- [ ] The change preserves behavior unless a behavior change was requested

## Notes for reviewers

<!-- Trade-offs, deliberate suppressions, or follow-ups. -->
