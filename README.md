# rate-my-books
Rates the books in a Dropbox folder (via Goodreads) and recommends what to read next, based on the
books you have read.

## setup
Uses [uv](https://docs.astral.sh/uv/) and Python 3.12+ (`uv python install 3.12` if you do not have it).

```
uv sync
uv run rate-my-books --help
```

You also need a Dropbox app access token for the `rate` command, and a read-list directory (below).

## 1. rate the library
`ACCESS_TOKEN=<dropbox token> uv run rate-my-books rate --path <path_in_dropbox> --ratings ratings.json`

Goes over every `.mobi` file in the Dropbox folder, looks up its Goodreads average rating and rating
count, and stores them in `ratings.json` (`rating` 0 = not found, -1 = request failed).
`uv run rate-my-books view --ratings ratings.json` prints them ranked.

## 2. keep a read-list
One markdown note per book, anywhere under an Obsidian directory. A note is a book when its frontmatter has a `title`:

```
---
title: The Aleph
author: Jorge Luis Borges
rating: 5               # 1-5, optional
read_date: 2026-10-01   # optional, used by `next`
---
```

Add a book from the command line (does nothing if it is already listed):
`uv run rate-my-books add --title "The Aleph" --author "Jorge Luis Borges" --rating 5`

## 3. get recommendations
```
export READLIST_DIR=~/path/to/vault/books
uv run rate-my-books taste   # best fits for your overall taste
uv run rate-my-books next    # builds on what you read recently
```
Each prints 5 picks from your library (books you have not read) and 2 from outside it, with the reasons.
`--library-picks`, `--outside-picks` and `--half-life` (days until a read counts half as much in `next`) adjust it.
`--ratings` and `--cache` default to `ratings.json` and `.cache/openlibrary.json` in the working directory.

* Subjects come from [Open Library](https://openlibrary.org/dev/docs/api/search) and are cached
  (the first run over a large library takes a while). When Open Library does not know a title
  (typically translations) the author's most common subjects are used instead.
* `taste` weights every read by how much you liked it (3 stars is neutral, below pushes away).
  `next` also decays older reads and prefers *adjacent* books: close to your recent reads but adding subjects
  they do not have. The weights live in `Params` in `src/rate_my_books/model.py`.

## development
```
uv run pytest
uv run mypy            # strict, covers src and tests
uv run ruff check . && uv run ruff format --check .
```
Code is in `src/rate_my_books/`, tests in `tests/`.

## other
`indexing/` is a Kotlin (Gradle) module that indexes books into Elasticsearch; `docker-compose.yaml`
starts Elasticsearch and Kibana for it.
