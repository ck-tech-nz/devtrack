---
name: matrix-workflow
description: "Issue-to-deploy developer workflow for this repo. Triggered by /matrix-workflow <subcommand> (start, pr, reviews, fix, feat, hotfix, review, release) or natural-language cues like 'squash and merge to main'. Covers issue-triage / PR / merge / release / notification tasks."
user-invokable: true
argument-hint: "start i99 | pr | reviews 45 | fix 'login crash' | feat 'dark mode' | review 'branch' | release 'to prod' | 'squash and merge to main'"
---

# matrix-workflow

Single project-level skill that owns the entire issue-to-deploy developer workflow for this repo. Everything lives under this directory; copying it is sufficient to reproduce the workflow elsewhere.

**Repo scope:** single repo, rooted at `./`. No monorepo sub-repos — all commands operate on the current working repo.

**Prerequisite:** `gh auth status` must pass. For Sentry / DevTrakr sources, the developer must copy `config.env.example` → `config.env` and fill in tokens (see `README.md`).

## Invocation

This skill registers **only one slash command**: `/matrix-workflow`. The entries below are **subcommand triggers** parsed from the ARGUMENTS string (or from natural-language cues in chat). They are **not** standalone slash commands — `/fix`, `/feat`, `/wf-start`, etc. do not exist.

Usage patterns:

- `/matrix-workflow start <input>` — input may be `i143`, `sentry#34`, `d12`, or free text
- `/matrix-workflow <bare-source>` — shortcut: bare `sentry#34` / `i143` / `d12` routes to `start`
- `/matrix-workflow fix "<desc>"` / `feat "<desc>"` / `hotfix "<desc>"`
- `/matrix-workflow pr` / `reviews [<pr#>]`
- `/matrix-workflow review "<branch>"` / `release "to test|prod"`
- Chat: `"squash and merge to main"` (no slash)

## Subcommand registry

| Subcommand | Playbook | Purpose |
|---|---|---|
| `start <input>` | `playbooks/wf-start.md` | Start work from a requirement (issue#, sentry#, devtrakr#, or free text) |
| `fix "<desc>"` | `playbooks/fix.md` | Start a bug-fix branch from main |
| `feat "<desc>"` | `playbooks/feat.md` | Start a feature branch from main |
| `hotfix "<desc>"` | `playbooks/hotfix.md` | Interrupt current work for an urgent fix |
| `review "<branch>"` | `playbooks/review.md` | Review another branch against main, then squash-merge |
| `release "to test\|prod"` | `playbooks/release.md` | Push main (or feature branch for test) to env branch + tag + aggregate release notes. Pre-merge test push allowed for `env/test`. |
| `pr` | `playbooks/wf-pr.md` | Self-review + create PR with release-note block |
| `reviews [<pr#>]` | `playbooks/wf-reviews.md` | Address reviewer comments on your own PR |
| *"squash and merge to main"* | `playbooks/squash-merge.md` | Natural-language trigger for single-commit merge |

## Dispatch

When `/matrix-workflow` fires with ARGUMENTS, or a natural-language trigger appears:

1. Parse ARGUMENTS to pick a subcommand. Bare `i<N>`, `sentry#<N>`, `d<N>`, or a pure number routes to `start`.
2. **Load the referenced playbook file and follow it exactly**, step by step.
3. Playbooks reference shared subroutines in `playbooks/atomic-ops.md`. Do not skip or reorder steps.

## Branch-naming convention (unified)

All branches created by this skill use the format:

```
<gh_login>/<identifier>-<english_slug>
```

- `<gh_login>` = `gh api user --jq .login`
- `<identifier>` = issue number (when starting from an issue) OR subcommand type (`fix`/`feat`/`hotfix`)
- `<english_slug>` = `scripts/slug.sh "<english title>"`; no truncation
- Chinese titles are translated to English before slugifying (Claude does this)

Examples:

- `ck/143-all-day-events-not-show-on-device-dashboard-page`
- `ck/fix-login-crash`
- `ck/feat-dark-mode`

## Release-note block format

Every user-facing PR body contains:

```markdown
<!-- RELEASE_NOTE_START -->
## Release Note

### New Features
- ...

### Improvements
- ...

### Bug Fixes
- ...
<!-- RELEASE_NOTE_END -->
```

Add `<!-- RELEASE_NOTE_LOCKED -->` to prevent regeneration. The `release` playbook scans these markers at release time and **prepends** each release's entry (under a `## {tag}` heading) into the month-bucketed file `docs/releases/{YYYY-MM}.md` so newest releases are always at the top.

## Non-goals

- Automating step 3 (writing code and committing). That is ordinary conversation.
- Archiving release notes outside of `release`.
- Notification wiring beyond the stub in `scripts/notify.sh`.
- Discovering or using skills for languages/frameworks — this skill is workflow-only.

## Related files

- `playbooks/` — step-by-step for each trigger
- `scripts/slug.sh`, `scripts/parse_source.sh`, `scripts/notify.sh`
- `sources/github.sh` (live), `sources/sentry.sh` + `sources/devtrakr.sh` (stubs)
- `hooks/post-merge-notify.sh` — PostToolUse hook, registered in `.claude/settings.json`
- `tests/run_all.sh` — umbrella test runner
- `README.md` — onboarding
