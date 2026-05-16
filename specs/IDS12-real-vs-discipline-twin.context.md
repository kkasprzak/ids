# IDS12 — Real vs Discipline Twin comparison

## Purpose

Adds the most strategically loaded section of the monthly report: a comparison between the user's actual portfolio (Real) and a virtual shadow portfolio that mechanically applies the strategy's exit rules to the same entries (Discipline Twin). The Twin closes positions strictly at −5% from entry, realises 50% of a position when it crosses +15%, and otherwise mirrors the user's actions. Comparing both gives the user a quantified answer to a critical question: does my discretionary execution add or destroy value versus mechanical strategy execution? This is the headline input to the eventual go/no-go decision on scaling the strategy to a larger capital pool.

## Input

- Parsed XTB data from prior SPECs:
  - `Open Position` and `Closed Position History` — for entry events (Twin reuses the user's entries) and for the Real-side outcomes
  - `Cash Operation History` — for chronological cash flow used in equity reconstruction
- Strategy thresholds reused from IDS02: `−5%` stop-loss, `+15%` profit-take (50% realisation).
- Output of IDS08 (period bounds, deposited capital baseline) and IDS10 (step-curve reconstruction methodology — the same approach is applied to the Twin's equity series).

The Twin's exit logic operates on the data the system has — at minimum, it can simulate exits at the moments captured in `Cash Operation History` events and the export's snapshot end-of-period prices. Where the Twin would mechanically have exited *between* events at a price the system did not observe (e.g., an intra-day stop trigger), the simulation is approximate and uses the next available event price as the exit. This conservatism is acknowledged explicitly in the report so the user does not over-interpret small Twin–Real differences.

## Output

A new section in the monthly report — `## Real vs Discipline Twin` — placed after the reflection prompts. It contains:

- **Headline metric:** cumulative PLN difference between Real and Twin equity at the end of the report period (`Real − Twin`). A positive number means the user's discretion has added value vs mechanical execution; a negative number means it has destroyed value.
- **Period-only metric:** the same difference computed over the period (`Real period return − Twin period return`).
- **Per-closed-position breakdown table:** for every position closed in the cumulative window, columns: symbol, open date, Real close date / price / P&L, Twin close date / price / P&L (per mechanical rules), delta in PLN. This makes it visible *which* trades drove the discretion gap.
- **Equity overlay chart** (`real_vs_twin.png` in the monthly report's per-period directory): two step curves — Real (the same one as IDS10 equity curve) and Twin — over the same span, plus a small disclaimer about approximation between events.
- **Approximation caveat:** a one-paragraph note describing the Twin's exit simulation method, the data limitations (no historical intraday prices), and why small Twin–Real differences should not be over-interpreted.

## Which User problem it addresses (PRD section 2)

Targets the deepest layer of the user problem — *"decisions rely on intuition rather than hard data"* — by translating "is my discretion worth anything" from a feeling into a number in PLN. Without IDS12 the user can know that the strategy outperforms passive benchmarks (IDS08), but cannot know whether their *execution* of the strategy is the source of that outperformance or a drag on it. The headline metric is the cleanest possible input to the eventual capital-scaling decision: if mechanical execution wins, automate; if discretionary wins, the user's judgment is alpha.

## Which Functional requirements it covers (PRD section 5)

- **Discipline Twin (mechanical strategy shadow execution)** — full implementation of the requirement (shadow portfolio simulation, Real vs Twin comparison, equity overlay, per-position breakdown).
- **Monthly evaluation report** — extends with the `Real vs Discipline Twin` section.
- **Chart visualization** — adds a fourth monthly chart (`real_vs_twin.png`) using the same per-report directory pattern from IDS10.
