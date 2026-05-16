# IDS05 — Instrument metadata management

## Purpose

Introduces `instruments.yaml` — a small, user-curated mapping of every traded symbol to its sector and region. This metadata is the missing piece that unlocks position size limits per instrument type (stock vs ETF) and concentration checks (sector ≤ 40%, region ≤ 50%) in subsequent SPECs (IDS06, IDS07). The system handles discovery and stub creation; the user fills in the classification because XTB exports do not carry that information.

## Input

- Parsed XTB export (extends IDS01 ingestion):
  - `Open Position` sheet — symbols of currently held positions
  - `Closed Position History` sheet (already added in IDS03) — symbols of historically traded positions
- Existing `inputs/instruments.yaml` if present; created fresh if not.
- Allowed values for the metadata fields are defined as a small, fixed vocabulary maintained alongside the file (e.g., `sector` ∈ {financials, energy, tech, healthcare, equity_etf, bond_etf, commodities, ...}; `region` ∈ {PL, EU, US, UK, global, ...}).

## Output

- A YAML file at `inputs/instruments.yaml` mapping every symbol seen in XTB data to:
  - `type` — `stock` | `etf` | `blue_chip_stock`
  - `sector` — one of the allowed sector values, or empty placeholder if not yet classified by the user
  - `region` — one of the allowed region values, or empty placeholder if not yet classified by the user
- On first run, the file is created with stubs (empty `sector` / `region` for every symbol) so the user has something to fill rather than a blank file.
- On subsequent runs, new symbols (e.g., a recently opened position not previously seen) are appended as new stubs without touching existing entries.
- The system validates the file: any symbol referenced by an existing or closed position must be present; any entry with empty `sector` or `region` is reported as needing classification.

The file lives in `inputs/` (not `outputs/`) because it is user-curated configuration, versioned in Git so changes are traceable.

## Which User problem it addresses (PRD section 2)

This SPEC does not directly address the user-facing problem on its own — its value is enabling the concentration alerts (IDS06) and pre-purchase compliance check (IDS07) that *do* address the problem. It is delivered as a separate vertical slice because (a) curating the mapping is a one-off user task that benefits from being done in isolation, and (b) the artefact has independent value: the user can inspect / search by sector or region even before any consumer SPEC exists.

## Which Functional requirements it covers (PRD section 5)

- **Instrument metadata management** — full implementation of stub generation, append-on-new-symbol behaviour, validation, and warning for symbols missing classification.
- **XTB data ingestion** — reuses the parser from IDS01 / IDS03 for symbol discovery; no new sheets required.
