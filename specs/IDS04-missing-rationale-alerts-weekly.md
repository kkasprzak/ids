# SPEC: Missing rationale alerts in weekly snapshot

**Depends on:** IDS01 (weekly report scaffold), IDS02 (alerts section pattern), IDS03 (position log artefact).

## User Story

As an **active investor maintaining a position log**, I want **the weekly snapshot to list every position whose open or close rationale is still empty**, so that **I am consistently reminded to document my reasoning while the context is still fresh in my memory**.

## Context

IDS03 created the position log artefact but provided no feedback loop. Without an active reminder, log files easily become a folder of empty templates — defeating the purpose of building a learning archive. This SPEC closes the loop by surfacing missing rationale as part of the regular weekly review the user already does.

The detection logic is intentionally simple: a section is "missing" if its body contains no meaningful text after the system-written heading. This catches the common case of files that were created automatically and never edited. False positives (e.g., a one-character note) are acceptable — the goal is gentle pressure, not perfect classification.

The report does not block, fail, or escalate when rationale is missing. It is a passive surface; pressure to act comes from the user seeing the same names appear week after week, not from the system enforcing anything.

## Acceptance Criteria

### Detection of missing rationale

- [ ] GIVEN an open position has a log file with an empty `## Open rationale` section
      WHEN the weekly snapshot is generated
      THEN that position is listed under the missing-rationale section of the report

- [ ] GIVEN an open position has a log file with non-empty user-written content under `## Open rationale`
      WHEN the weekly snapshot is generated
      THEN that position is not listed as missing rationale

- [ ] GIVEN a closed position has a log file with empty `## Open rationale` and / or empty `## Close rationale`
      WHEN the weekly snapshot is generated
      THEN that position is listed as missing whichever section(s) are empty

- [ ] GIVEN a closed position has user-written content in both `## Open rationale` and `## Close rationale`
      WHEN the weekly snapshot is generated
      THEN that position is not listed as missing rationale

### Report section content

- [ ] GIVEN at least one position has missing rationale
      WHEN the weekly snapshot is generated
      THEN the report contains a `## Position log status` section
      AND that section starts with a summary line stating how many open and closed positions are missing rationale
      AND each listed position references its log file path

- [ ] GIVEN every logged position has its rationale documented
      WHEN the weekly snapshot is generated
      THEN the `## Position log status` section is still present
      AND it explicitly states that all logged positions have rationale documented

- [ ] GIVEN no log files exist yet (e.g., first run before IDS03 has produced anything)
      WHEN the weekly snapshot is generated
      THEN the `## Position log status` section explicitly states that no log files were found
      AND no error is raised

### Non-interference with other report content

- [ ] GIVEN the weekly snapshot is generated
      WHEN the `## Position log status` section is added
      THEN existing sections from IDS01 (portfolio summary, open positions table) and IDS02 (alerts) remain unchanged in structure and content

## Out of Scope

- Editing log files on the user's behalf — system only reads to detect emptiness
- Interactive prompts to fill rationale during report generation — explicitly out of MVP per PRD product borders
- Quality checks on filled rationale (e.g., minimum length, structured fields) — any non-empty content counts as documented
- Aging metrics ("position open 30 days, still no rationale") — out of scope; presence/absence is the only signal
- Surfacing missing rationale in reports other than weekly — out of scope (monthly report focuses on aggregates, not log hygiene)
- Action items list including "fill rationale" — the section itself is the prompt; a consolidated weekly action list is a future enhancement
