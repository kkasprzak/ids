# IDS06 — Concentration & position-size alerts in weekly snapshot

## Purpose

Adds the metadata-dependent rule checks that IDS02 deferred — sector concentration, geographic concentration, and per-position size limits per instrument type. Combined with IDS05 (the metadata source) and IDS02 (the alerts mechanism), this completes the strategy-compliance picture for the weekly snapshot. After this SPEC the report covers every "green" rule from the PRD compliance set.

## Input

- Weekly snapshot from IDS01 / IDS02 (portfolio summary, open positions, alerts section).
- `inputs/instruments.yaml` from IDS05 — for each symbol: `type` (`stock` / `etf` / `blue_chip_stock`), `sector`, `region`.
- Strategy thresholds, hardcoded as system constants (taken directly from the strategy document):
  - Sector concentration soft limit: `40%` of equity per sector
  - Geographic concentration soft limit: `50%` of equity per region
  - Position size per type:
    - ETF: minimum `20%`, maximum `30%`
    - Stock: minimum `10%`, maximum `25%`
    - Blue-chip stock: minimum `10%`, maximum `30%` (strategy raises only the maximum for blue chips)

## Output

The weekly report extended with new alert categories under `## Alerts`:

- **Sector concentration warnings** — list of sectors exceeding the 40% soft limit, with current share and the positions contributing to it.
- **Geographic concentration warnings** — same pattern for regions exceeding 50%.
- **Position size violations** — positions outside their type's allowed range (too small or too large), with the breach amount.
- **Missing classification warnings** — any open position whose symbol is not yet classified in `instruments.yaml` (delegated message that points to IDS05 reconciliation).

Per-position flag column (introduced in IDS02) is extended so concentration / sizing breaches show up there too.

## Which User problem it addresses (PRD section 2)

Closes the gap left by IDS02: the user problem mentions *"open positions violate strategy rules"*, and concentration / sizing rules are a meaningful subset of those rules. This SPEC ensures the weekly snapshot fully reflects the deterministic rule set the strategy defines, so the user no longer has to reason about exposure mentally.

## Which Functional requirements it covers (PRD section 5)

- **Strategy compliance monitoring** — completes the implementation by adding the metadata-dependent rules (position size limits, sector concentration, geographic concentration) on top of IDS02's metadata-independent rules.
- **Weekly review report** — extends the alerts section with three new alert categories.
- **Instrument metadata management** — first downstream consumer of `instruments.yaml`; surfaces missing-classification gaps as actionable warnings inside the weekly report.
