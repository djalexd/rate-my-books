"""Thin client for the Open Library search API (subjects, ratings, authors)."""

import logging
import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

import requests
from rapidfuzz import fuzz

from rate_my_books.text import normalize

SEARCH_URL = 'https://openlibrary.org/search.json'
FIELDS = 'title,author_name,subject,ratings_average,ratings_count'
_JUNK_SUBJECT_PREFIXES = (
    'nyt:',
    'open_syllabus',
    'translations',
    'accessible book',
    'protected daisy',
    'lending library',
    'in library',
    'large type',
    'reading level',
    'internet archive',
)


@dataclass(frozen=True)
class OpenLibraryBook:
    title: str
    author: str | None
    subjects: list[str]
    rating: float | None
    rating_count: int | None


def _clean_subjects(subjects: list[str]) -> list[str]:
    """Open Library subjects fuse several tags ('fiction, science fiction, general') and
    carry parenthetical notes; split them into plain lowercase tags."""
    cleaned = set()
    for subject in subjects:
        if subject.strip().lower().startswith(_JUNK_SUBJECT_PREFIXES):
            continue
        for part in re.sub(r'\([^)]*\)', '', subject).split(','):
            tag = part.strip().lower()
            if tag and tag != 'general':
                cleaned.add(tag)
    return sorted(cleaned)


def _search(params: dict[str, Any]) -> list[OpenLibraryBook]:
    try:
        r = requests.get(
            SEARCH_URL,
            params={**params, 'fields': FIELDS},
            headers={'User-Agent': 'rate-my-books (personal recommender)'},
            timeout=15,
        )
        r.raise_for_status()
        docs = r.json().get('docs', [])
    except (requests.RequestException, ValueError) as e:
        logging.error(f'Open Library request failed: {e}')
        return []
    return [
        OpenLibraryBook(
            title=d['title'],
            author=(d.get('author_name') or [None])[0],
            subjects=_clean_subjects(d.get('subject', [])),
            rating=d.get('ratings_average'),
            rating_count=d.get('ratings_count'),
        )
        for d in docs
        if d.get('title')
    ]


def _author_subjects(title: str, author: str, max_subjects: int = 8) -> OpenLibraryBook | None:
    """Stand-in for a book Open Library only knows under another title (typically a translation):
    the subjects most common across the author's works. Rating is left unknown."""
    wanted = normalize(author)
    works = [
        b
        for b in _search({'author': author, 'limit': 25})
        if b.author and fuzz.ratio(wanted, normalize(b.author)) >= 85
    ]
    counts = Counter(s for w in works for s in set(w.subjects))
    common = [s for s, c in counts.most_common() if c >= 2][:max_subjects]
    if not common:
        return None
    return OpenLibraryBook(title=title, author=author, subjects=common, rating=None, rating_count=None)


def find_book(title: str, author: str | None = None) -> OpenLibraryBook | None:
    """Best title match among the top hits, else the author's typical subjects; None if neither."""
    params: dict[str, Any] = {'title': title, 'limit': 5}
    if author:
        params['author'] = author
    wanted = normalize(title)
    scored = [(fuzz.ratio(wanted, normalize(b.title)), b) for b in _search(params)]
    scored = [(s, b) for s, b in scored if s >= 80]
    # among equally good title matches, prefer the one with the most subjects
    best = max(scored, key=lambda sb: (sb[0], len(sb[1].subjects)))[1] if scored else None
    if best is not None and best.subjects:
        return best
    fallback = _author_subjects(title, author) if author else None
    if best is not None and fallback is not None:
        return replace(best, subjects=fallback.subjects)
    return best or fallback


def books_for_subject(subject: str, limit: int = 30) -> list[OpenLibraryBook]:
    """Highest-rated English books for a subject."""
    return _search({'q': f'subject:"{subject}" language:eng', 'sort': 'rating', 'limit': limit})
