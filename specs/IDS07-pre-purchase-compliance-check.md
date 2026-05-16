# SPEC: Pre-purchase compliance check

**Depends on:** IDS01 (XTB ingestion, CLI subcommand pattern), IDS02 (rule evaluation engine), IDS05 (`instruments.yaml`), IDS06 (concentration and size rules).

## User Story

As an **active investor about to open a new position in XTB**, I want **a one-shot CLI command that simulates the candidate purchase against the current portfolio and tells me which strategy rules it would pass, warn on, or violate**, so that **I can avoid breaking my own rules at the moment of buying — when intuition is strongest and discipline weakest**.

## Context

The strategy document explicitly defines a "Check-in rules" section asking the user to verify sector exposure, regional exposure, and correlation before opening a new position. In practice this check happens in the user's head while looking at the XTB app on a phone, with imperfect recall of current allocations. That is exactly when the strategy is most likely to be silently broken.

This SPEC turns the strategy's check-in rules into a deterministic CLI command. Same rule values, same metadata, same data source as the weekly snapshot — but applied to a *hypothetical post-purchase portfolio* rather than the current state. The output answers a single, concrete question: "If I commit this trade right now, what changes and what breaks?"

The command is **advisory only**. It never refuses to print a verdict, never modifies XTB, never prevents the user from proceeding — because (a) the system has no way to enforce anything in XTB and (b) soft limits in the strategy are deliberately permissive ("guidelines, nie zakazy"). What the command guarantees is that ignorance is no longer a defence: if a rule is broken, the user has seen it spelled out before placing the order.

Inputs follow the CLI pattern established in the PRD: flags supplied are used as-is; missing inputs are prompted interactively. The candidate's `type` may be omitted if the symbol is already classified in `instruments.yaml`; otherwise the user is prompted, and the same path that runs in IDS05 may be invoked to add a new entry.

## Acceptance Criteria

### Invocation

- [ ] GIVEN the user invokes the pre-purchase check subcommand with all required flags (`symbol`, `value`; `type` if symbol not yet classified)
      WHEN the command runs
      THEN the verdict is printed without further prompting

- [ ] GIVEN the user invokes the pre-purchase check subcommand without all required flags
      WHEN the command runs
      THEN the missing values are prompted interactively
      AND the verdict is printed once all values are collected

- [ ] GIVEN the user provides a symbol that is not present in `instruments.yaml`
      WHEN the command runs
      THEN the user is prompted to classify the symbol (`type`, `sector`, `region`)
      AND the new classification is written to `instruments.yaml` before the verdict is computed

### Position size verdict

- [ ] GIVEN the candidate's value would place a position within its type's allowed range
      WHEN the verdict is computed
      THEN the position-size rule is reported as `pass` with the resulting share of equity

- [ ] GIVEN the candidate's value would place a position above its type's maximum or below its type's minimum
      WHEN the verdict is computed
      THEN the position-size rule is reported as `fail` with the resulting share, the limit, and the breach amount

### Cash reserve verdict

- [ ] GIVEN purchasing the candidate would leave cash at or above 10% of equity
      WHEN the verdict is computed
      THEN the cash-reserve rule is reported as `pass` with the resulting cash percentage

- [ ] GIVEN purchasing the candidate would leave cash below 10% of equity
      WHEN the verdict is computed
      THEN the cash-reserve rule is reported as `fail` with the resulting cash percentage and the 10% minimum

### Sector concentration verdict

- [ ] GIVEN the candidate's sector would remain at or below 40% of equity after purchase
      WHEN the verdict is computed
      THEN the sector-concentration rule is reported as `pass` with the sector's resulting share

- [ ] GIVEN the candidate's sector would exceed 40% of equity after purchase
      WHEN the verdict is computed
      THEN the sector-concentration rule is reported as `warning` with the sector's resulting share, the 40% limit, and the names of every position contributing to that sector after the purchase

### Geographic concentration verdict

- [ ] GIVEN the candidate's region would remain at or below 50% of equity after purchase
      WHEN the verdict is computed
      THEN the region-concentration rule is reported as `pass` with the region's resulting share

- [ ] GIVEN the candidate's region would exceed 50% of equity after purchase
      WHEN the verdict is computed
      THEN the region-concentration rule is reported as `warning` with the region's resulting share, the 50% limit, and the names of every position contributing to that region after the purchase

### Verdict aggregation

- [ ] GIVEN every rule passed
      WHEN the verdict is finalised
      THEN the summary line states "OK to proceed"

- [ ] GIVEN at least one rule produced a `warning` and none produced a `fail`
      WHEN the verdict is finalised
      THEN the summary line states "OK with warnings" and includes the warning count

- [ ] GIVEN at least one rule produced a `fail`
      WHEN the verdict is finalised
      THEN the summary line states "Rule violations" and includes the failure count
      AND the command exits with a non-zero status

### Non-effects

- [ ] GIVEN any pre-purchase check invocation
      WHEN the command runs
      THEN no XTB state is modified
      AND no weekly or monthly report file is created
      AND the position log is unchanged

## Out of Scope

- Persisting the verdict to a file (e.g., as part of position log or audit trail) — verdict is terminal output only
- Multi-candidate batch evaluation ("simulate buying these three at once") — single candidate per invocation
- Correlation analysis between the candidate and existing positions — explicitly out of MVP per PRD product borders
- Suggesting alternative positions that would not breach limits — system is advisory, not prescriptive
- Modifying any state in XTB — the system never integrates with XTB beyond reading exports
- Auto-pulling current market price for the candidate symbol — the user supplies `value` (volume × price) directly
