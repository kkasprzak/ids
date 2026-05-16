# IDS11 — Monthly reflection prompts

## Purpose

Closes the monthly report with a section of structured reflection prompts derived from the period's data. The strategy treats the user as the sole author of strategy modifications — the system never proposes changes or rewrites rules. What it does provide here is a small set of pointed questions, automatically populated with the period's facts, that prompt the user to think systematically about whether the strategy still serves them. This is the bridge between "evaluate" and "modify" in the build–implement–evaluate–modify cycle.

## Input

- Outputs of IDS08 (period and cumulative performance vs benchmarks) and IDS09 (closed-trade statistics, rule adherence retrospective) — these provide the facts that prompts reference.
- Position log directory (from IDS03) — for cross-referencing trades whose rationale the user may want to revisit while reflecting.
- A small set of **prompt templates** maintained as system constants. Each template is a question with placeholders that get filled from the period's data (e.g., "Why did position X close beyond the −5% limit?"). The templates are deliberately fixed and limited; the system does not generate prompts dynamically with an LLM.

## Output

A new section in the monthly report — `## Reflection prompts` — containing a short list of generated questions. Each prompt is one to three lines, references concrete data from the period (a number, a symbol, a metric outcome), and is phrased as an open question that the user answers in their head, in their notes, or by editing the active strategy document.

Examples of generated prompt categories (final templates are part of this SPEC's implementation):

- **Rule adherence:** "Two losing trades in this period exceeded the −5% threshold (FRO.PL, KRU.PL). Was the deviation deliberate, or did execution discipline slip? If deliberate, does the strategy need to encode that exception?"
- **Outperformance attribution:** "The portfolio is ahead of the bank deposit benchmark by 3.1pp this period. Which positions drove that? Are those signals repeatable?"
- **Underperformance:** "The portfolio is behind the rental property benchmark cumulatively. What would need to change for the strategy to be worth the time vs leaving capital in passive instruments?"
- **Position-log hygiene:** "Three closed positions this period have empty close-rationale fields. Is the rationale capture cadence working?"

The number of prompts is small (target 3–6 per report). If a category has nothing meaningful to ask in a given period (e.g., no rule violations), the prompt for that category is omitted rather than producing a vacuous question.

## Which User problem it addresses (PRD section 2)

Closes the *learning cycle* loop. IDS08, IDS09, and IDS10 deliver evaluation data; without a structured pause to reflect, that data flows past the user without changing anything — the very pattern the user identified as their original pain ("decisions opierają się na intuicji zamiast twardych danych"). Prompts force a brief, recurring moment of structured thinking, which is exactly the friction needed to convert observation into strategy modification.

## Which Functional requirements it covers (PRD section 5)

- **Monthly evaluation report** — adds the `Reflection prompts` section described in the functional requirement.
