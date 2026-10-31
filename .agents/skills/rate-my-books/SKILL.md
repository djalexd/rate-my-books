---
name: rate-my-books
description: Run the rate-my-books CLI. Use when the user asks what to read next, wants book recommendations, wants their Dropbox library rated or ranked, or wants to record a book they finished.
---

# rate-my-books

Run everything with `uv run rate-my-books <command>` from the repo root. If the environment is missing, use the
`rate-my-books-setup` skill.

| Command | Use it to | Needs |
|---|---|---|
| `rate --path <dropbox_path>` | Look up Goodreads ratings for the library, store them in `ratings.json` | `ACCESS_TOKEN`; network, slow |
| `view` | Print the rated library, best first | `ratings.json` |
| `taste` | Recommend by overall taste (long-term) | `READLIST_DIR`, `ratings.json` |
| `next` | Recommend based on recent reads (older reads decay, prefers adjacent books) | `READLIST_DIR`, `ratings.json` |
| `add --title ...` | Record a finished book as a note in the read-list | `READLIST_DIR` |

## Flow
`rate` (once, or when the library changes) → `view` / `taste` / `next`. `ratings.json` is generated and not
committed, so if it is missing run `rate` first.

## Rules
- `rate` and `add` have side effects (Dropbox and Goodreads requests; a new note in the user's vault). Confirm before
  running them, and never ask for or print `ACCESS_TOKEN`.
- If `READLIST_DIR` is unset, ask the user for the path; do not guess.
- The first `taste`/`next` run over a large library is slow (Open Library lookups); later runs use `.cache/`.
- Pick `taste` for "what suits me", `next` for "what should I read after what I just finished".

Each recommend command prints 5 picks from the library (unread) and 2 from outside, with reasons. Flags:
[references/commands.md](references/commands.md).
