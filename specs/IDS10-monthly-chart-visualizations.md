# SPEC: Monthly chart visualizations

**Depends on:** IDS08 (monthly report scaffold, period selection, `Cash Operation History` ingestion, benchmarks), IDS09 (closed-trade aggregates and per-trade context).

## User Story

As an **active investor evaluating my strategy over time**, I want **the monthly report to embed three charts — portfolio equity vs passive benchmarks, drawdown from peak, and P&L per position**, so that **I can see at a glance how the strategy is tracking, when drawdowns happened, and which positions are net contributors or drags on performance**.

## Context

Numbers in tables answer "what happened"; charts answer "when, how, and how shaped". For a momentum-trading strategy where drawdowns and benchmark-relative trajectory are central, charts are not decorative — they are the part of the report most likely to drive a strategy modification.

The MVP scope is exactly three charts, chosen because each addresses a distinct strategic question:

- **Equity curve vs benchmarks** — is the strategy beating the alternatives I would otherwise put capital into?
- **Drawdown from peak** — how close have I come to the −10% portfolio drawdown rule, and when?
- **P&L per position** — which trades are doing the heavy lifting and which are the dead weight?

A deliberate constraint sits underneath the equity and drawdown charts: the system has no historical market-price source (yfinance and similar are explicitly out of MVP per PRD product borders). The curves are therefore reconstructed as **step curves** — walking through `Cash Operation History` events in chronological order and updating equity at each transaction point. Between events the curve holds flat, because we know the cash position exactly but the open positions' market value is only sampled at the snapshot end-of-period (current `Market price` from the latest export). The charts are accurate at every recorded event and an approximation between them; the trade-off keeps the system simple and self-contained.

The P&L per position chart does not have this approximation problem — every closed trade has a final realised P&L from XTB, and every open position has a current unrealised P&L from the export.

Charts are stored as PNG files in a per-report directory rather than inline base64 because (a) Markdown viewers handle relative image links uniformly, (b) PNG files diff cleanly enough in Git to track meaningful changes, and (c) the user can open a chart at full resolution outside the Markdown viewer if needed.

## Acceptance Criteria

### Per-report output directory

- [ ] GIVEN a monthly report is generated for a given period
      WHEN the chart files are produced
      THEN they are saved under `outputs/reports/monthly/<YYYY-MM>/`
      AND the Markdown report file is renamed or relocated such that its relative image links resolve to that directory

- [ ] GIVEN a previous run of the same period has produced chart files
      WHEN the report is regenerated
      THEN existing chart files are overwritten with the new content (deterministic re-run)

### Equity curve chart

- [ ] GIVEN inception date is known and at least one cash event exists since inception
      WHEN the equity curve chart is generated
      THEN the chart spans from inception date to the end of the report period
      AND the X-axis represents calendar time
      AND the Y-axis represents value in PLN
      AND a "Portfolio" series traces the step-curve equity reconstructed from `Cash Operation History` plus the latest open-position market values
      AND a "Bank deposit (Belka-adjusted)" series traces deposited capital growing at the configured net deposit yield
      AND a "Rental property" series traces deposited capital growing at the configured rental net yield
      AND a legend identifies each series

- [ ] GIVEN no cash events have been recorded since inception
      WHEN the equity curve chart is generated
      THEN the chart is omitted
      AND the report explicitly states why (insufficient data)

### Drawdown chart

- [ ] GIVEN the equity curve has been reconstructed
      WHEN the drawdown chart is generated
      THEN the chart spans the same time range as the equity curve
      AND the Y-axis represents drawdown from the running historical peak as a non-positive percent
      AND the −10% strategy limit is shown as a horizontal reference line

- [ ] GIVEN the equity curve cannot be reconstructed
      WHEN the drawdown chart is generated
      THEN the chart is omitted
      AND the report explicitly states why

### P&L per position chart

- [ ] GIVEN at least one open or closed position exists in the cumulative window through the end of the report period
      WHEN the P&L per position chart is generated
      THEN the chart shows one bar per position
      AND each bar's height represents the position's gross P&L in PLN (realised for closed positions, current unrealised for open positions)
      AND bars are coloured to distinguish gains from losses
      AND positions are labelled with their symbol

- [ ] GIVEN multiple positions exist for the same symbol opened on different dates
      WHEN the chart is generated
      THEN each position appears as its own bar (matching the position-log file granularity)

### Markdown integration

- [ ] GIVEN the chart files have been generated
      WHEN the monthly Markdown report is updated
      THEN it includes an `## Charts` section placed after the closed-trade statistics section
      AND the section embeds the three images via relative paths
      AND each image has a descriptive caption naming the metric it visualises

- [ ] GIVEN any chart was omitted (per the data-availability rules above)
      WHEN the Markdown is rendered
      THEN the corresponding image is replaced by an explanatory note in the same position so the section structure is preserved

### Non-effects

- [ ] GIVEN the chart generation runs
      WHEN it completes
      THEN the weekly report files are unchanged
      AND the position log is unchanged
      AND `inputs/instruments.yaml` is unchanged

## Out of Scope

- Historical price fetching from external APIs (e.g., yfinance) — explicitly out of MVP per PRD product borders; deferred until step-curve granularity proves insufficient
- Interactive HTML / Plotly charts — PNG only for MVP
- Additional charts beyond the three listed (e.g., P&L distribution histogram, win-rate over time, sector treemap) — out of MVP
- Custom palette, dark-mode, or theming — default library palette is sufficient
- Per-month chart variants (e.g., a chart showing only the report period) — only inception-to-end-of-period spans are produced for the equity and drawdown charts
- Annotations of significant events (deposits, large trades) on the equity curve — out of MVP; raw step curve is enough
- Chart accessibility features beyond standard library output (e.g., colour-blind-safe palettes, screen-reader descriptions) — out of MVP
