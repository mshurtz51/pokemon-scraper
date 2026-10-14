# PROJECT_CONTEXT.md

# Pokémon TCG Analytics Platform — Project Context

This document captures the accumulated project decisions and context from development of the Pokémon TCG Analytics Platform. It gives Codex the useful project history that would otherwise live only in prior ChatGPT conversations.

## 1. Project Vision

The project is intended to become a public Pokémon TCG analytics platform.

The goal is to take tournament/decklist data, make it queryable, analyze it consistently, and turn the results into polished data visualizations.

The project is being built in stages rather than building the public website first.

Established workflow:

```text
Scraping
    ↓
Processing / Storage
    ↓
Analytics / Reports
    ↓
Visualization
    ↓
Public Interface
```

The user prefers finishing the analytics and visualization foundation before building the website.

## 2. Development Environment

Primary environment:

```text
Windows
Python
Spyder
SQLite
Pandas
Matplotlib
Git / GitHub
```

Local project:

```text
C:\Users\madis\Documents\pokemon_scraper
```

GitHub:

```text
https://github.com/mshurtz51/pokemon-scraper
```

## 3. Project Evolution

The project began as an RK9 tournament roster/decklist scraper and evolved into a broader analytics platform.

Current emphasis:

- reliable tournament data
- reusable analytics queries
- archetype/variant handling
- polished visualizations
- tournament metadata and assets
- eventual public-facing website

Advanced matchup/pairing analytics were intentionally postponed to V3.

The user later explicitly authorized matchup work. RK9 pairings are now
ingested alongside roster and deck data into `database/pairings.db`, with an
enriched `matchup_records` table joining player keys, deck URLs, outcomes,
archetypes, variants, rounds, records, and points.

Current matchup analytics include directed matchup matrices, tournament
trends, round-level matchup cohorts, Day 2 contention breakdowns, flattened
tournament totals, archetype performance against the full field, overall
archetype performance by round, and aggregated multi-tournament matchup
summaries. Matchup visualizations remain planned after the analytics reports
are reviewed. Matchup `win_rate` uses match-point weighting, with ties worth
one third of a win; `decisive_win_rate` remains available for comparisons that
exclude ties.

Queued next: a round-level archetype and variant field-composition report
using the stored Day 2 contention flags, so later rounds can be compared with
the tournament-wide deck mix.

## 4. RK9 Scraper

Target pages include RK9 tournament roster and decklist pages.

Roster information includes:

```text
playerid
first name
last name
country
division
deck list link
standing
```

RK9 player IDs were obfuscated in the HTML and were not used as the primary identity key.

Established identity:

```text
first name + last name + division
```

stored as `player_key`.

A previous validation produced:

```text
Players parsed: 2382
Decks parsed: 2382
```

The project noted a one-player difference from another reference source, associated with a drop/DQ situation.

Existing scraper concepts include:

```text
src/config.py
src/database.py
src/deck.py
src/models.py
src/roster.py
src/scraper.py
run.py
```

## 5. Data Models

Established concepts:

```text
Player
- player_key
- tournament_id
- first_name
- last_name
- country
- division
- standing

Deck
- player_key
- deck_url
```

The database is intended to support reusable tournament analytics.

## 6. Tournament Metadata

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

`Sets` metadata contains set information and asset filenames.

Tournament boundaries link through:

```text
Tournaments.begin_set
Tournaments.end_set
        ↕
Sets.set_code
```

Display convention:

```text
IC → International Championship
```

Tournament notes can be entered by the visualization console:

```text
Tournament Notes
Enter notes for this tournament (press Enter to leave blank):
```

## 7. Assets

Intended asset structure:

```text
assets/
├── sets/
├── logos/
└── cards/
```

Set image filenames are controlled by the set metadata.

## 8. Visualization System

Visualization work lives under:

```text
src/visualizations/
```

Shared styling:

```text
src/visualizations/chart_style.py
```

Known style constants:

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

These are project conventions and should be reused.

## 9. Design Philosophy

The user wants professional sports/data analytics information design.

Principles:

