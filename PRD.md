# Product Requirement Document (PRD) - Investment Decision System

## 1. Product overview

The Investment Decision System is an automation suite that supports active management of an IKZE portfolio held at XTB by ingesting account data exports and a reference investment strategy document to generate three automated outputs: continuous monitoring of open positions for strategy compliance and risk threshold violations, cyclical performance evaluation against the strategy and passive benchmarks (bank deposit, rental property yield), and initial screening of new investment instruments aligned with the strategy. It operates as a learning lab on a capped capital pool defined by IKZE regulations, where the active momentum-trading strategy is validated against passive alternatives before any decision to extend the strategy beyond the learning-lab capital. The automation closes the build-implement-evaluate-modify learning cycle within minutes per iteration, making it sustainable under recurring time constraints.

## 2. User problem

Active management of an IKZE investment portfolio requires three time-intensive activities: continuous monitoring of open positions, cyclical evaluation of results against the defined strategy and passive benchmarks (savings account yield, rental yield), and discovery of new investment instruments. Under recurring time constraints, these activities are often not performed systematically — as a result, open positions violate strategy rules (missing stop-losses, losses significantly exceeding defined thresholds), decisions rely on intuition rather than hard data, and the learning cycle — build, implement, evaluate, modify — does not close, blocking progress toward long-term financial goals. This project automates monitoring, strategy compliance evaluation, benchmark comparison, and initial instrument screening, reducing manual overhead so the learning cycle closes within available time and operates on hard data instead of feelings.

## 3. Success metrics

- **Strategy validation outcome**: After a sufficient observation window, the user can make an evidence-based go/no-go decision on whether to extend the active IKZE strategy beyond the learning-lab capital, supported by hard data on risk-adjusted returns versus passive benchmarks (bank deposit yield, rental property yield).
- **Strategy compliance**: 100% of open positions have stop-loss orders configured per strategy rules. Any position breaching a defined risk threshold (loss exceeds −5% from entry, portfolio drawdown approaches −10% limit, sector or geographic concentration breaches soft limit) is detected and reported within one business day.
- **Cycle closure**: The build-implement-evaluate-modify cycle completes at its defined cadence (weekly portfolio review, monthly performance evaluation, quarterly strategy modification) over a sustained period, without iterations being skipped due to time constraints.
- **Manual overhead**: A complete weekly portfolio review takes under 15 minutes including data import; a monthly evaluation takes under 30 minutes; instrument screening for new opportunities takes under 60 minutes per cycle.
- **Decision traceability**: Every position open, position close, and strategy modification has documented rationale linking the decision to either a strategy rule or a data-driven evaluation insight, enabling retrospective learning analysis.
- **Execution discipline calibration**: The system quantifies the PLN-denominated cost or value of discretionary deviations from strategy rules versus mechanical execution, providing the user with a definitive answer to whether their judgment adds alpha to the strategy or whether strict mechanical execution would yield better outcomes.

## 4. Product borders

- **In scope:** IKZE portfolio at XTB (account `<IKZE_ACCOUNT_ID>`, configured via the `IDS_IKZE_ACCOUNT_ID` environment variable); active momentum-trading strategy as defined in the project's strategy document; ingestion of XTB account XLSX exports as the primary data source; pull-based, on-demand report generation triggered manually by the operator; weekly portfolio review report (compliance checks, risk-threshold alerts, trailing-stop suggestions); monthly performance evaluation report (returns vs passive benchmarks, equity curve, drawdown, closed-trade statistics, Real vs Discipline Twin comparison); embedded chart visualizations in monthly reports (portfolio equity vs benchmarks, drawdown over time, P&L per position); pre-purchase compliance check (sector and geographic concentration limits, position sizing, cash reserve); position log with auto-generated stubs from XTB data and operator-filled rationale; local execution with reports, charts, and position log versioned in this Git repository.
- **Out of scope:** general XTB trading account (any non-IKZE account, e.g. `<XTB_ACCOUNT_ID>`) and the passive global-diversification strategy (currently in DRAFT); real-time and intraday monitoring of any kind; direct API or scraping integration with XTB; automated modification of the strategy document (user is the sole author); discovery and momentum scanning of new investment instruments (deferred until the strategy defines concrete momentum criteria); AI-generated rationale for position log entries; quarterly strategy-modification report (deferred — manual reflection in the early months); external market data sources for historical prices (deferred until step-curve granularity proves insufficient); web dashboards, mobile apps, and external notification channels (email, Slack, push).

## 5. Functional requirements

