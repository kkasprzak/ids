# SPEC: Strategy compliance alerts in weekly snapshot

**Depends on:** IDS01 (weekly portfolio snapshot foundation, XTB ingestion, Markdown report generation, CLI subcommand pattern).

## User Story

As an **active investor**, I want **the weekly portfolio snapshot to flag any open position that violates my strategy rules (missing stop-loss configuration in XTB, loss exceeding −5% from entry, profit reaching the +15% realization threshold, portfolio cash reserve below 10%)**, so that **I can take corrective action without manually evaluating each position against each rule**.

## Context

Establishes the **rule evaluation engine** of the system — a deterministic component that takes the parsed XTB state and returns a list of alerts. This engine will be reused by IDS06 (concentration alerts) and IDS07 (pre-purchase compliance check).

Scope is intentionally limited to the four rules that do **not require external metadata** about instruments. Position size limits (which depend on knowing whether an instrument is a stock or ETF) and sector / geographic concentration limits (which depend on the symbol-to-sector / region mapping) are deferred to IDS06, after IDS05 introduces `instruments.yaml`.

This SPEC is the first one to translate the strategy document into machine-checked rules. The rule values (−5%, +15%, 10%) are taken directly from the active strategy and treated as system constants for now; promoting them to a configuration file is not in scope.

## Acceptance Criteria

### Stop-loss configuration check

- [ ] GIVEN an open position has a stop-loss value configured in XTB (SL non-null)
      WHEN the weekly snapshot is generated
      THEN no missing-stop-loss alert appears for that position

- [ ] GIVEN an open position has no stop-loss configured in XTB (SL = null)
      WHEN the weekly snapshot is generated
      THEN a "missing stop-loss configuration" alert lists that position
      AND the position's row in the Open positions table is flagged

### Loss threshold check (−5%)

- [ ] GIVEN an open position has a current loss greater than 5% from its open price
      WHEN the weekly snapshot is generated
      THEN a "stop-loss breach" alert lists that position with its loss percentage and a recommended action (close manually or set a protective stop in XTB)
      AND the position's row is flagged

- [ ] GIVEN an open position has a current loss of at most 5% from its open price (or is in profit)
      WHEN the weekly snapshot is generated
      THEN no stop-loss breach alert appears for that position

### Profit threshold check (+15%)

- [ ] GIVEN an open position has a current profit at or above 15% from its open price
      WHEN the weekly snapshot is generated
      THEN a "profit-taking opportunity" alert lists that position with the recommendation to realize 50% of the position
      AND the position's row is flagged

- [ ] GIVEN an open position has a current profit below 15%
      WHEN the weekly snapshot is generated
      THEN no profit-taking alert appears for that position

### Cash reserve check (≥ 10%)

- [ ] GIVEN cash balance is below 10% of equity
      WHEN the weekly snapshot is generated
      THEN a "cash reserve below minimum" alert appears with the current cash percentage

- [ ] GIVEN cash balance is at or above 10% of equity
      WHEN the weekly snapshot is generated
      THEN no cash reserve alert appears

### Aggregation

- [ ] GIVEN multiple positions trigger different alert types
      WHEN the weekly snapshot is generated
      THEN all alerts appear in the report, grouped by alert type
      AND each alert lists every position it applies to

- [ ] GIVEN no rule is violated by any position and the cash reserve is sufficient
      WHEN the weekly snapshot is generated
      THEN the alerts section explicitly states that no rule violations were detected

## Out of Scope

- Position size limits (10–30% per instrument type) — deferred to IDS06 (requires `instruments.yaml`)
- Sector and geographic concentration soft limits (40% / 50%) — covered by IDS06
- Trailing-stop tracking based on local maximum price — explicitly out of MVP per PRD product borders
- Portfolio drawdown tracking against the −10% peak limit — covered by IDS08 (cumulative figures) and IDS10 (chart)
- Externalising rule values into a configuration file — current values are system constants
- Pre-purchase compliance check — reuses this rule engine but is delivered separately in IDS07
