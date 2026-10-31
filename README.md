# rate-my-books
Rates the books in a Dropbox folder (via Goodreads) and recommends what to read next, based on the
books you have read.

## setup
* Create a Dropbox app to obtain an access token (only needed for `rate.py`)
* `pip install -r requirements.txt`
* Keep your read-list in an Obsidian directory (see below) and point `READLIST_DIR` at it

## 1. rate the library
`ACCESS_TOKEN=<dropbox token> python rate.py --path <path_in_dropbox> --ratings_path ratings.json`

Goes over every `.mobi` file in the Dropbox folder, looks up its Goodreads average rating and rating
count, and stores them in `ratings.json` (`rating` 0 = not found, -1 = request failed).
`viewer.py --ratings_path ratings.json` prints them ranked.

## 2. keep a read-list
One markdown note per book, anywhere under the directory. A note is a book when its frontmatter has a `title`:

```
---
title: The Aleph
author: Jorge Luis Borges
rating: 5               # 1-5, optional
read_date: 2026-10-01   # optional, used by `next`
---
```

Add a book from the command line (does nothing if it is already listed):
`python recommend.py add --title "The Aleph" --author "Jorge Luis Borges" --rating 5`

## 3. get recommendations
```
export READLIST_DIR=~/path/to/vault/books
python recommend.py taste   # best fits for your overall taste
python recommend.py next    # builds on what you read recently
```
Each prints 5 picks from your library (books you have not read) and 2 from outside it, with the reasons.
`--library-picks`, `--outside-picks` and `--half-life` (days until a read counts half as much in `next`) adjust it.

* Subjects come from [Open Library](https://openlibrary.org/dev/docs/api/search) and are cached in
  `.cache/openlibrary.json` (the first run over a large library takes a few minutes). When Open Library
  does not know a title (typically translations) the author's most common subjects are used instead.
* `taste` weights every read by how much you liked it (3 stars is neutral, below pushes away).
  `next` also decays older reads and prefers *adjacent* books: close to your recent reads but adding subjects
  they do not have. The weights live in `Params` in `recommender/model.py`.

## tests
`python -m pytest`

## other
`indexing/` is a Kotlin (Gradle) module that indexes books into Elasticsearch; `docker-compose.yaml`
starts Elasticsearch and Kibana for it.
