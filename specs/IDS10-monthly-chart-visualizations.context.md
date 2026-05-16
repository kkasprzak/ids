# IDS10 — Monthly chart visualizations

## Purpose

Adds three embedded charts to the monthly report — equity curve vs benchmarks, portfolio drawdown from peak, and P&L per position. Charts surface patterns that tables and aggregates hide: when drawdowns happened, how the strategy tracked benchmarks over time, which positions are net contributors versus net drags. After this SPEC the monthly report goes from textual summary to visual story.

## Input

- Parsed XTB data (already ingested by IDS01 / IDS03 / IDS08):
  - `Cash Operation History` — the canonical event stream for deposits, dividends, interest, stock purchases / sales — used to reconstruct cash and equity at each transaction time
  - `Closed Position History` — sale events with realised P&L
  - `Open Position` — current positions and their unrealised P&L for the snapshot end-of-period view
- Benchmark configuration constants from IDS08 (deposit 4% gross / Belka-adjusted; rental 5.5%).
- The same report period selection as IDS08 / IDS09.

The chart data is reconstructed by walking transaction events in chronological order (a "step curve"). Between events, equity is held flat — we do not interpolate market prices for open positions because no historical price source is in scope for the MVP (deferred per PRD product borders). Granularity of the equity and drawdown curves is therefore at the resolution of XTB cash-event timestamps, accurate at every transaction point and approximate between them.

## Output

Three PNG charts saved into a per-report directory (`outputs/reports/monthly/<YYYY-MM>/`) and embedded in the monthly Markdown via relative image links:

- **`equity_curve.png`** — portfolio equity over the inception-to-period-end span, plotted alongside the deposit benchmark (Belka-adjusted) and rental property benchmark, both starting from the inception-date deposited capital and growing at their respective annualised yields. Y-axis: PLN.
- **`drawdown.png`** — running drawdown from the historical equity peak over the same span. Y-axis: percent (negative values).
- **`positions_pl.png`** — bar chart of P&L per position across both currently open and historically closed positions in the period (or in the full cumulative window — see Acceptance Criteria for which view ships). Bars coloured by sign (gain vs loss). Y-axis: PLN.

The Markdown report adds an `## Charts` section after the closed-trade statistics, embedding the three images with descriptive captions.

## Which User problem it addresses (PRD section 2)

Operates on the same *strategy validation* axis as IDS08 but at a different cognitive register — humans see things on charts that they miss in tables. The drawdown chart in particular puts the strategy's −10% portfolio drawdown rule into context (at what dates did the portfolio approach this limit?). Visual evidence is also more compelling for the eventual go/no-go decision on scaling capital, which is the project's overarching goal.

## Which Functional requirements it covers (PRD section 5)

- **Chart visualization** — full implementation of the three monthly charts described in the PRD.
- **Monthly evaluation report** — extends the report with the `Charts` section and per-report directory layout.
