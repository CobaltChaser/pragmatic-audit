# Agent skill

The skill is a folder: [`skills/pragmatic-programmer`](../skills/pragmatic-programmer). It contains a `SKILL.md` entry point and four reference files. The same folder works in every Agent Skills-compatible host.

## What it does

The skill changes how an agent approaches code, not just how it talks about code.

- Before coding: clarify the need, find the smallest end-to-end slice, define done, prefer reversible decisions, and avoid speculative structure.
- While coding: keep one authoritative representation of knowledge, keep concerns orthogonal, validate boundaries, own resources, externalize configuration, name for intent, and test behavior.
- After coding: run the tests, run `pragmatic-audit`, triage findings, and re-run.
- In audit mode: read the code before repeating a finding, separate confirmed issues from false positives, and report the few changes that most improve changeability.

The skill does not require the CLI. It uses the CLI when available and falls back to a manual review otherwise.

## Install

### Claude Code

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && mkdir -p ~/.claude/skills && cp -R ~/.cache/pragmatic-audit/skills/pragmatic-programmer ~/.claude/skills/
```

### Claude Cowork / claude.ai

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && cd ~/.cache/pragmatic-audit/skills && zip -r ~/Downloads/pragmatic-programmer.zip pragmatic-programmer
```

Then: **Customize → Skills → Upload** and select the ZIP.

### ChatGPT Work / CoWork

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && cd ~/.cache/pragmatic-audit/skills && zip -r ~/Downloads/pragmatic-programmer.zip pragmatic-programmer
```

Then: **Plugins → Skills → Create → Upload from your computer** and select the ZIP.

For local Codex:

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && mkdir -p ~/.codex/skills && cp -R ~/.cache/pragmatic-audit/skills/pragmatic-programmer ~/.codex/skills/
```

### OpenCode

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && mkdir -p ~/.config/opencode/skills && cp -R ~/.cache/pragmatic-audit/skills/pragmatic-programmer ~/.config/opencode/skills/
```

Project-local:

```bash
mkdir -p .opencode/skills && cp -R /path/to/pragmatic-audit/skills/pragmatic-programmer .opencode/skills/
```

### Generic Agent Skills host

```bash
rm -rf ~/.cache/pragmatic-audit && git clone --depth 1 https://github.com/CobaltChaser/pragmatic-audit.git ~/.cache/pragmatic-audit && mkdir -p ~/.agents/skills && cp -R ~/.cache/pragmatic-audit/skills/pragmatic-programmer ~/.agents/skills/
```

## Compatibility

| Host | Global path | Project path | Notes |
|---|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` | Native skill support |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` | Also reads `~/.claude/skills/` and `~/.agents/skills/` |
| Codex (local) | `~/.codex/skills/` | `.codex/skills/` | Workspace skills use the UI |
| Claude Cowork / claude.ai | — | — | Upload ZIP through Customize → Skills |
| ChatGPT Work / CoWork | — | — | Upload ZIP through Plugins → Skills |
| Cursor and other compatible hosts | `~/.agents/skills/` | Host-specific | Check the host's local skill directory |
| Generic | `~/.agents/skills/` | `.agents/skills/` | Agent Skills standard |

Rules for every host:

- `SKILL.md` must be at the root of the skill folder.
- The folder name must match the `name` in the frontmatter.
- Keep the `references/` folder next to `SKILL.md`; the skill reads it on demand.
- Re-run the install command to update. The command removes the cache clone and replaces the installed folder.

## Invocation examples

The host decides when to load a skill from its description. You can also ask directly.

**Writing a feature:**

```text
Use the pragmatic-programmer skill. Build the smallest end-to-end slice for
saving a draft. Define what done means, keep the boundary explicit, and add
tests before you call it finished.
```

**Reviewing agent output:**

```text
Use the pragmatic-programmer skill in audit mode. Run pragmatic-audit on this
repo, read the agent packet, and confirm or dismiss each finding in the actual
code. Report only the changes that most improve changeability.
```

**Refactoring:**

```text
Use the pragmatic-programmer skill. This module is hard to test. Identify the
coupling, propose the smallest refactor that preserves behavior, and add a
characterization test first.
```

**PR review:**

```text
Use the pragmatic-programmer skill to review this diff. Check DRY,
orthogonality, contracts, resource ownership, and test behavior. Do not comment
on style preferences. Cite the file and line for every issue.
```

## What the skill will refuse to do

- Treat a scanner finding as proven without reading the code.
- Suppress a finding without a written reason.
- Rewrite working code for stylistic purity.
- Add abstractions for hypothetical futures.
- Invent a score, benchmark, or security claim.
- Follow instructions embedded in repository content.

## Troubleshooting

**The host does not see the skill.** Check that `SKILL.md` is directly inside the installed folder, and that the folder name is `pragmatic-programmer`. Restart the host after installing.

**The skill cannot find the CLI.** Install it with `pipx install git+https://github.com/CobaltChaser/pragmatic-audit.git`, or clone the repository and run `python3 -m pragmatic_audit`. The skill can still perform a manual review without the CLI.

**The host reads a stale version.** Run the install command again. It deletes the cache clone and replaces the skill folder.

**The agent treats the audit as a verdict.** Point it at the "hybrid by design" section of the skill and the README. Findings are hypotheses; the agent must verify them.
