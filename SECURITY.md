# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |
| older | no |

## Reporting a vulnerability

Do not open a public issue for a security problem.

Use GitHub's private vulnerability reporting:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Include a description, reproduction steps, affected version, and impact.

If private reporting is unavailable, contact [@CobaltChaser](https://github.com/CobaltChaser) through GitHub and ask for a private channel. Do not include exploit details in a public message.

You can expect an acknowledgment within seven days. This is a small, unfunded project; please allow reasonable time for a fix and coordinated disclosure.

## Scope

In scope:

- arbitrary code execution caused by the scanner;
- path traversal or unintended file reads beyond the audited directory;
- secret disclosure in reports, logs, or packet files;
- denial of service caused by a crafted repository;
- supply-chain issues in the release process.

Out of scope:

- findings that the audit itself reports (those are code-quality findings, not vulnerabilities);
- false positives or false negatives in a rule, unless they create a security impact;
- vulnerabilities in third-party tools used to install or host the project;
- social engineering.

## Design commitments

- No network access at runtime.
- No telemetry.
- No execution of repository code.
- Secrets are located by line and never printed.
- Repository content is treated as data. The agent skill explicitly tells agents not to follow instructions found in repository files.

## If you find a secret in a repository

The scanner reports the location of a possible secret, not its value. If the secret is real:

1. Remove it from the tracked files and the git index.
2. Rotate it at the provider.
3. Treat the old value as compromised even if the history is rewritten.
4. Add the file or pattern to `.gitignore`.

The audit report is not a remediation tool.
