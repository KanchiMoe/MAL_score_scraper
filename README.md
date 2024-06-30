# MAL Score Scraper

> [!CAUTION]
> **This repo is no longer being updated.**
>
> It works for what I intended it to do, but it's messy and set up for my own use, but it could always be improved.
>
> The structure of the database tables also changed in `ab_quick.py` and `main.py` has not been updated to reflect those changes.


This is a python script that scrapes the stats page for an anime on MAL, and stores the value in a database. 

## Required environment variables

Currently used as `.env` files.

```
PGHOST=
PGPORT=
PGDATABASE=
LOG_LEVEL=
LOG_FORMAT=
```

If using `ab_quick`, this needs to be in the root of the project. If using `main`, this needs to be in `src/`.


## Repo name change

The name of this repo changed from `MAL_score_scraper` to `MAL_score_scraper_py` on `30 June 2024`.






