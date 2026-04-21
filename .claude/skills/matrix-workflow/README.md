# matrix-workflow

Project-level Claude Code skill that owns the issue-to-deploy developer workflow for this single-repo project.

See `SKILL.md` for the full subcommand reference. The only slash command is `/matrix-workflow <subcommand>`; everything else is either a subcommand arg or a natural-language trigger.

## One-time setup (per developer)

```bash
cd .claude/skills/matrix-workflow
cp config.env.example config.env
# edit config.env, fill in any tokens you have access to
```

`config.env` is gitignored — each developer keeps personal tokens locally.

## Running the tests

```bash
.claude/skills/matrix-workflow/tests/run_all.sh
```