- **XTB data ingestion:** The system reads XTB account XLSX exports from a designated input directory. It parses four sheets (closed positions, open positions, pending orders, cash operation history) and the account summary header. The latest export is auto-selected by filename or modification date; the user does not need to specify a path explicitly.
- **Position log management:** For each position detected in XTB data (open or closed), the system generates a corresponding Markdown file under `outputs/position_log/` named `<YYYY-MM-DD>_<SYMBOL>.md`. Each file contains frontmatter with position metadata (id, symbol, type, dates, prices, P&L, status) and Markdown sections for user-filled rationale (open rationale, close rationale, review history). The system never overwrites user-written content; it only appends or updates the metadata frontmatter on subsequent runs.
- **Strategy compliance monitoring:** The system evaluates open positions against deterministic rules from the active strategy: stop-loss configured in XTB, current loss vs. −5% threshold from entry, profit threshold +15% (50% realization trigger), position size limits per instrument type, cash reserve minimum (10% of portfolio), and sector and geographic concentration soft limits (40% / 50%). Each violation or warning is reported as an alert with a recommended action.
- **Performance evaluation against benchmarks:** The system computes portfolio total return and compares it against passive benchmarks: savings-account yield and rental yield. Both benchmarks are configured by the operator and can be updated as market assumptions change. Both period and cumulative-since-inception views are produced for monthly reports.
- **Chart visualization:** Monthly reports include three embedded charts: equity curve over time versus passive benchmarks, portfolio drawdown from peak (step-curve based on transaction-time data), and P&L per position covering both open and closed positions.
- **Weekly review report:** On invocation, the system generates a Markdown report containing portfolio summary, an open-positions table with per-position alerts, action-required alerts (stop-loss breaches, profit-taking opportunities, missing stop-loss configuration in XTB, concentration warnings), position log status (positions missing rationale), and a consolidated action list for the week.
- **Monthly evaluation report:** On invocation, the system generates a Markdown report containing performance summary versus benchmarks (period and cumulative), embedded charts, closed-trade statistics, strategy compliance retrospective for the period, a Real vs Discipline Twin comparison (see below), and reflection prompts for strategy review.
- **Discipline Twin (mechanical strategy shadow execution):** The system maintains a virtual shadow portfolio that mechanically applies strategy exit rules to the same positions opened by the user (strict −5% stop-loss from entry, +15% partial profit-taking, mechanical trailing stops where determinable from available data). Monthly reports include a Real vs Twin comparison showing the cumulative PLN cost or alpha of discretionary execution versus mechanical strategy execution, an equity-curve overlay of both portfolios, and a per-position breakdown of what the user did versus what mechanical discipline would have done.
- **Pre-purchase compliance check:** The system accepts a candidate purchase (symbol, instrument type, position value in PLN) and validates it against strategy rules: position size limits, cash reserve impact, sector and geographic concentration impact, and presence of an instruments.yaml entry. It outputs a structured verdict with each rule's pass/fail/warning status. Missing inputs are interactively prompted from the user.
- **Instrument metadata management:** The system maintains an `instruments.yaml` file mapping each symbol to its sector and region. On first run, it creates a stub containing all symbols from the current portfolio with empty sector/region fields. Symbols not present in the metadata file trigger a warning until the user fills in their sector and region values manually.
- **CLI interface:** All capabilities are exposed through a single command-line entry point with subcommands (e.g., `report weekly`, `report monthly`, `check-purchase`). The CLI provides built-in help, clear error messages, and supports both flag-based and interactive input modes for commands that require user input.
- **Local execution and Git versioning:** Strategy documents, instrument metadata, generated reports and charts, and the position log are versioned in this Git repository. XTB XLSX exports remain on the local filesystem and are excluded from version control.

## 6. User stories

User stories are maintained as individual SPEC files under [`specs/`](specs/). Each SPEC follows the walking-skeleton pattern (user story, context, acceptance criteria in Given/When/Then form, out of scope) and ships as an independent vertical slice. A companion `<id>.context.md` file alongside each SPEC describes its inputs, outputs, and the user-problem / functional-requirement coverage from this PRD.

The IDS prefix denotes creation order; the actual implementation order is decided separately.

