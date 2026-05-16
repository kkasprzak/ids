# IDS08 — Monthly performance vs benchmarks

## Purpose

Establishes the monthly evaluation report — the strategic counterpart to the operational weekly snapshot. Where the weekly report asks "is anything broken right now?", the monthly report asks "is the strategy working over time?" This first monthly SPEC delivers the core answer: portfolio return vs passive benchmarks (bank deposit, rental property), in both period (this month) and cumulative-since-inception views. Subsequent monthly SPECs (IDS09–IDS12) add closed-trade statistics, charts, reflection prompts, and the Discipline Twin comparison.

## Input

- Parsed XTB export (extends IDS01 / IDS03 ingestion):
  - `Open Position` sheet — current open positions for snapshot equity
  - `Closed Position History` — realised gains and losses
  - `Cash Operation History` (newly required) — deposits, dividends, interest, stock purchases / sales — the source of truth for inception date, capital flow, and intermediate cash events
- Account header — current Equity (snapshot total value).
- Benchmark configuration, hardcoded as system constants for MVP:
  - Bank deposit gross yield: `4%` annualised (configurable concept, default value as a constant)
  - Rental property net yield: `5.5%` annualised (configurable concept, default value as a constant)
- A "report period" — by default, the most recently completed calendar month. The user may also request a specific past month.

## Output

A Markdown report at `outputs/reports/monthly/<YYYY-MM>_monthly.md` containing the **performance summary** section:

- **Inception date** — date of the first IKZE deposit detected in `Cash Operation History`
- **Period view** (the requested month):
  - Period return in PLN and percent
  - Bank deposit benchmark return for the same period (4% gross, 19% Belka tax applied for net comparison parity)
  - Rental property benchmark return for the same period (5.5%)
  - Outcome line per benchmark (`ahead by X.Xpp`, `behind by X.Xpp`)
- **Cumulative since inception view**:
  - Total return in PLN and percent
  - Annualised return in percent
  - Bank deposit benchmark cumulative return for the same span
  - Rental property benchmark cumulative return for the same span
  - Outcome line per benchmark

Numerical convention: returns are computed against deposited capital (sum of `IKZE Deposit` events from `Cash Operation History`), not against starting balance. This handles mid-period deposits cleanly and matches how the user thinks about "money I put in vs money it's worth now."

## Which User problem it addresses (PRD section 2)

Directly addresses the *strategy validation* element of the user problem: the user explicitly framed their goal as "is my IKZE strategy beating bank deposit and rental property yields." Without IDS08 the user has only weekly compliance data; with it, they have the period-by-period evidence base needed to decide whether to scale the strategy to a larger capital pool — which is the core motivation of the project per the Product overview.

## Which Functional requirements it covers (PRD section 5)

- **Monthly evaluation report** — first concrete instance of the report file (charts, closed-trade stats, reflection prompts, Discipline Twin come in subsequent SPECs).
- **Performance evaluation against benchmarks** — full implementation of the requirement (period and cumulative views; both benchmarks).
- **XTB data ingestion** — extends the parser with the `Cash Operation History` sheet, which becomes the canonical source for inception, deposits, dividends, and interest going forward.
- **CLI interface** — third subcommand (`report monthly`), reusing the pattern from `report weekly`.
- **Local execution and Git versioning** — establishes the monthly report file path convention.
