# Test Suite Guide

Companion to `TEST_STRATEGY.md` (which explains rules and philosophy).
This file explains **what each test file protects** and **where to look** when changing code.

## Quick orientation

```
tests/
├── domain/            ← pure logic tests — no filesystem, no I/O
│   ├── conftest.py    ← Object Mother factories: make_snapshot, make_position, make_account
│   ├── test_models.py
│   ├── test_ports.py
│   └── test_weekly_snapshot.py
├── adapters/          ← I/O contract tests — real filesystem via tmp_path
│   ├── conftest.py    ← make_xlsx: builds synthetic XTB-like workbooks
│   ├── test_formatters.py
│   ├── test_jsonl_snapshot_store.py
│   ├── test_markdown_report_writer.py
│   ├── test_xtb_filename.py
│   └── test_xtb_portfolio_loader.py
├── cli/
│   └── test_decimal_context.py
├── e2e/
│   └── test_report_weekly.py  ← full CLI smoke test + golden file diff
└── fixtures/
    ├── account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx  ← committed anonymized XTB export fixture
    └── expected/
        └── weekly_2026-05-02.md  ← golden Markdown output
```

---

## Domain tests (`tests/domain/`)

**Marker:** `pytest.mark.unit` — run with `uv run pytest -m unit`

These are pure-function tests. They never touch the filesystem, network, or any I/O library.
If a test here fails, the bug is in `src/ids/domain/`.

### `conftest.py` — Object Mother factories

Defines `make_account`, `make_position`, `make_snapshot` with sensible round-number defaults.
Every test that needs a domain object calls these factories — never copies values from real data.

```python
position = make_position(symbol="PKN.PL", gross_pl_pln=Decimal("100"))
snapshot = make_snapshot(positions=(position,))
```

The factories are also exposed as pytest fixtures so tests can receive them via parameter injection.

### `test_weekly_snapshot.py` — the domain service contract

Protects `build_weekly_snapshot()` in `src/ids/domain/services/weekly_snapshot.py`.

Key behaviors locked down:
- Empty portfolio → zero count, empty rows
- P&L % = `gross_pl / purchase_value * 100`, rounded to 2dp
- Cash % = `balance / equity * 100`
- Zero-division guards (equity=0 or purchase_value=0) → 0.00, no exception
- Rows sorted by P&L % descending, ties broken alphabetically by symbol
- `days_held` = `as_of_date - open_date` (not "now − open_date")

**When to inspect:** any change to `src/ids/domain/services/weekly_snapshot.py` or `src/ids/domain/viewmodels.py`.

### `test_models.py` — domain model invariants

Protects frozen dataclass invariants: schema_version default, enum values.

### `test_ports.py` — error hierarchy

Protects that all port errors (`NoPortfolioAvailableError`, `PortfolioMalformedError`, etc.)
are subclasses of `IDSError`. This matters because CLI error handling catches `IDSError`.

---

## Adapter tests (`tests/adapters/`)

**Marker:** `pytest.mark.integration` — run with `uv run pytest -m integration`

These tests write to the real filesystem using pytest's `tmp_path` fixture.
`tmp_path` provides a temporary directory unique to each test, automatically cleaned up.
No test can affect another's files. If a test here fails, the bug is in `src/ids/adapters/`.

### `conftest.py` — `make_xlsx` factory

Writes a minimal synthetic XTB-like workbook to a given path.
Account 99999999, invented position IDs and monetary values — **no real brokerage data ever**.
Also exports `_HEADER` (the position column list) for tests that build custom workbooks.

### `test_xtb_filename.py` — filename parser

Protects `parse_xtb_filename()` and `parse_xtb_account_id()` in `src/ids/adapters/xtb_filename.py`.
Covers valid patterns, wrong account ID, malformed dates.

### `test_xtb_portfolio_loader.py` — XTB XLSX ingestion

The largest test file (28 tests). Protects `XTBPortfolioLoader` in
`src/ids/adapters/xtb_portfolio_loader.py`.

Grouped by concern:
| Group | What it guards |
|-------|---------------|
| Happy-path parsing | Single/multiple positions, empty table, SL=0→None, fractional volume, datetime localisation |
| File selection | Strict filename → as_of_date from filename; fallback by mtime → as_of_date from workbook header |
| Sheet discovery | Prefix-first (`OPEN POSITION `); semantic fallback for non-standard names; ambiguity error |
| Header scanning | Account labels / position headers / export datetime found even when shifted past original row windows |
| Column normalisation | Whitespace/case variants; `Gross P&L` alias; missing field names logical error message |
| Footer detection | Non-exact "Total" strings (TOTAL, padded); malformed position rows still raise |
| Error paths | Wrong account ID, no directory, no matching files, missing sheet, missing columns |

**When to inspect:** any change to `XTBPortfolioLoader`, `_POSITION_COLUMN_SCHEMA`, scan caps,
or footer/sheet-discovery logic.

