# SPEC: Monthly performance vs benchmarks

**Depends on:** IDS01 (XTB ingestion of `Open Position`, CLI subcommand pattern, file-path conventions), IDS03 (XTB ingestion of `Closed Position History`).

## User Story

As an **active investor validating whether my IKZE strategy beats passive alternatives**, I want **a monthly Markdown report comparing my portfolio's period and cumulative returns to bank deposit and rental property yields**, so that **I have hard data to judge whether active management is paying off and whether the strategy is ready to scale to a larger capital pool**.

## Context

This is the **first monthly evaluation SPEC** and the strategic counterpart to the weekly snapshot from IDS01. While the weekly report answers "is anything wrong now?", the monthly report answers "is the strategy working over time?" — the question that ultimately drives the go/no-go decision on capital allocation outside IKZE.

The MVP scope deliberately covers only the headline performance comparison: period return and cumulative return, each measured against bank deposit and rental property benchmarks. Closed-trade statistics, charts, reflection prompts, and the Discipline Twin comparison are deferred to dedicated SPECs (IDS09–IDS12) so each piece of strategic evidence ships in isolation.

The benchmarks are intentionally simple yardsticks defined by the user, not exotic indices. Bank deposit (4% gross) is the lowest-effort alternative and is taxed at 19% Belka — both gross and Belka-adjusted views are reported so the comparison is parity. Rental property yield (5.5%) is the user's actual experienced yield from existing real estate; tax handling is rolled into the input figure (treated as net for comparison).

The reference point for returns is **deposited capital**, computed from `IKZE Deposit` events in `Cash Operation History`. This convention handles mid-period deposits without distortion and matches the user's mental model ("money I put in vs money it's worth now"). It also enables a stable inception date as the first deposit event.

`Cash Operation History` is also the canonical source for dividends, interest, and stock purchases / sales going forward; this SPEC introduces the parser for that sheet so subsequent monthly SPECs can reuse it.

## Acceptance Criteria

### Period selection

- [ ] GIVEN the user invokes the monthly report subcommand without specifying a period
      WHEN the report is generated
      THEN the period defaults to the most recently completed calendar month
      AND the report file is named `<YYYY-MM>_monthly.md` corresponding to that month

- [ ] GIVEN the user invokes the monthly report subcommand with a specific past month
      WHEN the report is generated
      THEN the report file is named `<YYYY-MM>_monthly.md` for the requested month
      AND every figure in the report reflects only that month's data and the cumulative span up to its end

### Inception detection

- [ ] GIVEN `Cash Operation History` contains one or more `IKZE Deposit` events
      WHEN the report is generated
      THEN the earliest such event's date is reported as the inception date

- [ ] GIVEN `Cash Operation History` contains no `IKZE Deposit` events
      WHEN the report is generated
      THEN the report explicitly states that no inception event was detected
      AND cumulative-view figures are omitted (or marked as not applicable)

### Period return

- [ ] GIVEN the report period and the equity at the start and end of that period are known
      WHEN the report is generated
      THEN the report shows the period return in PLN
      AND the report shows the period return as a percent of the deposited-capital base at the start of the period

- [ ] GIVEN one or more deposits occurred during the report period
      WHEN the period return is computed
      THEN the deposit amounts are not counted as gains
      AND the resulting return reflects only market value changes plus dividends, interest, and realised P/L

### Cumulative return since inception

- [ ] GIVEN inception date is known and the latest equity is known
      WHEN the report is generated
      THEN the cumulative return in PLN is reported as `latest equity − total deposited capital`
      AND the cumulative return as percent is reported relative to total deposited capital
      AND the annualised return is computed for the elapsed span

### Benchmark comparison — bank deposit

- [ ] GIVEN a bank deposit gross yield of 4% is configured
      WHEN the report is generated
      THEN the deposit benchmark is shown as both gross (4%) and Belka-adjusted net (4% × (1 − 0.19)) for the period and the cumulative span
      AND a per-view outcome line states whether the portfolio is `ahead by X.Xpp` or `behind by X.Xpp` versus the Belka-adjusted comparison

### Benchmark comparison — rental property

- [ ] GIVEN a rental property net yield of 5.5% is configured
      WHEN the report is generated
      THEN the rental benchmark is shown for the period and the cumulative span
      AND a per-view outcome line states whether the portfolio is `ahead by X.Xpp` or `behind by X.Xpp` versus the rental yield

### Report file output

- [ ] GIVEN the report has been generated
      WHEN it is written to disk
      THEN the file is placed under `outputs/reports/monthly/`
      AND the filename includes the year and month of the period in `<YYYY-MM>_monthly.md` format

- [ ] GIVEN a monthly report for the same period has previously been generated
      WHEN the report is regenerated
      THEN the existing file is replaced with the new content (deterministic re-run)

### CLI invocation

- [ ] GIVEN the system is installed
      WHEN the user invokes the monthly report subcommand
      THEN the report is generated and the path of the produced file is displayed in the terminal

- [ ] GIVEN no XTB export is present in the input location
      WHEN the monthly report subcommand is invoked
      THEN an error is shown explaining that no input data is available

## Out of Scope

- Closed-trade statistics (win rate, average gain / loss, holding-period stats, rule-adherence retrospective) — covered by IDS09
- Embedded charts (equity curve, drawdown, P&L per position) — covered by IDS10
- Reflection prompts based on the period's data — covered by IDS11
- Real vs Discipline Twin comparison — covered by IDS12
- Time-weighted return (TWR) calculation accounting for cash flow timing — out of MVP; the deposited-capital baseline is the chosen approximation
- Currency adjustments for non-PLN positions — out of MVP; XTB exports already report values in account currency (PLN)
- External market-data sources for benchmark yields — current values are system constants
- Tax modelling beyond the Belka adjustment for the deposit benchmark — out of MVP
