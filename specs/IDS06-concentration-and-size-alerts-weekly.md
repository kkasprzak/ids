# SPEC: Concentration & position-size alerts in weekly snapshot

**Depends on:** IDS01 (weekly report scaffold), IDS02 (alerts section pattern, rule evaluation engine), IDS05 (`instruments.yaml` metadata).

## User Story

As an **active investor**, I want **the weekly snapshot to flag positions whose size falls outside the limits defined for their instrument type, sectors that exceed the 40% concentration soft limit, and regions that exceed the 50% concentration soft limit**, so that **I detect unintended exposure before it becomes a real risk to my portfolio**.

## Context

IDS02 implemented the rule evaluation engine but only for rules that require no external metadata. This SPEC completes the picture by adding the rules that depend on `instruments.yaml` (introduced in IDS05): per-instrument-type position size limits, sector concentration, and geographic concentration. After this SPEC the weekly snapshot covers every "green" compliance rule listed in the PRD.

The metadata dependency creates a soft failure mode worth treating explicitly: when a held symbol is missing from `instruments.yaml` or has incomplete classification, the system cannot evaluate concentration or sizing for it. Instead of skipping silently or crashing, the report surfaces the gap as a missing-classification warning, pointing the user back to the metadata file.

Concentration and size limits are **soft limits** per the strategy ("guidelines, nie zakazy"). Alerts therefore phrase breaches as warnings with the recommendation to reconsider, not as hard violations. Each soft-limit breach in the strategy may be intentional ("I'm taking a deliberate concentrated bet"); the system's job is to make the breach visible, not to block it.

The position-size minimum is included alongside the maximum because the strategy explicitly states minimums (ETF ≥ 20%, stock ≥ 10%) — undersized positions dilute attention without contributing meaningfully to the portfolio.

## Acceptance Criteria

### Position size — maximum

- [ ] GIVEN an open position is classified as `etf` and its value exceeds 30% of equity
      WHEN the weekly snapshot is generated
      THEN a "position size above maximum" alert lists that position with its current share and the 30% limit
      AND the position's row is flagged

- [ ] GIVEN an open position is classified as `stock` (non-blue-chip) and its value exceeds 25% of equity
      WHEN the weekly snapshot is generated
      THEN a "position size above maximum" alert lists that position with its current share and the 25% limit
      AND the position's row is flagged

- [ ] GIVEN an open position is classified as `blue_chip_stock` and its value exceeds 30% of equity
      WHEN the weekly snapshot is generated
      THEN a "position size above maximum" alert lists that position with its current share and the 30% limit
      AND the position's row is flagged

### Position size — minimum

- [ ] GIVEN an open position is classified as `etf` and its value is below 20% of equity
      WHEN the weekly snapshot is generated
      THEN a "position size below minimum" alert lists that position with its current share and the 20% minimum

- [ ] GIVEN an open position is classified as `stock` or `blue_chip_stock` and its value is below 10% of equity
      WHEN the weekly snapshot is generated
      THEN a "position size below minimum" alert lists that position with its current share and the 10% minimum

### Sector concentration

- [ ] GIVEN the combined value of all open positions in a single sector exceeds 40% of equity
      WHEN the weekly snapshot is generated
      THEN a "sector concentration above soft limit" alert names the sector, its current share, and the 40% limit
      AND the alert lists the positions contributing to that sector

- [ ] GIVEN every sector represented in the portfolio is at or below 40% of equity
      WHEN the weekly snapshot is generated
      THEN no sector concentration alert appears

### Geographic concentration

- [ ] GIVEN the combined value of all open positions in a single region exceeds 50% of equity
      WHEN the weekly snapshot is generated
      THEN a "region concentration above soft limit" alert names the region, its current share, and the 50% limit
      AND the alert lists the positions contributing to that region

- [ ] GIVEN every region represented in the portfolio is at or below 50% of equity
      WHEN the weekly snapshot is generated
      THEN no region concentration alert appears

### Missing classification handling

- [ ] GIVEN an open position references a symbol not present in `instruments.yaml`
      WHEN the weekly snapshot is generated
      THEN a "missing classification" warning lists that symbol and instructs the user to reconcile metadata
      AND that position is excluded from concentration and size calculations until classified

- [ ] GIVEN an open position references a symbol whose entry exists in `instruments.yaml` but has empty `sector`, empty `region`, or placeholder `type`
      WHEN the weekly snapshot is generated
      THEN a "missing classification" warning lists that symbol with the missing fields
      AND concentration / size rules dependent on the missing field are skipped for that position

### Aggregation with existing alerts

- [ ] GIVEN concentration or size rules trigger in the same run as IDS02 alerts (stop-loss, profit-take, cash reserve, missing SL)
      WHEN the weekly snapshot is generated
      THEN all alert categories appear together under the unified `## Alerts` section, grouped by category
      AND the per-position `Flag` column reflects the most relevant warning when multiple apply

## Out of Scope

- Hard rejection / blocking of any kind — these are soft limits surfaced as warnings only
- Trailing-stop tracking against local maxima — explicitly out of MVP per PRD product borders
- Correlation analysis between positions — explicitly out of MVP per PRD product borders
- Automatic suggestions for how to rebalance to come back within limits — strategy guidance, not system behaviour
- Pre-purchase concentration check (what would happen if I bought X) — that is IDS07
- Treating any sector or region as exempt from limits — strategy treats every sector / region the same
- Heuristic detection of "blue chip" status from symbol or external data — classification is user-owned via `instruments.yaml`
