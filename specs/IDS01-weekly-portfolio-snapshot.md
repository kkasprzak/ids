# SPEC: Weekly portfolio snapshot from XTB export (walking skeleton)

## User Story

As an **active investor managing my IKZE portfolio**, I want **a weekly Markdown snapshot of my current portfolio (cash, equity, open positions with P&L) generated from my latest XTB export**, so that **I have a versioned, file-based view of my portfolio that I can review without opening the XTB app**.

## Context

This is the **walking skeleton** of the Investment Decision System. It proves a concrete end-to-end path: **XTB XLSX export → parse → Markdown report**. The patterns established here (latest-export auto-discovery, Markdown report generation, CLI subcommand structure, file path conventions) will be reused by every subsequent SPEC.

Intentionally narrow scope: the snapshot contains only a portfolio summary and a table of open positions. No alerts, no position log, no benchmark comparison, no charts. These responsibilities are explicitly deferred to dedicated SPECs (IDS02–IDS12) that build on top of this foundation.

The minimal scope keeps the first deliverable shippable in a small time window and enables fast feedback on the integration approach before adding more capabilities.

## Acceptance Criteria

### XTB export ingestion

- [ ] GIVEN one XTB XLSX export is present in the designated input location
      WHEN the weekly snapshot is generated
      THEN that export is read and parsed without manual path specification

- [ ] GIVEN multiple XTB XLSX exports are present in the input location
      WHEN the weekly snapshot is generated
      THEN the latest export (by filename or modification date) is selected

- [ ] GIVEN the XTB export contains an Open Position sheet and an account summary header
      WHEN the export is parsed
      THEN account-level Balance and Equity values are extracted
      AND each open position's symbol, open date, open price, market price, volume, and gross P&L are extracted

### Report content

- [ ] GIVEN an XTB export has been parsed
      WHEN the weekly snapshot Markdown is produced
      THEN it contains a Portfolio summary section listing equity, cash, cash percentage, and number of open positions

- [ ] GIVEN one or more open positions exist
      WHEN the snapshot is produced
      THEN it contains an Open positions table with one row per position, including: symbol, open date, days held since open, open price, current market price, P&L in PLN, P&L in percent

- [ ] GIVEN no open positions exist
      WHEN the snapshot is produced
      THEN the Open positions table is replaced with a clear "no open positions" indication

### Report file output

- [ ] GIVEN the snapshot has been generated
      WHEN it is written to disk
      THEN the file is placed under `outputs/reports/weekly/`
      AND the filename includes the date the report was generated

- [ ] GIVEN a snapshot for the same date has previously been generated
      WHEN the snapshot is regenerated
      THEN the existing file is replaced with the new content (deterministic re-run)

### CLI invocation

- [ ] GIVEN the system is installed
      WHEN the user invokes the weekly report subcommand
      THEN the report is generated and the path of the produced file is displayed in the terminal

- [ ] GIVEN no XTB export is present in the input location
      WHEN the weekly report subcommand is invoked
      THEN an error is shown explaining that no input data is available

## Out of Scope

- Alerts of any kind (stop-loss breach, profit-taking trigger, missing SL, cash reserve, concentration) — covered by IDS02 and IDS06
- Position log generation and missing-rationale tracking — covered by IDS03 and IDS04
- Sector / geographic concentration analysis — covered by IDS05 and IDS06
- Pre-purchase compliance check — covered by IDS07
- Monthly report, charts, benchmarks, closed-trade statistics, reflection prompts, Discipline Twin — covered by IDS08–IDS12
- Parsing of `Closed Position History`, `Pending Orders History`, and `Cash Operation History` sheets — added when later SPECs require that data
- Historical price fetching from external sources
