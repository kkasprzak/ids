# IDS09 — Monthly closed-trade statistics

## Purpose

Adds a closed-trade statistics section to the monthly report. Where IDS08 answers "did the portfolio beat benchmarks", this SPEC answers "what kind of trader am I becoming?" — surfacing patterns in win rate, average gain vs average loss, holding periods, and adherence to the −5% stop-loss rule. These statistics are the user's first systematic mirror of their own decision quality across the full set of closed positions.

## Input

- Parsed XTB export — specifically `Closed Position History` (parsed in IDS03) and `Cash Operation History` (parsed in IDS08, used to attribute dividends to held positions when computing net per-trade outcome).
- Strategy thresholds reused from earlier SPECs: stop-loss `−5%` for adherence calculation, profit-take `+15%` for matching realised wins to the rule.
- The same report period selection as IDS08 (default: most recent completed calendar month; a specific past month may be requested).

## Output

A new section in the monthly report (`outputs/reports/monthly/<YYYY-MM>_monthly.md`) — `## Closed-trade statistics` — covering:

- **For the period:**
  - Number of closed trades
  - Win rate (% of closed trades with positive gross P&L)
  - Average winning trade in PLN and percent return
  - Average losing trade in PLN and percent return
  - Average holding period (days)
  - Total realised P&L for the period
- **Strategy adherence retrospective for the period:**
  - Number of losing trades that exceeded the −5% threshold before being closed (rule violations)
  - Number of winning trades that crossed +15% (eligible for profit-take rule application — informational, since IDS09 cannot verify whether 50% was actually realised mechanically)
- **Per-trade table** — one row per closed trade in the period: symbol, open date, close date, holding days, P&L PLN, P&L %, outcome marker (`win` / `loss` / `flat`), rule-adherence marker (`within −5%` / `breach beyond −5%`).

Cumulative-since-inception equivalents of the headline figures (win rate, avg win, avg loss, total realised P&L, rule-adherence count) are also reported for context.

## Which User problem it addresses (PRD section 2)

Reinforces the *learning cycle* element: the user cannot improve as a trader without seeing patterns in their own behaviour, and the user cannot see those patterns by recalling individual trades. This SPEC is the systematic mirror — it surfaces things like "I let losers run too long" or "my winners don't get big enough" with hard numbers rather than vibes. It also provides the per-period record-keeping that the *Decision traceability* success metric depends on.

## Which Functional requirements it covers (PRD section 5)

- **Monthly evaluation report** — extends with the `Closed-trade statistics` section.
- **Strategy compliance monitoring** — extends the compliance lens from "current state" (weekly) to "historical adherence" (rule-adherence retrospective on closed trades).
