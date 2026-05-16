# IDS02 — Strategy compliance alerts in weekly snapshot

## Purpose

Extends the weekly report from IDS01 with an alerts section. This is when the report starts to actually protect the user against situations like FRO.PL — the system flags positions violating strategy rules instead of merely listing them.

## Input

- Everything from IDS01 (XTB export, open positions data, account summary).
- **Rules from the active strategy**, hardcoded as system constants (taken directly from the strategy document):
  - Stop-loss `−5%` from open price
  - Profit-taking trigger `+15%` from open price
  - Minimum cash reserve `10%` of equity
  - Stop-loss order required to be configured in XTB for every open position
- Additional column from the export: `Open Position` `SL` column (already parsed in IDS01) — checked for null.

Scope note: this SPEC does **not** check position size limits (10–30%) or concentration limits (40% / 50%). Both require a symbol-to-instrument-type / sector / region mapping that the system does not yet have. They will be addressed in later SPECs after `instruments.yaml` is introduced.

## Output

The weekly report (the same file as IDS01) enriched with:

- **A `Flag` column in the open positions table** — short per-position marker (e.g., `🔴 STOP-LOSS BREACH`, `🟡 Approaching profit-take`, `⚠️ No SL set`).
- **An `## Alerts` section** with grouped warnings and concrete actions:
  - Stop-loss breaches (loss < −5% without SL set)
  - Profit-taking opportunities (profit ≥ +15%)
  - Missing stop-loss configuration (SL = null in XTB)
  - Cash reserve below minimum (cash < 10%)

## Which User problem it addresses (PRD section 2)

Addresses the core of the PRD's user problem: *"open positions violate strategy rules (missing stop-losses, losses significantly exceeding defined thresholds), decisions rely on intuition rather than hard data"*. This is the first SPEC where the system starts to use hard rules (instead of feelings) to evaluate the portfolio. Without it, the portfolio remains a set of numbers — with it, the portfolio starts being "judged" by the system.

## Which Functional requirements it covers (PRD section 5)

- **Strategy compliance monitoring** — partial implementation (the four rules independent of instrument metadata: stop-loss configured, −5% loss, +15% profit, cash reserve). Position size limits and concentration soft limits are left to subsequent SPECs.
- **Weekly review report** — extends the report from IDS01 with the `Alerts` section and the `Flag` column in the open positions table.
