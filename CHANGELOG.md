# Changelog

All notable changes to this project will be documented here.

---

## v0.1.0 - Initial Release

### Added

- Project structure
- GitHub repository
- Tournament roster scraper
- Decklist scraper
- Player model
- Deck model
- DeckCard model
- SQLite database
- Player table
- Deck table
- Deck card table
- Full tournament ETL pipeline
- QA test suite

### Performance

- Successfully scraped a tournament with:
  - 2,382 players
  - 2,382 decklists
  - 65,020 unique deck card rows

### Next Version

- Connection pooling using `requests.Session()`
- Parallel deck downloads
- Retry failed requests
- Tournament metadata
- Analytics module
- Historical tournament support