# SPEC: Position log with auto-generated stubs

**Depends on:** IDS01 (XTB ingestion foundation, file path conventions, CLI subcommand pattern).

## User Story

As an **active investor learning from each trade I take**, I want **a per-position Markdown log automatically populated with metadata from my XTB exports and structured sections where I write my own rationale**, so that **I have a durable, reviewable archive of why I opened and closed each position without spending energy on bookkeeping**.

## Context

The position log is the artefact the strategy document calls *"fundament nauki inwestowania"*. Without it, the user cannot recall why a position was taken months later, cannot review whether decisions followed the strategy, and cannot spot patterns in their own behaviour. This SPEC creates the artefact and the rules under which the system maintains it.

The split of responsibility is deliberate:

- **System owns the metadata.** Position id, symbol, dates, prices, P&L, SL, status — anything XTB knows or anything mechanically derivable. The system writes and refreshes these in the YAML frontmatter on every run.
- **User owns the narrative.** Open rationale, close rationale, review notes — anything that lives only in the user's head. The system writes empty section headers as scaffolding and never touches that content again.

This boundary is enforced by treating frontmatter and Markdown body as separate write zones: frontmatter is fully managed by the system; the body below is append-only from the system's perspective (it can add new section headers if scaffolding evolves, but it never modifies or deletes user-written prose).

The discipline loop that prompts the user to actually fill in the rationale (alerts in the weekly report) is delivered separately in IDS04. This SPEC delivers the artefact in isolation; even with no nagging, it is independently valuable because the user can start writing rationale immediately.

## Acceptance Criteria

### Log file generation

- [ ] GIVEN an XTB export contains an open position not yet present in the log
      WHEN the position log is updated
      THEN a new Markdown file is created under `outputs/position_log/` named `<open_date>_<symbol>.md`
      AND it contains YAML frontmatter populated with position metadata (`position_id`, `symbol`, `type`, `status`, `open_date`, `open_price`, `volume`, `gross_pl`, `last_updated`)
      AND it contains empty body sections: `## Open rationale`, `## Close rationale`, `## Review history`

- [ ] GIVEN an XTB export contains a closed position not yet present in the log
      WHEN the position log is updated
      THEN a new Markdown file is created with status `closed` in frontmatter
      AND it includes `close_date`, `close_price`, and final `gross_pl` in frontmatter

- [ ] GIVEN multiple positions exist for the same symbol opened on different dates
      WHEN the position log is updated
      THEN each position has its own log file (filename uniqueness comes from open date plus symbol)

### Frontmatter refresh on subsequent runs

- [ ] GIVEN a log file exists for an open position
      WHEN the position log is updated and the position is still open in XTB
      THEN frontmatter fields that change (`gross_pl`, `last_updated`, current `SL`) are refreshed
      AND no other frontmatter fields are modified

- [ ] GIVEN a log file exists for a position that was open in a previous run and is now closed in XTB
      WHEN the position log is updated
      THEN the frontmatter `status` transitions from `open` to `closed`
      AND `close_date`, `close_price`, and final `gross_pl` are written into frontmatter

### Non-destructive body handling

- [ ] GIVEN a log file exists with user-written content under `## Open rationale`
      WHEN the position log is updated
      THEN that user content is preserved exactly as written

- [ ] GIVEN a log file exists with user-written content under `## Close rationale` or `## Review history`
      WHEN the position log is updated
      THEN that user content is preserved exactly as written

### Run integration

- [ ] GIVEN the user invokes a command that triggers position log update
      WHEN the command runs
      THEN the log directory is reconciled with the latest XTB export in a single pass (new files created, existing frontmatter refreshed, statuses transitioned where applicable)

## Out of Scope

- Alerts about missing rationale in the weekly report — covered by IDS04
- Interactive prompts asking the user to fill rationale at the moment a position is detected — explicitly out of MVP per PRD product borders (user fills directly in the editor)
- AI-generated suggestions for rationale text — explicitly out of MVP per PRD product borders
- Move / archive of closed-position log files into a separate folder — flat directory with status in frontmatter is sufficient
- Manual editing of frontmatter by the user — frontmatter is system-owned and may be overwritten on the next run
- Surfacing position log content inside generated reports — out of scope for this SPEC; reports may reference the log directory but do not embed log content