- [IDS01 — Weekly portfolio snapshot from XTB export (walking skeleton)](specs/IDS01-weekly-portfolio-snapshot.md) ([context](specs/IDS01-weekly-portfolio-snapshot.context.md))
- [IDS02 — Strategy compliance alerts in weekly snapshot](specs/IDS02-strategy-compliance-alerts-weekly.md) ([context](specs/IDS02-strategy-compliance-alerts-weekly.context.md))
- [IDS03 — Position log with auto-generated stubs](specs/IDS03-position-log-stubs.md) ([context](specs/IDS03-position-log-stubs.context.md))
- [IDS04 — Missing rationale alerts in weekly snapshot](specs/IDS04-missing-rationale-alerts-weekly.md) ([context](specs/IDS04-missing-rationale-alerts-weekly.context.md))
- [IDS05 — Instrument metadata management](specs/IDS05-instrument-metadata-management.md) ([context](specs/IDS05-instrument-metadata-management.context.md))
- [IDS06 — Concentration & position-size alerts in weekly snapshot](specs/IDS06-concentration-and-size-alerts-weekly.md) ([context](specs/IDS06-concentration-and-size-alerts-weekly.context.md))
- [IDS07 — Pre-purchase compliance check](specs/IDS07-pre-purchase-compliance-check.md) ([context](specs/IDS07-pre-purchase-compliance-check.context.md))
- [IDS08 — Monthly performance vs benchmarks](specs/IDS08-monthly-performance-vs-benchmarks.md) ([context](specs/IDS08-monthly-performance-vs-benchmarks.context.md))
- [IDS09 — Monthly closed-trade statistics](specs/IDS09-monthly-closed-trade-statistics.md) ([context](specs/IDS09-monthly-closed-trade-statistics.context.md))
- [IDS10 — Monthly chart visualizations](specs/IDS10-monthly-chart-visualizations.md) ([context](specs/IDS10-monthly-chart-visualizations.context.md))
- [IDS11 — Monthly reflection prompts](specs/IDS11-monthly-reflection-prompts.md) ([context](specs/IDS11-monthly-reflection-prompts.context.md))
- [IDS12 — Real vs Discipline Twin comparison](specs/IDS12-real-vs-discipline-twin.md) ([context](specs/IDS12-real-vs-discipline-twin.context.md))

## 7. User personas

### Active Investor

The Active Investor is the primary user of the system — the same role that designs the strategy, executes trades in XTB, fills rationale in the position log, and ultimately decides whether to extend the strategy beyond the learning-lab capital. The product is a single-operator automation suite, not a multi-user platform; design decisions favour clarity and discipline for one rigorous operator over discoverability for newcomers.

**Core context:** An individual investor managing an IKZE portfolio at XTB with limited operational time. Time is the binding constraint and execution is intentionally single-operator. The IKZE statutory annual contribution cap defines this as a learning lab on a small, capped capital pool before any decision to extend the strategy further.

**Key motivations:**

- Financial independence and the freedom to choose passion-aligned work that flows from it.
- Learning to invest competently through deliberate practice on a small capital pool before risking larger sums.
- Validating whether an active momentum-trading strategy beats passive alternatives (bank deposit, rental property yield) clearly enough to justify extending the strategy beyond the learning-lab capital.
- Closing the build-implement-evaluate-modify learning cycle within limited available time so the cycle actually compounds instead of stalling.

**Key concerns:**

- Discipline gap between strategy on paper and execution in practice (e.g., positions held well past the −5% stop-loss threshold without protective orders set in XTB).
- Making decisions on intuition rather than hard data, particularly at the moment of buying when emotion is strongest.
- Cycle closure — the evaluate-modify half of the loop falling apart under time pressure, leaving evaluation data unused.
- Capital opportunity cost during the validation period — non-active capital sitting at sub-inflation yields while purchasing power erodes.

**Operating modes:**

- **Weekly review.** Short and action-oriented, scanning the weekly snapshot for compliance violations, missing rationale, and concrete actions to take this week. Designed for quick consumption on a phone or alongside the XTB app.
- **Pre-purchase check.** Single-shot validation of a candidate trade against the strategy's rules. High emotional stakes (the user is about to commit capital), short attention span, often executed on mobile.
- **Monthly evaluation.** Longer and more reflective, sitting with the monthly report — performance vs benchmarks, charts, closed-trade statistics, and the Real vs Discipline Twin comparison — to consider whether the strategy is working and what might need to change.
- **Strategy authoring.** Infrequent but high-stakes; edits the active strategy document directly when monthly insights warrant a change. The user is the sole author; the system never rewrites the strategy.

**Technical comfort:** High. Comfortable with command-line tools, Markdown, Git workflows, and YAML configuration. Edits files directly in editors like VS Code or Obsidian rather than expecting GUIs. Product artefacts (PRD, SPECs, reports) are written in English; the strategy document and personal reflections may be written in the user's first language.
