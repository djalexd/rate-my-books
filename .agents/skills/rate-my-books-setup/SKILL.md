---
name: rate-my-books-setup
description: One-time setup of the rate-my-books project. Use when the user wants to install, set up, or get rate-my-books running, or when `uv run rate-my-books` fails because the environment is missing.
---

# rate-my-books setup

1. Needs [uv](https://docs.astral.sh/uv/) and Python 3.12+. If Python is missing: `uv python install 3.12`.
2. Install and smoke-test:
   ```
   uv sync
   uv run rate-my-books --help
   ```
3. Confirm the install with the dev checks:
   ```
   uv run pytest && uv run mypy && uv run ruff check . && uv run ruff format --check .
   ```
4. Tell the user what the commands need (do not set these for them):
   - `READLIST_DIR`: the Obsidian directory with one note per read book. Ask the user for the path; it is not known.
     `export READLIST_DIR=~/path/to/vault/books`
   - `ACCESS_TOKEN`: a Dropbox app access token, only for `rate`. Never ask for it or print it; the user exports it.
5. Next step: the `rate-my-books` skill (`rate` first, then `taste`/`next`).
