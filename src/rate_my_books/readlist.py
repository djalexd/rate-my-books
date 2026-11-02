"""Read-list kept as an Obsidian vault directory: one markdown note per book.

A note counts as a book when its YAML frontmatter has a `title`:

    ---
    title: The Aleph
    author: Jorge Luis Borges
    rating: 5               # 1-5, optional
    read_date: 2026-10-01   # optional
    dropbox_path: /books/Aleph - Borges.mobi   # optional, where the file is (set by `import`)
    ---
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from rate_my_books.text import normalize

_FRONTMATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*(?:\n|\Z)', re.DOTALL)


@dataclass(frozen=True)
class ReadEntry:
    title: str
    author: str | None
    rating: float | None
    read_date: date | None
    path: Path
    dropbox_path: str | None = None


def _parse_note(path: Path) -> ReadEntry | None:
    match = _FRONTMATTER.match(path.read_text(encoding='utf-8'))
    if not match:
        return None
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict) or not meta.get('title'):
        return None
    rating = meta.get('rating')
    read_date = meta.get('read_date')
    if isinstance(read_date, str):
        try:
            read_date = date.fromisoformat(read_date)
        except ValueError:
            read_date = None
    return ReadEntry(
        title=str(meta['title']),
        author=str(meta['author']) if meta.get('author') else None,
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        read_date=read_date if isinstance(read_date, date) else None,
        path=path,
        dropbox_path=str(meta['dropbox_path']) if meta.get('dropbox_path') else None,
    )


def load_readlist(directory: Path) -> list[ReadEntry]:
    entries = (_parse_note(p) for p in sorted(directory.rglob('*.md')))
    return [e for e in entries if e is not None]


def _same_book(entry: ReadEntry, title: str, author: str | None) -> bool:
    if normalize(entry.title) != normalize(title):
        return False
    return not (author and entry.author) or normalize(author) == normalize(entry.author)


def find_entry(
    entries: Iterable[ReadEntry], title: str, author: str | None = None, dropbox_path: str | None = None
) -> ReadEntry | None:
    """The entry for this book: same Dropbox file, or same title (and author, when both are known)."""
    for entry in entries:
        if (dropbox_path and entry.dropbox_path == dropbox_path) or _same_book(entry, title, author):
            return entry
    return None


def add_entry(
    directory: Path,
    title: str,
    author: str | None = None,
    rating: float | None = None,
    read_date: date | None = None,
    dropbox_path: str | None = None,
    dated: bool = True,
) -> Path:
    """Write one note for the book; returns the existing note if the book is already listed.

    `dated=False` leaves out `read_date` instead of defaulting it to today.
    """
    existing = find_entry(load_readlist(directory), title, author, dropbox_path)
    if existing:
        return existing.path
    meta: dict[str, str | float | date] = {'title': title}
    if author:
        meta['author'] = author
    if rating is not None:
        meta['rating'] = rating
    if dated:
        meta['read_date'] = read_date or date.today()
    if dropbox_path:
        meta['dropbox_path'] = dropbox_path
    safe_name = re.sub(r'[\\/:*?"<>|]', '', f'{title} - {author}' if author else title).strip()
    path = directory / f'{safe_name}.md'
    path.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n', encoding='utf-8')
    return path
