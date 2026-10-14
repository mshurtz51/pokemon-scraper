# Pokémon TCG Analytics Platform

The Pokémon TCG Analytics Platform collects tournament roster and deck-list data from RK9, stores it in SQLite, classifies decks into archetypes and variants, and provides reusable analytics for tournament analysis and visualization.

The project is currently focused on building a reliable data and visualization foundation. A public-facing website is planned for a later phase.

## What the project does

- Scrapes tournament rosters and public deck lists from RK9.
- Parses deck lists into structured card data.
- Stores tournaments, players, decks, cards, and classifications in SQLite.
- Classifies decks by archetype and variant using the project’s rule system.
- Calculates tournament metrics such as meta share, average finish, card inclusion, conversion, and performance index.
- Ingests RK9 pairings into a separate SQLite database for matchup analysis.
- Reports matchup rates by archetype, round, Day 2 contention, and opponent field.
- Queues round-level archetype and variant field composition among Day 2 contenders.
- Produces reusable Matplotlib visualizations for tournament and metagame analysis.

## Data pipeline

```text
RK9 tournament pages
        ↓
Scrape rosters and deck lists
        ↓
Parse and store data in SQLite
        ↓
Classify decks into archetypes and variants
        ↓
Run analytics and generate visualizations
```

## Repository layout

```text
pokemon_scraper/
├── assets/
│   └── sets/                    # Set artwork used by visualizations
├── metadata/
│   └── metadata.xlsx            # Tournament and set metadata
├── src/
│   ├── analytics/               # Console analytics and reports
│   ├── visualizations/          # Chart scripts and shared chart styling
│   ├── analytics_queries.py     # Reusable database queries for analysis
│   ├── classifier.py            # Deck classification rules
│   ├── classifier_sync.py       # Store classifications in the database
│   ├── database.py              # SQLite schema and database operations
│   ├── deck.py                  # Deck-list parsing
│   ├── importer.py              # Import and synchronize tournament data
│   ├── metadata.py              # Tournament and set metadata helpers
│   ├── models.py                # Project data models
│   ├── roster.py                # Roster parsing
│   └── scraper.py               # RK9 page retrieval
├── tests/                       # Database, importer, classifier, metadata, and analytics checks
├── run.py                       # Main ETL and classification entry point
└── CHANGELOG.md                 # Project change history
```

Generated or local-only folders such as `database/`, `raw/`, `exports/`, and Python cache folders are not part of the source code.

## Getting started

### Requirements

Use Python 3.10 or newer. Install the project’s Python dependencies in a virtual environment before running the pipeline.

The repository does not currently include a dependency lockfile or `requirements.txt`; inspect the imports in `src/` when setting up a new environment.

### Run the data pipeline

From the repository root:

```bash
python run.py
```

The pipeline creates the SQLite database when needed, synchronizes tournament data, and synchronizes deck classifications. Network access to RK9 is required when new data must be downloaded.

## Database

The SQLite database is created at `database/pokemon.db`.

Pairings are stored in `database/pairings.db` and enriched matchup records are
stored in the `matchup_records` table.

The main tables are:

| Table | Purpose |
| --- | --- |
| `tournaments` | Tournament names, dates, formats, locations, set boundaries, and notes |
| `players` | Player identity, division, standing, archetype, variant, and classification data |
| `decks` | Player-to-deck-list relationships |
| `deck_cards` | Parsed cards and quantities for each deck |

Player identity uses the project’s composite `player_key` based on first name, last name, and division. This preserves the established handling of obfuscated RK9 player IDs.

## Analytics and visualizations

Reusable database queries are in [src/analytics_queries.py](src/analytics_queries.py). Console analytics are in [src/analytics/](src/analytics), including:

- Archetype and variant meta share
- Meta share timelines
- Average finish and finish distribution analysis
- Card inclusion and card inclusion timelines
- Core cards and tech-card performance
- Cumulative conversion and top-cut conversion
- Performance index timelines
- Metagame variant breakdowns