- information first
- scannable
- clear hierarchy
- direct labels
- restrained color
- minimal decoration
- useful context
- social-media-ready output
- consistency across charts

Baseball Savant was discussed as an information-design influence. The goal is to learn from its data-first/scannable philosophy, not copy its exact visual style.

Generic Matplotlib-looking charts are not the desired end state.

## 10. Branding

Visualization brand:

```text
PTCG Data Viz
```

`Data Viz` is visually important.

Current convention places `PTCG Data Viz` in the top-right area of visualizations.

## 11. Archetype / Variant Naming

Consistent examples:

```text
Dragapult
Dragapult — Straight
Dragapult — Dusknoir
Ogerpon — Teal
```

`Default` variants generally omit the suffix.

This naming convention should be consistent across all visualizations.

## 12. Completed Visualizations

### 12.1 Archetype Meta Share

Purpose: show composition of a single tournament field.

Established design:

- one tournament
- horizontal bars
- largest to smallest
- user-selectable Top N
- overall or variant mode
- player count inside the left/base portion of the bar
- percentage outside the bar
- `Other Archetypes` / `Other Variants` beneath the percentage
- tournament context panel
- included set logos
- optional notes
- PTCG Data Viz branding

Wording:

```text
Total Deck Variants
```

Tournament context generally follows:

```text
Tournament Type: International Championship
Format: Standard

From:       To:
[first set] [last set]
```

### 12.2 Meta Share Timeline

Purpose: show representation changes across tournaments.

It was intentionally designed as a console-like heatmap/table rather than a standard line chart.

Structure:

```text
Rows    = archetypes / variants
Columns = tournaments
Cells   = meta share %
Final   = Rising / Falling / Neutral
```

Cell intensity is normalized independently within each tournament column.

Top N selection is used.

Variant labels follow the established naming convention.

### 12.3 Archetype Comparison

Purpose: compare selected archetypes within one tournament.

Current fields:

```text
Players
Meta Share
Average Finish
PI Top 64
PI Top 128
PI Top 512
Made Day 2
```

Users select 2–5 archetypes.

Performance Index:

```text
1.00x = expected representation
>1.00x = overrepresented
<1.00x = underrepresented
```

Example interpretation previously established:

For approximately 3.2% meta share:

```text
64 × 0.032 ≈ 2.05
```

expected Top 64 players.

A PI Top 64 around 2.90x means roughly 2.90 times expected representation, not 290% meta share.

A future iteration may add `Made Day 2` after RK9 matchup/pairing data becomes available.

### 12.4 Finish Distribution

Purpose: show where players using each archetype/variant finished.

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

Each cell contains:

```text
% = percentage of that deck's players in the range
x = field-adjusted concentration
```

Concentration:

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

Additional conventions:

```text
Bold    = largest share of that archetype's players
Outline = strongest field-adjusted range
```

The user explicitly liked this visualization and considered it informative enough to move on.

## 13. Visualization Roadmap

Completed:

```text
1. Archetype Meta Share
2. Meta Share Timeline
3. Archetype Comparison
4. Finish Distribution
```

Next:

```text
5. Card Inclusion
```

Remaining:

```text
6. Card Inclusion Timeline
7. Core Cards
8. Cumulative Conversion
9. Metagame Breakdown
10. Performance Index Timeline
11. Tech Card Performance
12. Top Cut Conversion
13. Variant Compare
```

`meta_share_qa.py` is QA/testing, not a user-facing visualization.

Notion currently lists the visualization task order as Archetype Comparison,
Average Finish, Card Inclusion, Card Inclusion Timeline, Core Cards, Cumulative
Conversion, Meta Share, Meta Share Timeline, Metagame Breakdown, Performance
Index Timeline, Tech Card Performance, Top Cut Conversion, and Variant Compare.
The Notion task records currently show these tasks as `Not Started`, which is
not synchronized with the repository implementation or the Notion project
page. Keep QA/development tasks such as `meta_share_qa.py` separate from the
user-facing visualization count.

The repository currently has four user-facing visualization implementations:
Archetype Meta Share, Meta Share Timeline, Archetype Comparison, and Finish
Distribution. Notion calls the existing `average_finish.py` work “Average
Finish,” while the repository documentation refers to its user-facing output
as “Finish Distribution.” This naming difference must be resolved explicitly
before changing the roadmap order.

