\# Pokemon Scraper



A Python application for downloading Pokémon TCG tournament data from RK9, storing it in SQLite, and enabling large-scale analytics.



\## Features



\- Download tournament rosters from RK9

\- Download every submitted decklist

\- Parse decklists into structured Python objects

\- Store tournament data in SQLite

\- Built with a modular architecture for future analytics and visualization



\## Project Structure



```

pokemon\_scraper/

│

├── src/

│   ├── config.py

│   ├── database.py

│   ├── deck.py

│   ├── models.py

│   ├── roster.py

│   ├── scraper.py

│   └── utils.py

│

├── tests/

│

├── raw/

├── exports/

├── notebooks/

│

├── run.py

├── README.md

└── CHANGELOG.md

```



\## Current Database Schema



\### players



| Column | Type |

|--------|------|

| player\_key | TEXT |

| tournament\_id | TEXT |

| first\_name | TEXT |

| last\_name | TEXT |

| country | TEXT |

| division | TEXT |

| standing | INTEGER |



\### decks



| Column | Type |

|--------|------|

| player\_key | TEXT |

| deck\_url | TEXT |



\### deck\_cards



| Column | Type |

|--------|------|

| id | INTEGER |

| player\_key | TEXT |

| quantity | INTEGER |

| card\_name | TEXT |

| card\_type | TEXT |

| set\_code | TEXT |

| card\_number | TEXT |



\## Current Status



Version: \*\*0.1.0\*\*



Completed:



\- ✅ Tournament roster parser

\- ✅ Deck parser

\- ✅ Full tournament scraper

\- ✅ SQLite database

\- ✅ End-to-end ETL pipeline



\## Planned Features



\- Faster scraping using concurrent requests

\- Tournament metadata

\- Historical tournament database

\- Card analytics

\- Deck analytics

\- Meta trend analysis

\- Interactive dashboard



\## Example Workflow



```python

players, decks = parse\_roster(tournament\_id)



cards = parse\_all\_decks(players, decks)



create\_database()



insert\_players(players)

insert\_decks(decks)

insert\_cards(cards)

```



\## License



Personal analytics project.

