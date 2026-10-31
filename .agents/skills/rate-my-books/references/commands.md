# Command reference

Matches `uv run rate-my-books <command> --help`.

## rate
`--path PATH` (required, Dropbox folder) · `--ratings RATINGS` (default `ratings.json`) · `--limit LIMIT` (only rate
this many books). In `ratings.json`, `rating` 0 = not found, -1 = request failed.

## view
`--ratings RATINGS` (default `ratings.json`).

## taste / next
- `--readlist-dir READLIST_DIR` (or env `READLIST_DIR`)
- `--ratings RATINGS` (default `ratings.json`, output of `rate`)
- `--cache CACHE` (default `.cache/openlibrary.json`)
- `--library-picks N` (default 5) · `--outside-picks N` (default 2)
- `--half-life DAYS`: days after which a read counts half as much (`next` only)

The summary line reports books read, library size and how many library books have no subject data (those fall back to
the author's most common subjects).

## add
`--title TITLE` (required) · `--author AUTHOR` · `--rating RATING` (1-5) · `--date YYYY-MM-DD` (default today) ·
`--readlist-dir READLIST_DIR`. Does nothing if the book is already listed. Notes are markdown with frontmatter
`title`, `author`, `rating`, `read_date`.
