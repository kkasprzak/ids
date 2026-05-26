# Investment Decision System (IDS)

Spec-driven, hexagonal Python toolkit for analyzing XTB brokerage portfolios — generates daily snapshots, compliance alerts, and investment discipline reports.

## What it is

IDS is a personal-use automation suite for an IKZE portfolio held at XTB. It ingests XTB account XLSX exports and produces weekly portfolio reviews, monthly performance evaluations, and pre-purchase compliance checks against a user-defined trading strategy. The product is a single-user tool: design decisions favour clarity and discipline for one rigorous user over multi-user discoverability.

See [`PRD.md`](PRD.md) for the full product brief and [`specs/`](specs/) for individual feature specifications (IDS01–IDS12).

## Quick start

```bash
uv sync                          # install dependencies (incl. dev group)
export IDS_IKZE_ACCOUNT_ID=...   # your XTB IKZE account ID (or use --ikze-account-id)
uv run ids report weekly         # generate the weekly snapshot from inputs/xtb_exports/
```

Place XTB XLSX exports under `inputs/xtb_exports/` (gitignored). Reports and snapshots land under `outputs/` (also gitignored — your data stays local).

## Development

```bash
uv run pytest -n auto                # run tests in parallel
uv run pytest                        # run the same test suite CI runs
uv run pytest --cov=ids --cov-report=term-missing --cov-report=html
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run pyright                       # type-check (strict on src/)
uv run pre-commit install            # enable git hooks
```

The HTML coverage report is written to `htmlcov/index.html`. Coverage is informational only;
CI runs tests without a coverage gate.

## Architecture

Hexagonal (ports & adapters), four layers under `src/ids/`:

- `domain/` — pure domain models and rules; no I/O library imports
- `application/` — use-case orchestration, ports, and report view models
- `infrastructure/` — concrete I/O adapters (XLSX, JSONL, Markdown, templates)
- `presentation/` — user-facing delivery adapters, currently the `typer` CLI

`outputs/snapshots/<as_of>.jsonl` is the canonical time-series substrate; reports are views over snapshot history.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design record, [`TECH_STACK.md`](TECH_STACK.md) for the library list, and [`TEST_STRATEGY.md`](TEST_STRATEGY.md) for the testing approach.

## Task tracking

Issue tracking uses [beads](https://github.com/gastownhall/beads) with the Dolt database synced to a **separate private remote** (`.beads/` is gitignored in this repo). The public repo holds code; backlog and decision history live elsewhere by design.

To set up beads on a new machine:

```bash
bd bootstrap   # reads sync.remote from .beads/config.yaml and clones the Dolt DB
```

## License

Personal project. No license granted at this time — code is published for reference and learning.
