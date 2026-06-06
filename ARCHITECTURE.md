# Architecture

This document records the design decisions that shape the Investment Decision System. The narrow list of libraries and tools lives in `TECH_STACK.md`; this document explains how those tools fit together and the conventions that bind the codebase.

## Architectural style: hexagonal (ports and adapters)

The codebase is organised around four layers:

- **Domain** — pure domain models and rules. Functions take domain models as input and return domain models or simple value types as output. No I/O, no global state, no library-specific types in signatures.
- **Application** — use-case logic and ports. It defines `Protocol` contracts for required I/O, projects domain models into report view models, and depends only on the domain.
- **Infrastructure** — concrete implementations of I/O. Adapters implement application ports and translate between external formats (XLSX, Markdown, JSONL, file system) and application/domain models.
- **Presentation** — user-facing delivery adapters. The current presentation adapter is a `typer` CLI that parses user input, delegates to injected application actions, and renders user-facing output.

The boundary contract is strict: domain code never imports `pandas`, `matplotlib`, `openpyxl`, `yaml`, `frontmatter`, `jinja2`, or any I/O library at module level. Validation libraries such as `pydantic` are also boundary tools: they may be used by adapters to validate external payloads, but domain and application code must not import them. Application code never imports infrastructure or presentation code. Presentation code also never imports infrastructure code; concrete adapter wiring lives in the composition root. Import-linter enforces the user-facing dependency flow `presentation -> application -> domain`.

## Composition root

`ids.bootstrap` is the composition root for the CLI application. It is the only production module that imports concrete infrastructure adapters and wires them into application use cases. This keeps presentation code focused on CLI concerns while infrastructure remains hidden behind application ports.

## Project layout

- **`src/` layout** with package `ids`.
- CLI binary name: `ids`.

```
src/ids/
├── bootstrap.py      ← composition root for the CLI application
├── domain/          ← pure domain models and rules
├── application/     ← use cases, ports, report view models
├── infrastructure/  ← I/O implementations
└── presentation/    ← delivery adapters

tests/             ← see "Test strategy" section

inputs/
├── strategy/
│   ├── active-strategy.md
│   └── passive-strategy.md
├── instruments.yaml
├── config.yaml
└── xtb_exports/                    (gitignored)

outputs/
├── reports/
│   ├── weekly/
│   └── monthly/
└── position_log/

specs/                              (user stories — see PRD section 6)
```

## Domain types

- **Frozen dataclasses** model domain concepts: `AccountSummary`, `Position`, and `PortfolioSnapshot`.
- Report-oriented dataclasses live in `ids.application.viewmodels`; they are projections over domain models, not domain entities.
- Dataclasses are `@dataclass(frozen=True)` so they are hashable, comparable, and safe to pass around without aliasing surprises.
- Optional fields use `T | None`.
- Enums for fixed sets of values (`PositionType`, `Outcome`, `AlertSeverity`).

### Money: `Decimal`, never `float`

- Every money value in the domain is `Decimal`.
- `Decimal` is constructed from strings or integers (`Decimal("36.50")`), never from floats.
- `decimal.getcontext()` is configured once at startup with `prec=28` and `rounding=ROUND_HALF_UP`.
- Inside compute functions that use `pandas` or `matplotlib`, conversion to `float` is performed locally; the result is converted back to `Decimal` before crossing the function boundary.

### Currency

- All money values (equity, cash, P&L, purchase value) are in PLN.
- Per-instrument prices (`open_price`, `market_price`, `close_price`, `sl`) are *currency-naive* — plain `Decimal` numbers in whatever currency XTB reports them. The system never compares prices across instruments; only ratios within a single instrument matter for compliance rules.
- This convention works because XTB performs FX internally and reports `Purchase value` / `Sale value` / `Gross P/L` already in PLN.
- Fields ending in `_pln` (e.g., `purchase_value_pln`) make the unit explicit in the domain model.

### Datetime

- All `datetime` values in the domain are *aware* and in `Europe/Warsaw`.
- JSONL snapshot storage persists `datetime` values in UTC (for example `2026-05-02T08:00:00Z`) and converts them back to `Europe/Warsaw` when rebuilding domain models.
- The XTB loader localises naive XLSX timestamps on ingestion; nothing else in the system needs to know about timezones.
- Period boundaries (e.g., "April 2026") are constructed as aware datetimes at midnight Warsaw time.

## Decision records

Short notes on cross-cutting design choices. New entries are appended as one-paragraph bullets, not new top-level sections.

- **Strategy rule constants live in `ids.domain.strategy_rules`** (IDS02). Numeric thresholds for compliance rules are named `Decimal` constants there; rule evaluation code (current compliance alerts, future pre-purchase checks) references the constants rather than hard-coding values, keeping the rulebook a single source of truth.

## Ports and adapters

Every I/O concern is a port. Application code depends only on the port; infrastructure adapters provide the implementation. Tests can substitute fake implementations for any port.

| Port | Default adapter | Purpose |
|------|-----------------|---------|
| `ids.application.ports.PortfolioLoader` | `ids.infrastructure.adapters.XTBPortfolioLoader` | Loads the most recent portfolio snapshot from the configured source. |
| `ids.application.ports.SnapshotStore` | `ids.infrastructure.adapters.JSONLSnapshotStore` | Persists and retrieves the historical series of `PortfolioSnapshot` records. |
| `ids.application.ports.ReportWriter` | `ids.infrastructure.adapters.MarkdownReportWriter` | Renders a view-model into a Markdown report file using `jinja2` templates. |
| `ConfigLoader` | `YAMLConfigLoader` | Reads `inputs/config.yaml` and returns `BenchmarkConfig`. |
| `InstrumentMetadataStore` | `YAMLInstrumentStore` | Reads and writes `inputs/instruments.yaml`. |
| `PositionLogStore` | `MarkdownPositionLogStore` | Reads and writes per-position Markdown files with frontmatter. |
| `ChartWriter` | `MatplotlibChartWriter` | Writes PNG chart files. |

