# SPEC: Real vs Discipline Twin comparison

**Depends on:** IDS01 / IDS03 (XTB ingestion of `Open Position` and `Closed Position History`), IDS08 (monthly report scaffold, period selection, `Cash Operation History` ingestion, deposited-capital baseline), IDS10 (equity step-curve reconstruction methodology and per-report chart directory).

## User Story

As an **active investor weighing whether to scale my strategy to a larger capital pool**, I want **the monthly report to compare my actual portfolio outcomes against a virtual shadow portfolio that mechanically applies my strategy's exit rules to the same entries I made**, so that **I have a hard PLN measure of whether my discretionary execution adds value, destroys value, or is roughly neutral versus pure mechanical execution**.

## Context

This is the most strategically loaded SPEC in the monthly report. Its premise: the user takes the entries (the system cannot pick stocks) but then exits discretely — sometimes earlier, sometimes much later than the strategy prescribes (FRO.PL closed at −22% rather than the rule's −5%). Two extreme outcomes are possible after enough months of data:

- **Mechanical wins.** The Twin's clean −5% / +15% discipline outperforms the user's actual results. Implication: the user's judgment subtracts value, and the strategy is best executed by code, not human discretion. This is a clear scale-up signal — automate at the larger capital level.
- **Discretionary wins.** The user's actual results outperform the Twin. Implication: the user's judgment adds alpha that mechanical rules miss. Scaling decisions then have to weigh whether that alpha is repeatable at higher capital.

Without this comparison the user cannot tell which of those worlds they live in, and therefore cannot make an evidence-based capital-allocation decision — the project's headline goal per the Product overview.

The Twin operates strictly on data the system has access to. It simulates two mechanical exits per position:

- A **stop-loss exit at −5%** from entry. The Twin closes the position at the first observable price point where the position's loss would have crossed −5%.
- A **profit-take partial exit at +15%** from entry. The Twin realises 50% of the position at the first observable price point where the position's gain would have crossed +15%, and continues holding the remaining 50% under the same rules.

"Observable price point" in MVP means: a price implied by an event in `Cash Operation History` (a sale, a dividend) or the snapshot price in the latest `Open Position` export. There is no historical intraday data source. As a result the Twin's simulated exits are **approximate** between events — for example, if the price crossed −5% mid-day on a date with no logged event, the Twin will recognise it only at the next event timestamp. This conservatism is explicitly acknowledged in the report so the user does not over-interpret marginal Real–Twin gaps.

The headline metric (`Real − Twin` in PLN at end of period) is the simplest possible expression of the comparison. It is reinforced by a per-closed-position breakdown so the user can see which individual trades drove the gap, and by an equity-curve overlay so the time shape is visible.

## Acceptance Criteria

### Twin simulation

- [ ] GIVEN a position's entry exists in XTB and the position is currently open
      WHEN the Twin is simulated for that position
      THEN the Twin holds the same volume from the same entry date and price
      AND if any observable price between entry and the report period end implies a loss greater than 5%, the Twin closes the position at that price point
      AND if any observable price implies a gain at or above 15%, the Twin realises 50% of the position at that price point and continues holding the remaining 50% under the same rules
      AND if neither threshold is crossed, the Twin still holds the position at the period end at the same market price as the Real portfolio

- [ ] GIVEN a position is already closed in XTB
      WHEN the Twin is simulated for that position
      THEN the Twin's close events follow the same rules as for open positions
      AND if neither rule triggered before the user's actual close, the Twin closes at the same date and price as the user

- [ ] GIVEN the simulation needs to evaluate prices between events for which no data exists
      WHEN the Twin is simulated
      THEN the simulation uses the next available event price as the effective exit price (approximate)
      AND the report records that approximation in its caveat note

### Headline metrics

- [ ] GIVEN both Real and Twin equity have been reconstructed up to the report period end
      WHEN the section is generated
      THEN the cumulative `Real − Twin` value is reported in PLN
      AND it is presented as either "discretion alpha" (positive) or "discretion cost" (negative)

- [ ] GIVEN both Real and Twin equity series exist for the report period
      WHEN the section is generated
      THEN a period-only `Real − Twin` value is reported alongside the cumulative figure

### Per-closed-position breakdown

- [ ] GIVEN at least one position has closed in the cumulative window
      WHEN the section is generated
      THEN a table lists every closed position with: symbol, open date, Real close date, Real close price, Real gross P&L, Twin close date, Twin close price, Twin gross P&L, and the per-position delta `Real − Twin` in PLN
      AND rows are ordered by Real close date

- [ ] GIVEN no positions have closed in the cumulative window
      WHEN the section is generated
      THEN the breakdown table is replaced with an explicit "no closed positions yet" indication

### Equity overlay chart

- [ ] GIVEN both Real and Twin equity series have been reconstructed
      WHEN the chart is generated
      THEN it is saved as `real_vs_twin.png` in the same per-report directory as IDS10 charts (`outputs/reports/monthly/<YYYY-MM>/`)
      AND the chart plots both series as step curves over the same time range
      AND a legend distinguishes "Real" and "Discipline Twin"
      AND the chart is embedded in the monthly Markdown via a relative image link

- [ ] GIVEN either equity series cannot be reconstructed
      WHEN the chart is generated
      THEN the chart is omitted
      AND the report explicitly states why

### Approximation caveat

- [ ] GIVEN the section is rendered
      WHEN the user reads the report
      THEN a short paragraph describes the Twin's exit simulation method, the data limitations (no historical intraday prices), and a recommendation to focus on directional and large gaps rather than small Real–Twin differences

### Section integration

- [ ] GIVEN the monthly report has been generated through IDS11
      WHEN the Real vs Discipline Twin section is added
      THEN it is placed after the reflection prompts section
      AND existing sections from IDS08 through IDS11 remain unchanged in structure and content

### Determinism

- [ ] GIVEN the same input data
      WHEN the section is regenerated
      THEN the headline metrics, the per-closed-position breakdown, and the equity overlay produce identical content (the simulation is deterministic; no randomness)

## Out of Scope

- Trailing-stop simulation against local maxima — explicitly out of MVP per PRD product borders; Twin uses only the −5% from entry and +15% partial profit-take rules
- Mechanical handling of the −10% portfolio-drawdown rule (closing positions to defend the portfolio) — out of MVP; Twin operates per-position
- Concentration or position-size enforcement on the Twin (e.g., refusing to hold a Twin position that would breach 30%) — out of MVP; Twin mirrors entries verbatim
- Use of historical intraday prices to refine the approximation — explicitly out per PRD product borders; deferred until step-curve granularity proves insufficient and an external data source is added in a future SPEC
- Suggesting that the user adopt mechanical execution — system is observational; the user interprets the comparison
- Backtesting against alternative rule values (e.g., what if my stop were −7% instead?) — out of MVP; rule values are system constants
- A standalone CLI command for the Twin separate from the monthly report — Twin output lives only inside the monthly report
- Per-period (rather than cumulative) Twin reconstructions for past months on demand — only the natural rolling cumulative-since-inception window is produced
