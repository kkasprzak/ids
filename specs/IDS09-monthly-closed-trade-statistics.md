# SPEC: Monthly closed-trade statistics

**Depends on:** IDS03 (XTB ingestion of `Closed Position History`), IDS08 (monthly report scaffold, period selection, `Cash Operation History` ingestion).

## User Story

As an **active investor learning from my track record**, I want **monthly statistics on my closed trades — win rate, average gain, average loss, average holding period, and adherence to the −5% stop-loss rule**, so that **I can spot patterns in my own decision-making instead of relying on vague impressions of how I trade**.

## Context

IDS08 tells the user whether the portfolio outperformed passive benchmarks; this SPEC tells the user *how* the wins and losses were distributed across individual trades. Both are essential — a portfolio can be net-positive while the trader is making systematic mistakes (e.g., one big winner masking many small losers cut too late).

The statistics are deliberately simple and deterministic: counts, averages, holding periods, and a rule-adherence breakdown. No advanced trading metrics like Sharpe ratio or expectancy formulas are introduced; the user is at an early learning stage where headline numbers and per-trade visibility teach more than statistical sophistication.

The rule-adherence retrospective focuses on the **−5% stop-loss rule** because it is the rule whose past violations are unambiguously detectable from XTB data alone (loss percent at close is computable from open and close prices). The +15% profit-take rule is reported as informational (how many winners crossed +15%) but the system cannot verify from XTB exports alone whether 50% was realised mechanically per the strategy — that nuance belongs to IDS12 (Discipline Twin).

The per-trade table makes individual decisions visible alongside the aggregates so the user can pivot from "in this month I had a 60% win rate" to "let me read the rationale of the loser that broke −5%". This connects the statistics back to the position log from IDS03.

## Acceptance Criteria

### Headline statistics — period view

- [ ] GIVEN the report period and the set of trades closed during that period are known
      WHEN the report is generated
      THEN a count of closed trades for the period is reported

- [ ] GIVEN at least one trade closed during the period
      WHEN the report is generated
      THEN the win rate is reported as the percentage of closed trades with strictly positive gross P&L

- [ ] GIVEN at least one closed trade with positive gross P&L
      WHEN the report is generated
      THEN the average winning trade is reported in PLN and as percent return relative to its purchase value

- [ ] GIVEN at least one closed trade with negative gross P&L
      WHEN the report is generated
      THEN the average losing trade is reported in PLN and as percent return relative to its purchase value

- [ ] GIVEN at least one trade closed during the period
      WHEN the report is generated
      THEN the average holding period is reported in days, computed from each trade's open and close timestamps

- [ ] GIVEN at least one trade closed during the period
      WHEN the report is generated
      THEN the total realised P&L for the period is reported in PLN

- [ ] GIVEN no trades closed during the period
      WHEN the report is generated
      THEN the section explicitly states that no trades closed during the period
      AND none of the headline aggregates are computed for the period

### Strategy adherence retrospective — period view

- [ ] GIVEN closed trades exist in the period
      WHEN the report is generated
      THEN the count of losing trades that exceeded the −5% threshold before being closed is reported, along with the symbols of those trades

- [ ] GIVEN closed trades exist in the period
      WHEN the report is generated
      THEN the count of winning trades that reached or exceeded +15% return is reported, along with the symbols of those trades, marked as informational

### Per-trade table

- [ ] GIVEN at least one trade closed during the period
      WHEN the report is generated
      THEN the section contains a per-trade table with one row per closed trade
      AND each row shows symbol, open date, close date, holding days, gross P&L in PLN, gross P&L in percent, an outcome marker (`win` / `loss` / `flat`), and a rule-adherence marker (`within −5%` / `breach beyond −5%`)

- [ ] GIVEN per-trade rows are produced
      WHEN the table is rendered
      THEN trades are ordered by close date

### Cumulative-since-inception aggregates

- [ ] GIVEN inception date is known and at least one trade has ever closed
      WHEN the report is generated
      THEN cumulative versions of these aggregates are reported alongside the period view: total closed trades, win rate, average winning trade, average losing trade, total realised P&L, count of −5% rule violations
      AND the cumulative window matches the inception-to-end-of-period span used by IDS08

### Section integration

- [ ] GIVEN the monthly report has been generated
      WHEN the closed-trade statistics section is added
      THEN the existing performance summary section from IDS08 remains unchanged in structure and content
      AND the closed-trade statistics section is placed after the performance summary section in the report

## Out of Scope

- Advanced trading metrics (Sharpe, Sortino, expectancy, R-multiples, max consecutive losses) — out of MVP; headline aggregates are the chosen learning surface
- Verification of mechanical execution of the +15% profit-take rule from XTB data alone — covered by IDS12 (Discipline Twin)
- Per-trade rationale review or correlation between rationale content and outcome — out of MVP; user reads rationale manually via the position log files
- Charts of the statistics (e.g., win rate over time, P&L distribution) — covered by IDS10 for the equity curve, drawdown, and per-position P&L; statistical histograms are out of MVP
- Externalising rule values for adherence calculation — current values are system constants
- Tax-aware net P&L per trade — current calculations use gross P&L as reported by XTB
- Filtering trades by tag, sector, or other facets — period and cumulative views are the only slices in MVP
