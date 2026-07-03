# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

## Codex Notes

### Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ccf33ec3 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Build & Quality Gates

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and Python 3.12+.

```bash
uv sync                       # Install dependencies (incl. dev group)
uv run pytest                 # Run test suite
uv run pytest -n auto         # Run tests in parallel (pytest-xdist)
uv run pytest --cov=ids       # Run with coverage
uv run ruff check .           # Lint
uv run ruff format .          # Format
uv run basedpyright           # Type-check, including Any leakage gate
uv run semgrep --config .semgrep/blocker.yml --error
uv run semgrep --config .semgrep/advisory.yml         # Advisory Semgrep feedback
uv run lint-imports           # Architecture contracts (importlinter)
uv run ids --help             # Run the CLI entrypoint
```

After code changes, review Semgrep advisory findings and handle each per the protocol
documented at the top of [`.semgrep/advisory.yml`](.semgrep/advisory.yml) (default: fix;
accept only by citing the governing `ARCHITECTURE.md` clause).

Pre-commit hooks are configured; install with `uv run pre-commit install`.

## Architecture Overview

**Investment Decision System (IDS)** — IKZE portfolio automation CLI. Reads XTB XLSX exports, persists portfolio snapshots, evaluates compliance rules, and renders Markdown reports.

Hexagonal (ports & adapters), four layers under `src/ids/`:

- **`domain/`** — pure business logic; no I/O library imports.
- **`application/`** — use-case orchestration, ports, and report view models.
- **`infrastructure/`** — concrete I/O adapters (XLSX, JSONL, Markdown, templates).
- **`presentation/`** — user-facing delivery adapters, currently the `typer` CLI.

`outputs/snapshots/<as_of>.jsonl` is the canonical time-series substrate; reports are views over snapshot history. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design record and [`TECH_STACK.md`](TECH_STACK.md) for the library list.

## Conventions & Patterns

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- **Per-bead workflow**: ensure master is up-to-date → new branch per bead → work → open PR → CI must be green before the bead is considered done.
