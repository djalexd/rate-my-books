"""Read-list kept as an Obsidian vault directory: one markdown note per book.

A note counts as a book when its YAML frontmatter has a `title`:

    ---
    title: The Aleph
    author: Jorge Luis Borges
    rating: 5               # 1-5, optional
    read_date: 2026-10-01   # optional
    ---
"""
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

import yaml

from recommender.text import normalize

_FRONTMATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*(?:\n|\Z)', re.DOTALL)


@dataclass(frozen=True)
class ReadEntry:
    title: str
    author: Optional[str]
    rating: Optional[float]
    read_date: Optional[date]
    path: Path


def _parse_note(path: Path) -> Optional[ReadEntry]:
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
    )


def load_readlist(directory: Path) -> List[ReadEntry]:
    entries = (_parse_note(p) for p in sorted(directory.rglob('*.md')))
    return [e for e in entries if e is not None]


def _same_book(entry: ReadEntry, title: str, author: Optional[str]) -> bool:
    if normalize(entry.title) != normalize(title):
        return False
    return not (author and entry.author) or normalize(author) == normalize(entry.author)


def add_entry(
    directory: Path,
    title: str,
    author: Optional[str] = None,
    rating: Optional[float] = None,
    read_date: Optional[date] = None,
) -> Path:
    """Write one note for the book; returns the existing note if the book is already listed."""
    for entry in load_readlist(directory):
        if _same_book(entry, title, author):
            return entry.path
    meta = {'title': title}
    if author:
        meta['author'] = author
    if rating is not None:
        meta['rating'] = rating
    meta['read_date'] = read_date or date.today()
    safe_name = re.sub(r'[\\/:*?"<>|]', '', f'{title} - {author}' if author else title).strip()
    path = directory / f'{safe_name}.md'
    path.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n', encoding='utf-8')
    return path
