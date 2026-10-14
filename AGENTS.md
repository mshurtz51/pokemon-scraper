# AGENTS.md

## Project

This repository is the Pokémon TCG Analytics Platform: a Python-based tournament data scraper, database, analytics, and visualization project focused on turning Pokémon TCG tournament results into reusable analysis and public-facing data visualizations.

The long-term goal is an external Pokémon TCG analytics website. The current focus is building and validating the underlying data pipeline, analytics, and visualization library before building the public interface.

## Working Principles

- Prefer the existing project architecture over unnecessary new abstractions.
- Use existing code and established project decisions as the source of truth.
- Do not invent data, fields, tournament metadata, or project requirements.
- Do not silently change analytical definitions.
- Preserve compatibility with the existing database and analytics functions unless a change is explicitly requested.
- Inspect the current file before modifying it.
- For substantial code changes, provide the complete resulting file when practical.
- Validate Python syntax before considering a code change complete.
- Run relevant tests or scripts when practical.
- For visualizations, inspect the rendered result for clipping, overlap, cut-off text, and margins.
- Never claim a change was made or verified unless it was actually made or verified.

## User Preferences

- Direct, concise communication.
- Sequential explanations rather than huge undifferentiated dumps.
- Complete files for substantial code changes.
- Exact replacement instructions when a complete file is impractical.
- Use existing project material instead of invented substitutes.
- Check visualization layouts for clipping, overlap, cut-off text, and safe margins.
- No emojis in project-facing communication.
- Public-facing writing should be understandable to normal readers, not just developers.

## Project Structure

Known structure:

```text
pokemon_scraper/
├── AGENTS.md
├── PROJECT_CONTEXT.md
├── README.md
├── .gitignore
├── run.py
├── src/
│   ├── config.py
│   ├── database.py
│   ├── deck.py
│   ├── models.py
│   ├── roster.py
│   ├── scraper.py
│   ├── analytics_queries.py
│   └── visualizations/
├── assets/
│   ├── sets/
│   ├── logos/
│   └── cards/
└── ...
```

The exact tree may evolve. Check the workspace rather than assuming every file exists.

## Data Pipeline

Established workflow:

```text
Scrape tournament data
        ↓
Process and store data
        ↓
Analyze and create reports
        ↓
Create visualizations
        ↓
Public-facing interface
```

## RK9 Scraping

Roster information includes player ID, first name, last name, country, division, deck list link, and standing.

RK9 player IDs were obfuscated in the HTML. The project therefore uses a composite `player_key` based on first name + last name + division.

A previous validation produced approximately 2,382 parsed players and 2,382 parsed decks.

Do not change the player identity strategy without a clear reason and validation.

## Models

Established concepts:

- `Player`: `player_key`, `tournament_id`, `first_name`, `last_name`, `country`, `division`, `standing`
- `Deck`: `player_key`, `deck_url`

## Tournament Metadata

Established `Tournaments` fields:

```text
tournament_id
tournament_name
season
game
format
event_type
city
state_province
country
start_date
begin_set
end_set
notes
```

`Sets` metadata includes set information and asset filenames.

Set metadata joins to tournament boundaries through:

```text
Tournaments.begin_set / end_set
        ↕
Sets.set_code
```

Display convention:

```text
IC → International Championship
```

Tournament visualizations may display first and last included set logos from `assets/sets/`.

## Visualization System

Visualization work lives under:

```text
src/visualizations/
```

Shared styling is maintained in:

```text
src/visualizations/chart_style.py
```

Known shared style values:

```text
FIGURE_SIZE = (16, 9)
DPI = 300
BACKGROUND_COLOR = #FFFFFF
BRAND_COLOR = #A6192E
BRAND_DARK = #751324
TEXT_COLOR = #1A1A1A
SECONDARY_TEXT_COLOR = #6B6B6B
GRID_COLOR = #E6E6E6
BORDER_COLOR = #D4D4D4
TITLE_SIZE = 25
SUBTITLE_SIZE = 13
LABEL_SIZE = 11
TICK_SIZE = 10
OVERVIEW_TITLE_SIZE = 10
OVERVIEW_LABEL_SIZE = 10
OVERVIEW_VALUE_SIZE = 17
FOOTER_SIZE = 18
```

Design philosophy:

- data-first
- scannable
- strong hierarchy
- direct labels
- restrained color
- minimal unnecessary decoration
- clear context
- social-media-ready output
- consistent branding

Baseball Savant is an information-design influence, not an exact visual template.

Brand:

```text
PTCG Data Viz
```

## Archetype / Variant Naming

Use consistent labels:

```text
Dragapult
Dragapult — Straight
Dragapult — Dusknoir
Ogerpon — Teal
```

`Default` variants generally omit the suffix.

## Current Visualization Status

Completed user-facing visualizations:

1. Archetype Meta Share
2. Meta Share Timeline
3. Archetype Comparison
4. Finish Distribution

Next:

5. Card Inclusion

Remaining:

6. Card Inclusion Timeline
7. Core Cards
8. Cumulative Conversion
9. Metagame Breakdown
10. Performance Index Timeline
11. Tech Card Performance
12. Top Cut Conversion
13. Variant Compare

`meta_share_qa.py` is QA/testing, not a user-facing visualization, and should not be counted.

## Visualization Decisions

### Archetype Meta Share

