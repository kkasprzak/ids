# SPEC: Instrument metadata management

**Depends on:** IDS01 (XTB ingestion of `Open Position` sheet), IDS03 (XTB ingestion of `Closed Position History` sheet for historical symbol discovery).

## User Story

As an **active investor**, I want **a configuration file mapping each symbol I have ever traded to its instrument type, sector, and region, with stubs auto-generated whenever a new symbol appears in my XTB data**, so that **I can curate this classification once per symbol and rely on it for downstream concentration and position-size checks without re-classifying repeatedly**.

## Context

Concentration limits (sector ≤ 40%, region ≤ 50%) and position size limits per instrument type (stock vs ETF, with a blue-chip exception up to 30%) are core rules of the active strategy. None of this information is present in the XTB export — XTB knows the symbol and the price, but not whether `V80A.DE` is a bond ETF or what region `KRU.PL` belongs to. Without metadata the system cannot enforce these rules.

The metadata is intentionally **user-owned**. Auto-classification via external APIs or LLMs is out of MVP scope (per PRD product borders) because (a) at ~10–20 instruments the manual cost is trivial, and (b) the user benefits from explicitly thinking about how each instrument fits into the strategy.

The system's contribution is mechanical: discover symbols from XTB data, generate stubs the user can fill, validate that nothing is missing, and surface the gaps as warnings. Once filled, the entries are stable — the system never touches a symbol's classification after the user has provided it.

The vocabulary for `sector` and `region` is intentionally small and grow-only: the user can introduce new values when needed, and the system accepts them as long as they are consistent with what the file declares.

## Acceptance Criteria

### Initial stub generation

- [ ] GIVEN no `inputs/instruments.yaml` exists
      WHEN the metadata is reconciled with the latest XTB export
      THEN the file is created
      AND it contains one entry per symbol observed across both `Open Position` and `Closed Position History`
      AND every entry has an empty `sector` and `region`, and a placeholder `type`

- [ ] GIVEN `inputs/instruments.yaml` does not exist
      WHEN the metadata is reconciled
      THEN entries are sorted in a stable, deterministic order (e.g., alphabetical by symbol)

### Appending new symbols

- [ ] GIVEN `inputs/instruments.yaml` exists with entries for every previously known symbol
      WHEN the user opens a new position with a symbol not yet in the file
      THEN reconciliation appends a new stub entry for that symbol
      AND existing entries are not modified in any way (order, fields, comments preserved)

### Preservation of user-curated values

- [ ] GIVEN `inputs/instruments.yaml` contains entries with user-filled `sector` and `region`
      WHEN reconciliation runs
      THEN those values are preserved exactly as written

- [ ] GIVEN the user has added comments or formatting to `inputs/instruments.yaml`
      WHEN reconciliation runs
      THEN those comments and formatting are preserved where technically possible

### Validation and warnings

- [ ] GIVEN one or more entries in `inputs/instruments.yaml` have an empty `sector`, empty `region`, or placeholder `type`
      WHEN any system command that depends on instrument metadata is invoked
      THEN a warning lists every symbol with missing classification
      AND the warning indicates which fields are missing per symbol

- [ ] GIVEN every symbol in the latest XTB export has a corresponding entry in `inputs/instruments.yaml`
      WHEN reconciliation runs
      THEN no missing-symbol warning is raised

- [ ] GIVEN `inputs/instruments.yaml` references a symbol that has never appeared in XTB data
      WHEN reconciliation runs
      THEN the entry is left in place (the user may have added it pre-emptively)
      AND no error is raised

### Reconciliation trigger

- [ ] GIVEN any system command runs that depends on instrument metadata
      WHEN the command starts
      THEN reconciliation runs first to ensure the file is up to date with current XTB data

## Out of Scope

- Automatic / AI-based classification of `sector`, `region`, or `type` — explicitly out of MVP per PRD product borders
- Enforcement of a closed vocabulary for `sector` / `region` — the file accepts any user-provided string consistent with itself
- Use of the metadata in alerts, reports, or compliance checks — covered by IDS06 (concentration), IDS07 (pre-purchase)
- Versioned history of classification changes beyond Git history — Git is sufficient
- A dedicated CLI subcommand to edit entries interactively — the user edits the YAML file directly
- Rich attributes beyond `type`, `sector`, `region` (e.g., currency, ISIN, exchange) — out of MVP; can be added later if needed