## 14. Analytics History

Analytics work has included:

- archetype/meta share
- variants
- average finish
- Performance Index
- card inclusion
- conversion metrics
- core cards
- tech-card performance
- timeline analysis

The user intentionally dropped several advanced analytics ideas from the near-term roadmap.

Do not reintroduce abandoned analytics without discussing them first.

## 15. Matchup / Pairing Data

Matchup, pairing, and round-by-round data is planned for V3.

Eventually the project wants outputs such as:

```text
round-by-round player vs player
player → deck
```

and matchup data integrated into the queryable database.

This is deliberately deferred. Do not derail current visualization work to build it unless explicitly requested.

## 16. Notion Project Management

The project is also tracked in Notion.

Main project:

```text
Pokémon TCG Analytics Platform
```

Notion has tracked fields such as:

```text
Current Phase
Current Task
Goal
Next Up
Priority
Status
Timeline
Notes
Public
```

Notion is project-management context; repository code is the implementation source of truth.

Current Notion project status:

```text
Status: Active
Current Phase: Visualization
Priority: High
Timeline: Ongoing
Current Task: Archetype Comparison visualization completed
Next Up: Average Finish visualization
```

Notion milestone status is currently:

```text
Data Source Investigation: Complete
Data Acquisition & Database: Complete
Deck Analytics & Reporting: Complete
Deck Visualizations: In Progress
Matchup Data Integration: Not Started
Matchup Analytics & Reporting: Not Started
Matchup Visualizations: Not Started
Scraper Automation & Code Efficiency: Not Started
```

Active project-management decisions are:

- Do not build the public website yet; share visualizations socially first.
- Build one primary visualization per existing report before expanding.
- Use RK9 instead of Limitless as the primary tournament data source.
- Treat matchup data, analytics, and visualizations as a separate later cycle.
- Complete deck and matchup visualizations before automation and efficiency work.

The Notion project page and task database are not currently synchronized. The
project page identifies Archetype Comparison as complete and Average Finish as
next, while the task database marks all visualization tasks as `Not Started`.
The repository implementation and generated outputs confirm that four
user-facing visualizations exist. Do not resolve this discrepancy by guessing;
use the repository for implementation status and Notion for approved project
priorities until the task records are deliberately updated.

Notion also records that a future “Made Day 2” metric should be added only
after RK9 matchup/round data is available. PI Top 512 is currently a temporary
proxy for that metric.

## 17. Git Workflow

Typical end-of-day workflow:

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

## 18. Development Lessons

### Inspect the actual current file

Earlier visualization work produced bad results when an older/reconstructed version of a file was edited instead of the exact current source.

Therefore:

- inspect the actual current file
- preserve current functionality
- make targeted edits
- validate the resulting source

Never claim a modification was made without checking it.

### Verify visualization geometry

For visualizations, inspect:

- clipping
- text overlap
- margins
- figure bounds
- title/subtitle spacing
- panel alignment
- logo sizing
- footer placement
- label collisions

The user wants a checked result, not a first draft with obvious layout problems.

### Avoid unnecessary rewrites

Do not reconstruct a working visualization from scratch for a small change.

Prefer targeted modifications.

## 19. Current State

At the time this context was created:

- scraper foundation exists
- database/query architecture exists
- tournament metadata/assets are established
- visualization system exists
- four user-facing visualizations are complete
- next visualization is Card Inclusion
- public-facing website remains a later phase
- matchup/pairing analytics remain V3

Immediate development focus:

```text
Card Inclusion visualization
```

Notion currently identifies Average Finish as the next task, but the repository
already contains `src/visualizations/average_finish.py` and an
`average_finish.png` output. The existing repository roadmap therefore treats
Card Inclusion as next after the four completed user-facing visualizations.
Confirm the intended definition of “Average Finish” versus “Finish
Distribution” before changing that order.

Unless the project owner changes priorities, repository implementation work
should follow the actual code state while roadmap and priority decisions should
be checked against Notion.
