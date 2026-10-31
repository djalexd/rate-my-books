"""Books: the Dropbox library (from ratings.json), read books, and outside candidates."""

import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from rate_my_books.openlibrary import OpenLibraryBook, find_book
from rate_my_books.rating import load_ratings
from rate_my_books.text import normalize, split_title_author

MATCH_THRESHOLD = 90


@dataclass(frozen=True)
class Book:
    title: str
    author: str | None
    rating: float | None = None
    rating_count: int | None = None
    subjects: tuple[str, ...] = ()
    source: str = 'library'

    @property
    def key(self) -> str:
        return normalize(self.title)


def load_library(ratings_path: Path) -> list[Book]:
    """Books from the `rate` command's output; a rating <= 0 means "unknown"."""
    books = []
    for item in load_ratings(ratings_path):
        title, author = split_title_author(item.name)
        rated = item.rating > 0
        books.append(
            Book(
                title=title,
                author=author,
                rating=item.rating if rated else None,
                rating_count=item.ratings_count if rated else None,
            )
        )
    return books


def find_match(title: str, books: Sequence[Book], threshold: int = MATCH_THRESHOLD) -> Book | None:
    wanted = normalize(title)
    best = max(books, key=lambda b: fuzz.ratio(wanted, b.key), default=None)
    if best is not None and fuzz.ratio(wanted, best.key) >= threshold:
        return best
    return None


def _from_open_library(book: Book, found: OpenLibraryBook) -> Book:
    return replace(
        book,
        author=book.author or found.author,
        rating=book.rating if book.rating is not None else found.rating,
        rating_count=book.rating_count if book.rating_count is not None else found.rating_count,
        subjects=tuple(found.subjects),
    )


def enrich(
    books: Sequence[Book],
    cache_path: Path,
    fetch: Callable[[str, str | None], OpenLibraryBook | None] = find_book,
    pause: float = 0.2,
) -> list[Book]:
    """Fill in subjects (and missing author/rating) from Open Library.

    Lookups, including misses, are cached on disk so a book is only fetched once.
    """
    cache: dict[str, dict[str, Any] | None] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    enriched = []
    fetched = 0
    for book in books:
        cache_key = f'{book.key}|{normalize(book.author or "")}'
        if cache_key not in cache:
            found = fetch(book.title, book.author)
            cache[cache_key] = (
                None
                if found is None
                else {
                    'title': found.title,
                    'author': found.author,
                    'subjects': found.subjects,
                    'rating': found.rating,
                    'rating_count': found.rating_count,
                }
            )
            fetched += 1
            if fetched % 25 == 0:
                print(f'  enriched {fetched} new books...', file=sys.stderr)
                cache_path.write_text(json.dumps(cache), encoding='utf-8')
            time.sleep(pause)
        hit = cache[cache_key]
        enriched.append(_from_open_library(book, OpenLibraryBook(**hit)) if hit else book)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache), encoding='utf-8')
    return enriched
