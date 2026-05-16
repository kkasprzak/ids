# IDS04 — Missing rationale alerts in weekly snapshot

## Purpose

Closes the discipline loop around the position log: the weekly snapshot now reminds the user about positions whose rationale fields are still empty. Without this nudge, the log from IDS03 risks becoming a dormant folder of empty templates; with it, the user gets gentle weekly pressure to document while context is still fresh.

## Input

- Output of IDS03 — position log directory `outputs/position_log/` with Markdown files (frontmatter + body sections).
- For each log file, the system reads:
  - Frontmatter (to identify the position and its status)
  - Body sections — `## Open rationale`, `## Close rationale` — to detect emptiness
- A section is considered "empty" if it contains no meaningful text (i.e., only whitespace or scaffolding placeholders left as written by the system).

## Output

The weekly report (the file from IDS01 / IDS02) extended with:

- **`## Position log status` section** listing positions whose rationale is missing:
  - Open positions with empty `## Open rationale`
  - Closed positions with empty `## Open rationale` and / or `## Close rationale`
- Each entry is a clickable / referenceable filename pointing to the relevant log file.
- A summary line at the top of the section (e.g., *"3 open positions and 1 closed position are missing rationale"*).

If no rationale is missing, the section explicitly states that all logged positions have rationale documented.

## Which User problem it addresses (PRD section 2)

Reinforces the *learning cycle* dimension of the problem and connects to *Decision traceability* in success metrics. IDS03 made the log possible; without IDS04 the user might never look at it again. The alert turns the log from a passive artefact into an active accountability mechanism, helping ensure the build-implement-evaluate-modify cycle actually closes.

## Which Functional requirements it covers (PRD section 5)

- **Weekly review report** — extends the report with the `Position log status` section described in the functional requirement.
- **Position log management** — implements the "report missing rationale" half of the requirement (IDS03 implemented the artefact half).
