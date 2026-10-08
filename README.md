# Pokémon TCG Analytics Platform

The Pokémon TCG Analytics Platform collects tournament roster and deck-list data from RK9, stores it in SQLite, classifies decks into archetypes and variants, and provides reusable analytics for tournament analysis and visualization.

The project is currently focused on building a reliable data and visualization foundation. A public-facing website is planned for a later phase.

## What the project does

- Scrapes tournament rosters and public deck lists from RK9.
- Parses deck lists into structured card data.
- Stores tournaments, players, decks, cards, and classifications in SQLite.
- Classifies decks by archetype and variant using the project’s rule system.
- Calculates tournament metrics such as meta share, average finish, card inclusion, conversion, and performance index.
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

Visualization scripts are in [src/visualizations/](src/visualizations). Shared dimensions, colors, typography, and export behavior are maintained in [src/visualizations/chart_style.py](src/visualizations/chart_style.py).

Generated charts are written under `src/visualizations/output/visualizations/` by the visualization scripts.

## Testing and validation

The repository includes checks under `tests/` for the database, importer, metadata, classifier, and analytics layers. When the test runner is available, run:

```bash
python -m pytest
```

For visualization changes, run the relevant script and inspect the rendered image for clipping, overlapping labels, cut-off text, spacing, and margins.

## Project status

The scraper, database, classification system, analytics foundation, and
user-facing visualization library are in place. The next development phase is:

1. Ingest the remaining tournaments.
2. Update and validate the tournament and set metadata spreadsheets.
3. Add and validate pairings data.

The public interface remains a later phase. Pairings and round-by-round
analytics begin after the broader tournament dataset and metadata are updated.

Actual card images remain deferred until a reliable card-image source is
available.

## License

Personal analytics project.
