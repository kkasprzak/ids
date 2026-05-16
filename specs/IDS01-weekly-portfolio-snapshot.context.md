# IDS01 — Weekly portfolio snapshot from XTB export

## Purpose (walking skeleton)

The simplest version of the weekly report — just the portfolio state without alerts, logs, or analysis. It establishes the foundation that subsequent SPECs build on (XTB ingestion + Markdown report generation + CLI subcommand pattern).

## Input

- **XTB export file** (`.xlsx`) containing:
  - `Open Position` sheet — currently open positions (symbol, open date, open price, market price, volume, gross P/L)
  - Account header section — Balance (cash), Equity (total value)
- The export is a file present in a designated input location — the system reads it and the user does not specify a path manually (the latest available export is selected automatically).

## Output

- **Markdown report file** for the weekly review with two sections:
  - **Portfolio summary** — Equity, Cash, cash %, number of open positions
  - **Open positions table** — for each position: symbol, open date, days held, open price, market price, P&L in PLN, P&L in %
- No alerts, no references to the position log, no charts, no benchmark comparison.

## Which User problem it addresses (PRD section 2)

Addresses part of the problem *"continuous monitoring of open positions [is] not performed systematically"* — provides a basic "what's in my portfolio" mechanism without opening the XTB app. This is **not a full solution** to the problem (no alerts, no analysis), only the foundation — but independently valuable: the user sees the portfolio state in one place, in a versioned form.

## Which Functional requirements it covers (PRD section 5)

- **XTB data ingestion** — first basic version (parsing `Open Position` sheet + account header is enough; full parsing of all four sheets can come in later SPECs when needed).
- **Weekly review report** — simplest version (only portfolio summary + open positions table; alerts, log status, and action items come in subsequent SPECs).
- **CLI interface** — first subcommand (`report weekly`); establishes the pattern for subsequent commands.
- **Local execution and Git versioning** — establishes file paths (`outputs/reports/weekly/<date>_weekly.md`) and the convention that reports are versioned in Git while XTB XLSX exports remain local and gitignored.
