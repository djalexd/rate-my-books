# AGENTS.md

rate-my-books rates the books in a Dropbox folder (via Goodreads) and recommends what to read next from an
Obsidian read-list. See `README.md` for usage.

## Layout
- `src/rate_my_books/`: the Python package; `cli.py` is the single `rate-my-books` entry point.
- `tests/`: pytest tests.
- `indexing/`: separate Kotlin (Gradle) module that indexes books into Elasticsearch. Do not touch it unless asked.

## Commands
```
uv sync
uv run pytest
uv run mypy                                   # strict, covers src and tests
uv run ruff check . && uv run ruff format --check .
```
Run all of them before finishing a change.

## Conventions
- Python 3.12+, uv, `src/` layout. Full type hints (mypy strict).
- ruff: single quotes, line length 120.
- New code goes inside the package; tests go in `tests/`.
- Recommendation weights live in `Params` in `src/rate_my_books/model.py`.

## Guardrails
- Flink and Kafka were removed on purpose; do not reintroduce them.
- Do not commit `ratings.json` or `.cache/` (generated).
- Never ask for, print or store the Dropbox token (`ACCESS_TOKEN`); the user exports it or puts it in `.env`.
  Never `cat`/read `.env` or print a value resolved from 1Password (`op://`).
- `rate` calls Dropbox and Goodreads, and `add` writes a note into the user's Obsidian vault
  (`READLIST_DIR`). Confirm with the user before running either.

## Skills
- `rate-my-books-setup`: first-time setup.
- `rate-my-books`: run the commands and read the results.

Skills live in `.agents/skills/` (`.claude/skills` is a symlink to it).
