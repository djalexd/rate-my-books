"""Glue: read-list + library + outside candidates -> ranked picks."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, List, Optional

from recommender.catalog import Book, enrich, find_match, load_library
from recommender.features import FeatureSpace
from recommender.model import Params, Pick, Read, build_profile, recommend, top_subjects
from recommender.openlibrary import OpenLibraryBook, books_for_subject, find_book
from recommender.readlist import load_readlist

OUTSIDE_SUBJECTS = 5


@dataclass(frozen=True)
class Recommendations:
    library: List[Pick]
    outside: List[Pick]
    reads: int
    library_size: int
    library_without_subjects: int


def _outside_candidates(
    queries: List[str],
    known: List[Book],
    fetch_subject: Callable[[str], List[OpenLibraryBook]],
) -> List[Book]:
    candidates: dict = {}
    for subject in queries:
        for found in fetch_subject(subject):
            book = Book(found.title, found.author, found.rating, found.rating_count,
                        tuple(found.subjects), source='outside')
            candidates.setdefault(book.key, book)
    return [b for b in candidates.values() if find_match(b.title, known) is None]


def recommend_books(
    mode: str,
    readlist_dir: Path,
    ratings_path: Path,
    cache_path: Path,
    library_picks: int,
    outside_picks: int,
    today: date,
    params: Params = Params(),
    fetch_book: Callable[[str, Optional[str]], Optional[OpenLibraryBook]] = find_book,
    fetch_subject: Callable[[str], List[OpenLibraryBook]] = books_for_subject,
    pause: float = 0.2,
) -> Recommendations:
    entries = load_readlist(readlist_dir)
    if not entries:
        raise ValueError(f'No books with a `title` in the frontmatter found under {readlist_dir}')

    library = load_library(ratings_path)
    enriched = enrich(library + [Book(e.title, e.author, source='read') for e in entries],
                      cache_path, fetch_book, pause)
    library, read_books = enriched[:len(library)], enriched[len(library):]
    reads = [Read(b, e.rating, e.read_date) for b, e in zip(read_books, entries)]

    unread = [b for b in library if find_match(b.title, read_books) is None]

    # outside candidates: top subjects of the profile in this mode, minus anything read or owned
    seed_space = FeatureSpace(library + read_books)
    profile = build_profile(reads, seed_space, mode, today, params)
    outside = _outside_candidates(
        top_subjects(profile, seed_space, OUTSIDE_SUBJECTS), read_books + library, fetch_subject,
    ) if outside_picks else []

    space = FeatureSpace(library + read_books + outside)
    return Recommendations(
        library=recommend(mode, reads, unread, space, library_picks, today, params),
        outside=recommend(mode, reads, outside, space, outside_picks, today, params) if outside else [],
        reads=len(reads),
        library_size=len(library),
        library_without_subjects=sum(1 for b in library if not b.subjects),
    )