### `test_jsonl_snapshot_store.py` — snapshot persistence

Protects `JSONLSnapshotStore` in `src/ids/adapters/jsonl_snapshot_store.py`.
Covers save/load round-trip, UTC datetime serialization, schema versioning, not-found errors, and malformed snapshot errors.

**When to inspect:** any change to snapshot serialisation or the `SnapshotStore` port.

### `test_markdown_report_writer.py` — Markdown rendering

Protects `MarkdownReportWriter` in `src/ids/adapters/markdown_report_writer.py`.
Writes a report to `tmp_path`, reads it back, asserts content.

**When to inspect:** any change to Jinja2 templates under `src/ids/adapters/templates/`.

### `test_formatters.py` — number/currency formatting

Protects formatting helpers (`format_pln`, `format_pct_signed`, etc.) in
`src/ids/adapters/formatters.py`.
Parametrised over positive, negative, and zero values; checks non-breaking spaces and minus sign.

---

## CLI test (`tests/cli/test_decimal_context.py`)

**Marker:** `pytest.mark.unit`

Protects that importing `ids.cli` configures `decimal.getcontext()` with `prec=28`
and `ROUND_HALF_UP`. This must happen before any Decimal arithmetic.

---

## E2E tests (`tests/e2e/test_report_weekly.py`)

**Marker:** `pytest.mark.e2e`

Full CLI integration: `CliRunner` invokes `ids report weekly` with a committed anonymized XLSX fixture,
compares the output Markdown byte-for-byte against `tests/fixtures/expected/weekly_2026-05-02.md`.

`monkeypatch.chdir(tmp_path)` makes the CLI think `inputs/` and `outputs/` are inside the
temp directory. `monkeypatch.setattr(report_cli, "_clock", lambda: FIXED_NOW)` uses the
documented CLI test seam to pin the clock so `generated_at` is deterministic.

Tests in this file:
| Test | What it locks down |
|------|--------------------|
| `test_weekly_report_happy_path` | Golden output — exact byte match against the committed file |
| `test_no_export_fails_with_actionable_message` | Missing `xtb_exports/` → exit 1, path in stderr |
| `test_missing_account_id_fails_with_actionable_message` | Missing env var → exit 2, env name in stderr |
| `test_invalid_export_file_fails_with_as_of_derivation_message` | Empty XLSX → clear error |
| `test_malformed_export_fails_with_loader_message` | Wrong sheet name → `OPEN POSITION` in stderr |
| `test_idempotency` | Running twice produces identical bytes both times |
| `test_weekly_report_export_override` | `--export` flag with standard filename |
| `test_weekly_report_export_override_accepts_custom_filename` | `--export` with non-standard filename |

**When to inspect:** any change to `src/ids/cli/report.py`, Jinja2 templates,
or the overall report flow. If the golden file needs updating, run:

```bash
# 1. Run the CLI once against committed fixture and capture output:
IDS_IKZE_ACCOUNT_ID=99999999 uv run ids report weekly \
    --export tests/fixtures/account_ikze_99999999_pl_xlsx_2024-12-31_2026-05-02.xlsx

# 2. Copy the generated report to the expected fixture path, review the diff, then commit.
cp outputs/reports/weekly/2026-05-02_weekly.md tests/fixtures/expected/weekly_2026-05-02.md
```

---

## Where to look when changing…

| Changing | Tests to run / inspect |
|----------|----------------------|
| `build_weekly_snapshot()` domain logic | `tests/domain/test_weekly_snapshot.py` |
| `XTBPortfolioLoader` parsing | `tests/adapters/test_xtb_portfolio_loader.py` |
| `_POSITION_COLUMN_SCHEMA` / aliases | Column-normalisation group in loader tests |
| JSONL snapshot format | `tests/adapters/test_jsonl_snapshot_store.py` |
| Markdown templates | `tests/adapters/test_markdown_report_writer.py` + golden file |
| CLI wiring / `report weekly` | `tests/e2e/test_report_weekly.py` |
| Number formatting | `tests/adapters/test_formatters.py` |
| Domain model fields | `tests/domain/test_models.py`, `test_ports.py` |
| Decimal context setup | `tests/cli/test_decimal_context.py` |

---

## Running tests

```bash
uv run pytest                    # full suite
uv run pytest -m unit            # domain + cli only (fast, no filesystem)
uv run pytest -m integration     # adapter tests
uv run pytest -m e2e             # CLI smoke tests
uv run pytest -n auto            # parallel (pytest-xdist)
uv run pytest --cov=ids          # with coverage

# Quality gates (run before committing)
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

`basedpyright` is the strict typing gate and fails on `Any` leaks.

All markers are defined in `pyproject.toml`. Tests marked `unit` complete in milliseconds.
`tmp_path` tests are slightly slower but still under 1 second for the full suite.
