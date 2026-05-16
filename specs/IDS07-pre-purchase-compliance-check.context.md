# IDS07 — Pre-purchase compliance check

## Purpose

Provides a one-shot CLI command that validates a candidate purchase against every strategy rule before the user places the order in XTB. Unlike weekly snapshots which evaluate the *current* portfolio, this command evaluates a *hypothetical post-purchase* portfolio and reports which rules the candidate would violate or breach. This is the system's check-in surface — the strategy explicitly defines pre-purchase questions ("Czy już mam ekspozycję na ten sektor / region? Czy te pozycje nie spadną jednocześnie?") and this SPEC operationalises them.

## Input

- Candidate purchase parameters provided by the user:
  - `symbol` — the instrument to buy
  - `type` — `stock` | `etf` | `blue_chip_stock` (optional if symbol already classified in `instruments.yaml`)
  - `value` — planned position value in PLN (volume × price equivalent)
- Latest XTB export — for the current state of equity, cash, and existing positions.
- `inputs/instruments.yaml` from IDS05 — for sector and region of the candidate symbol and existing holdings.
- Same rule constants used elsewhere (size limits, 40% sector / 50% region, 10% cash reserve).

Inputs not supplied as flags are interactively prompted (default behaviour from the CLI design choice in PRD).

## Output

A structured verdict printed to the terminal containing, for each rule:

- **Position size** — would the candidate fit between minimum and maximum for its type?
- **Cash reserve impact** — would cash drop below 10% of equity after the purchase?
- **Sector concentration impact** — would the sector containing this symbol exceed 40% of equity after purchase?
- **Geographic concentration impact** — would the region containing this symbol exceed 50% of equity after purchase?
- **Classification readiness** — does `instruments.yaml` have a complete entry for this symbol?

Each rule is reported with status `pass` / `warning` / `fail`, the relevant before/after numbers, and a concise verdict line at the end (e.g., "OK to proceed", "OK with warnings: 2", "Rule violations: 1").

The check is **advisory**, not blocking — the system never refuses to print a verdict, never edits XTB, and never prevents the user from making the purchase. Its job is to make consequences visible before commitment.

## Which User problem it addresses (PRD section 2)

Addresses the screening dimension of the user problem and a long-standing pain the user named explicitly: "now I sometimes open the XTB app and check positions manually." Pre-purchase compliance moves the rule check from a mental task done in front of a phone to a deterministic, repeatable command that operates on the same data and rules as the weekly snapshot. The "decisions on intuition rather than hard data" failure mode is most acute at the moment of buying — this SPEC inserts hard data exactly there.

## Which Functional requirements it covers (PRD section 5)

- **Pre-purchase compliance check** — full implementation of the functional requirement, reusing the rule evaluation engine from IDS02 and IDS06 plus the instrument metadata from IDS05.
- **CLI interface** — second subcommand after `report weekly`; demonstrates the flag-and-prompt input pattern (flags supplied directly are accepted; missing ones are prompted interactively).
- **Instrument metadata management** — second downstream consumer of `instruments.yaml`; reuses the missing-classification handling pattern established in IDS06.
