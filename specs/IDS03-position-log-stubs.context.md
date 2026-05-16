# IDS03 — Position log with auto-generated stubs

## Purpose

Introduces the position log — a per-position Markdown archive where the user records the rationale behind each open and close decision. The system handles all the mechanical work (creating files, populating metadata from XTB) so the user only contributes what XTB does not have: the *why*.

## Input

- Parsed XTB export (extension of IDS01 ingestion):
  - `Open Position` sheet (already parsed in IDS01)
  - `Closed Position History` sheet (newly required) — needed so closed positions also receive log files with their close metadata
- Position attributes used for log files: position id, symbol, type (BUY), open date, open price, close date (if closed), close price (if closed), volume, gross P&L, current SL, status (open / closed)

## Output

For every position detected in XTB data (open or closed), a Markdown file under `outputs/position_log/` named `<YYYY-MM-DD>_<SYMBOL>.md` (e.g., `2025-08-22_PZU.PL.md`). Each file contains:

- **Frontmatter (YAML)** with position metadata maintained by the system: `position_id`, `symbol`, `type`, `status` (`open` / `closed`), `open_date`, `open_price`, `close_date`, `close_price`, `volume`, `gross_pl`, `last_updated`.
- **Markdown body** with sections owned by the user:
  - `## Open rationale` — why the position was opened (signal, trend, thesis)
  - `## Close rationale` — only meaningful once the position is closed
  - `## Review history` — free-form notes added during weekly reviews

The user edits the body sections directly in their preferred editor (VS Code, Obsidian, etc.). The system **never overwrites** user-written body content. On subsequent runs the system only refreshes the frontmatter (status transitions, latest P&L, latest SL).

## Which User problem it addresses (PRD section 2)

Addresses the *learning cycle* dimension of the user problem: *"the learning cycle — build, implement, evaluate, modify — does not close"*. The position log is the artefact that makes individual trades reviewable months later, surfacing patterns and biases that intuition alone cannot recall. This SPEC provides the artefact itself; the discipline mechanism that nags about missing rationale is delivered separately in IDS04.

## Which Functional requirements it covers (PRD section 5)

- **Position log management** — full implementation of the file structure, frontmatter conventions, and non-destructive update behaviour described in the PRD.
- **XTB data ingestion** — extends the parser introduced in IDS01 by adding the `Closed Position History` sheet.