`PortfolioSnapshot` is the canonical domain record of a portfolio state at a point in time (`as_of_date`). It is persisted via `SnapshotStore` and read back by every report-generation flow; the Markdown weekly/monthly reports are views over the snapshot history, not the source of truth. The adapter that loads a snapshot stamps a `source_id` field (for example `xtb:<filename>`) so application/reporting code can render provenance without coupling the domain to the source format.

## File ownership

| Path | Owner | Notes |
|------|-------|-------|
| `inputs/strategy/active-strategy.md` | User | System never reads or modifies this file in MVP. |
| `inputs/strategy/passive-strategy.md` | User | Out of MVP scope. |
| `inputs/instruments.yaml` (values) | User | Sector and region are user-curated. |
| `inputs/instruments.yaml` (stubs) | System | New symbols are appended with empty fields. |
| `inputs/config.yaml` | User | System bootstraps with sensible defaults; user adjusts when rates change. |
| `inputs/xtb_exports/` | User | XLSX files; gitignored. |
| `outputs/reports/weekly/<date>_weekly.md` | System | Regenerated deterministically each run. |
| `outputs/reports/monthly/<period>/` | System | Regenerated deterministically. |
| `outputs/snapshots/<as_of>.jsonl` | System | One file per as_of_date; regenerated deterministically. Gitignored by default — local private data. |
| `outputs/position_log/<date>_<symbol>.md` (frontmatter) | System | Updated on every run. |
| `outputs/position_log/<date>_<symbol>.md` (body) | User | System never overwrites user-written content. |

## Operational conventions

### First-run bootstrap

On every invocation the system creates any missing directories and config files with sensible defaults. Each created artefact is announced explicitly via `rich` output. There is no separate `init` command.

### Latest XTB export selection

The system first globs `inputs/xtb_exports/` for filenames matching the IKZE account ID and parses the `to_date` from the filename. When strict matches exist, the export with the most recent `to_date` is used. If strict matches do not exist, the system falls back to the newest `.xlsx` file by modification time, excluding files whose names clearly declare a different IKZE account ID. In fallback mode, `as_of_date` is derived from the workbook export datetime header (date part). For explicit `--export` paths with non-matching names, the same workbook-header derivation is used; if export datetime cannot be read, the loader fails with a clear error.

### Monthly report period semantics

Reports are bounded by calendar months. Cash flows and realised P&L are accounted strictly to the period end. End-of-period equity uses the latest XTB export, even if it was taken after the period end; the report includes a snapshot disclaimer naming the export date. Users who want strict month-end equity can take XTB exports with `to_date` aligned to the period boundary.

### Per-trade P&L

Per-trade P&L is the gross P/L XTB reports for closed positions (price-only). Dividends and interest are reported separately at the portfolio level under "passive income from portfolio"; they are not attributed to individual trades. This keeps the per-trade view aligned with the strategy's trading-skill focus and keeps the Real vs Discipline Twin comparison clean.

### Idempotent reports

Running a report command twice for the same period produces the same output, assuming the same input data. Existing report files are overwritten on regeneration; there is no append-only behaviour and no timestamps in filenames beyond the period date.

### Snapshot store

Every report run persists the parsed `PortfolioSnapshot` to `outputs/snapshots/<as_of>.jsonl` before rendering. This is the substrate for all time-series views (equity curve, drawdown, Discipline Twin). The store is local-only by default — `outputs/` is gitignored to keep personal financial data private. One file per `as_of_date`, deterministically serialized, with `datetime` fields stored in UTC. An owner who wants to version snapshots privately should do so in a separate private repo, not the public codebase.

## Presentation and CLI structure

- Presentation code lives under `ids.presentation`; the current adapter is `ids.presentation.cli`.
- Single binary `ids` with subcommands: `report weekly`, `report monthly`, `check-purchase`.
- Subcommands accept flags or fall back to interactive prompts (`typer` pattern).
- All user-facing output uses `rich`; diagnostic logging uses the standard `logging` module.
- The exit code reflects success or rule violations (for example `check-purchase` returns non-zero when any rule fails).

## Test strategy

Four test groups mirror the source layers and user-facing boundary:

- **Domain unit tests** — pure-function tests; construct domain models in code, call functions, assert on returned models. No fixtures from disk. Coverage target ~90%.
- **Application unit tests** — verify use-case projections and port contracts without infrastructure dependencies.
- **Infrastructure adapter tests** — verify each adapter's translation contract using small, anonymised fixture files in `tests/fixtures/`. Coverage target ~70%.
- **End-to-end smoke tests** — run the CLI against a small sample data set and verify the produced files; mix snapshot tests (for stable rendered output) and structural assertions (for files where exact byte equality would be fragile).

Overall coverage target: ~80%. Coverage is a guide, not a ceiling.

Tests mirror the source structure under `src/ids/`:

```
tests/
├── domain/          ← pure domain tests, no fixtures from disk
├── application/     ← use-case and port-contract tests
├── infrastructure/  ← adapter translation tests with anonymised fixtures
├── presentation/    ← CLI/presentation tests
├── fixtures/        ← sample XLSX, instruments.yaml, etc.
└── e2e/             ← CLI smoke tests against sample data
```

## Quality gates

- **Pre-commit hooks** run `ruff check` and `ruff format` on staged files. Type checks and tests are not in pre-commit (they run in CI).
- **CI (GitHub Actions)** runs on every push: `ruff check`, `ruff format --check`, `basedpyright`, `pytest -m unit`, `pytest`.