- One tournament at a time.
- Horizontal bars, largest to smallest.
- User-selectable Top N.
- Overall or variant mode.
- Variant names use `Archetype — Variant`.
- Player count is inside the left/base portion of the bar.
- Percentage is outside the bar.
- `Other Archetypes` / `Other Variants` sit beneath the percentage.
- Tournament context includes type, format, set range, and optional notes.
- First and last included set logos are displayed.
- Use `Total Deck Variants`.
- `PTCG Data Viz` appears top-right.

### Meta Share Timeline

Console-like heatmap/table:

```text
Rows    = archetypes / variants
Columns = tournaments
Cells   = meta share %
Final   = Rising / Falling / Neutral
```

Cell intensity is normalized independently by tournament column. Use Top N selection and the established variant naming convention.

### Archetype Comparison

Current metrics:

```text
Players
Meta Share
Average Finish
PI Top 64
PI Top 128
PI Top 512
```

Users select 2–5 archetypes.

Performance Index:

```text
1.00x = expected representation
>1.00x = overrepresented
<1.00x = underrepresented
```

A future version may add `Made Day 2` once RK9 matchup/pairing data exists.

### Finish Distribution

Finish ranges:

```text
Top 64
65–128
129–512
513–1,024
1,025–1,499
1,500–2,499
2,500–3,499
3,500+
```

Each cell shows percentage plus field-adjusted concentration.

```text
1.0x = proportional to available finishing positions
>1.0x = overrepresented
<1.0x = underrepresented
```

Color semantics:

```text
Green  = overrepresented
Yellow = near field share
Red    = underrepresented
```

Bold = largest share of that archetype's players. Outline = strongest field-adjusted range.

## Deferred Work

Matchup, pairing, and round-by-round analytics are intentionally deferred to V3. Do not pull matchup work into the current visualization roadmap unless explicitly requested.

## Current Matchup Analytics

The user explicitly moved matchup analytics ahead of the deferred roadmap.
The RK9 pairing pipeline now stores roster/deck-enriched records in the
separate `database/pairings.db` database and materializes them in
`matchup_records`.

Completed matchup programs include:

- Archetype matchup summaries and directed matchup matrix
- Tournament-by-tournament matchup trends
- Round-level matchup cohorts with Day 2 contention
- Flattened tournament totals for round-level matchup cohorts
- Archetype performance against the full field
- Multi-tournament matchup summaries

The current matchup programs include single-tournament and aggregated
multi-tournament reports. Use the existing report runners while the matchup
visualization definitions are still being planned.

Matchup `win_rate` is match-point adjusted: wins are worth three points,
ties one point, and losses zero. `decisive_win_rate` remains available as the
wins divided by wins plus losses measure.

## Notion Project Management

The connected Notion project page is the source of truth for project-management context, including priorities, roadmap, milestones, decisions, and status. The actual repository code is the implementation source of truth.

Current Notion status:

```text
Status: Active
Current Phase: Visualization
Current Task: Archetype Comparison visualization completed
Next Up: Average Finish visualization
Priority: High
Timeline: Ongoing
```

Notion milestones currently mark Data Source Investigation, Data Acquisition & Database, and Deck Analytics & Reporting complete; Deck Visualizations in progress; and Matchup Data Integration, Matchup Analytics & Reporting, Matchup Visualizations, and Scraper Automation & Code Efficiency not started.

Active project decisions include:

- Do not build the public website yet; share visualizations socially first.
- Build one primary visualization per existing report before expanding.
- Use RK9 instead of Limitless.
- Treat matchup work as a separate later analytics cycle.
- Complete deck and matchup visualizations before automation and efficiency work.

Notion and the repository currently have a documented synchronization discrepancy. The Notion project page says Archetype Comparison is complete and Average Finish is next, while the Notion visualization task records all show `Not Started`. The repository contains four user-facing visualization implementations and treats Card Inclusion as the next item. Notion calls the existing `average_finish.py` work “Average Finish,” while repository documentation calls its output “Finish Distribution.” Do not silently reorder or relabel the roadmap; report the discrepancy and ask for direction when it affects implementation.

Keep QA/development tasks such as `meta_share_qa.py` separate from the user-facing visualization roadmap and count. The future “Made Day 2” metric remains deferred until RK9 matchup/round data exists; PI Top 512 is currently a proxy.

## Assets

```text
assets/
├── sets/
├── logos/
└── cards/
```

Set image filenames are defined by metadata and should not be guessed.

## Git

GitHub:

```text
https://github.com/mshurtz51/pokemon-scraper
```

Local:

```text
C:\Users\madis\Documents\pokemon_scraper
```

Typical workflow:

```bash
cd /c/Users/madis/Documents/pokemon_scraper
git status
git add .
git status
git commit -m "Describe the change"
git push
git status
```

Preferred final state:

```text
nothing to commit, working tree clean
```

## Before Editing

1. Inspect the current file.
2. Identify existing architecture and conventions.
3. Check whether requested behavior already exists elsewhere.
4. Make the smallest appropriate change.
5. Validate syntax.
6. Run relevant tests/scripts when practical.
7. For visualizations, inspect the rendered output.

If repository code contradicts this document, prefer the actual current code and flag the contradiction.

If a request would change an established analytical definition, schema, naming convention, or roadmap decision, ask before making the broader change.