The current user-facing visualization roadmap is complete through Top Cut
Conversion. Variant Compare was intentionally removed because it overlapped
too closely with the existing Metagame Variant Breakdown visualization.

Matchup reports can be run from the repository root:

```bash
python run_matchup_report.py --tournament-id TU01w1D52rjGebrE8szS --archetype Dragapult --opponent Alakazam
python run_field_performance.py --tournament-id TU01w1D52rjGebrE8szS
python run_round_performance.py --tournament-id TU01w1D52rjGebrE8szS --archetype Dragapult
python run_multi_matchup_report.py --archetype Dragapult
```

The round-performance report shows each archetype's games, wins, losses,
ties, and decisive win rate by round. Use `--day-2-filter yes` or
`--day-2-filter no` to isolate the Day 2 contention breakdown.
The multi-tournament matchup report aggregates directed archetype matchups
across all stored tournaments, or across selected tournaments when
`--tournament-id` is repeated.

The Day 2 field-composition report uses each round's
stored contention flags to show how the archetype and variant mix among players
still eligible for Day 2 differs from the full-tournament mix.

Compare the Day 2 field composition between rounds with:

```bash
python run_day_two_meta_delta.py --tournament-id TU01w1D52rjGebrE8szS
python run_day_two_meta_delta.py --tournament-id TU01w1D52rjGebrE8szS --variants
```

The Day 2 survival curve compares each archetype's round-by-round conversion
against its round-one contenders and the field-wide conversion baseline:

```bash
python run_day_two_survival.py --tournament-id TU01w1D52rjGebrE8szS --archetype Crustle
python run_day_two_survival.py --tournament-id TU01w1D52rjGebrE8szS --round 8
```

Card-level matchup performance can be inspected for a selected directed
archetype matchup:

```bash
python run_card_matchup_report.py --tournament-id TU01w1D52rjGebrE8szS --archetype Crustle --opponent Dragapult
```

The report compares each card's results when present in the selected
archetype's deck versus when absent, using the stored deck-card lists.

For the focused tech-card matchup analysis, select one archetype and card:

```bash
python run_tech_card_matchup.py --tournament-id TU01w1D52rjGebrE8szS --archetype Crustle --card "Tool Scrapper"
python run_tech_card_matchup.py --archetype Dragapult --variant Dusknoir --card "Meowth ex" --variants
```

This reports each opponent matchup twice—when the card is present and when it
is absent—with games, wins, losses, ties, match-point win rate, tie rate,
decisive win rate, and the with-card deltas.

The tech-card report checks the selected card in the opponent's deck. The
selected archetype is the focal deck whose win rate is measured. Omit
`--tournament-id` to aggregate all stored tournaments. Use `--variants` to
group opponents by variant, or add `--variant` to select one exact focal
variant.
The command also prints a `TOTAL` row calculated from all games rather than
averaging opponent rows.

Matchup `win_rate` uses the tournament scoring convention: a win contributes
three points, a tie contributes one point, and a loss contributes zero.
Therefore, `win_rate` is `(wins * 3 + ties) / (games * 3)`. Reports also
retain `decisive_win_rate`, which excludes ties from its denominator.

Visualization scripts are in [src/visualizations/](src/visualizations). Shared dimensions, colors, typography, and export behavior are maintained in [src/visualizations/chart_style.py](src/visualizations/chart_style.py).

Generated charts are written under `src/visualizations/output/visualizations/` by the visualization scripts.

## Testing and validation

The repository includes checks under `tests/` for the database, importer, metadata, classifier, and analytics layers. When the test runner is available, run:

```bash
python -m pytest
```

For visualization changes, run the relevant script and inspect the rendered image for clipping, overlapping labels, cut-off text, spacing, and margins.

## Project status

The scraper, database, classification system, analytics foundation, matchup
data layer, and user-facing visualization library are in place. The current
development phase is:

1. Finish and validate the matchup analytics programs.
2. Build matchup visualizations after the analytics definitions are stable.
3. Continue improving ingestion automation and runtime efficiency.

The public interface remains a later phase.

Actual card images remain deferred until a reliable card-image source is
available.

## License

Personal analytics project.
