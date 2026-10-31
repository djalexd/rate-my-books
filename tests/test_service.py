import json
from datetime import date
from pathlib import Path

import pytest

from rate_my_books.catalog import Book, enrich, find_match
from rate_my_books.model import Mode
from rate_my_books.openlibrary import OpenLibraryBook
from rate_my_books.service import recommend_books

TODAY = date(2026, 10, 31)
Workspace = tuple[Path, Path, Path]  # (tmp dir, ratings file, vault)

SUBJECTS = {
    'dune': ['science fiction', 'space opera'],
    'hyperion': ['science fiction', 'space opera'],
    'emma': ['romance', 'classics'],
    'persuasion': ['romance', 'classics'],
    'neuromancer': ['science fiction', 'cyberpunk'],
    'ubik': ['science fiction', 'cyberpunk'],
    'ulysses': ['classics', 'modernism'],
}
# unrelated pairs so that no genre covers most of the library
for _topic in ('gardening', 'cooking', 'travel', 'sailing'):
    for _n in (1, 2):
        SUBJECTS[f'{_topic}{_n}'] = [_topic]


def fake_fetch_book(title: str, author: str | None = None) -> OpenLibraryBook | None:
    subjects = SUBJECTS.get(title.lower())
    return OpenLibraryBook(title, author, subjects, 4.0, 500) if subjects else None


def fake_fetch_subject(subject: str) -> list[OpenLibraryBook]:
    if subject == 'science fiction':
        return [
            OpenLibraryBook('Foundation', 'Asimov', ['science fiction', 'space opera'], 4.2, 9000),
            OpenLibraryBook('Dune', 'Herbert', ['science fiction', 'space opera'], 4.3, 9000),
        ]
    return []


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ratings = [
        {'name': f'{t} - Someone', 'path': f'/books/{t}.mobi', 'rating': 4.0, 'ratings_count': 800}
        for t in ['Dune', 'Emma', 'Neuromancer', 'Ubik', 'Ulysses'] + [k.title() for k in SUBJECTS if k[-1] in '12']
    ] + [{'name': 'Unknown - Nobody', 'path': '/books/u.mobi', 'rating': 0.0, 'ratings_count': 0}]
    ratings_path = tmp_path / 'ratings.json'
    ratings_path.write_text(json.dumps(ratings))
    vault = tmp_path / 'vault'
    vault.mkdir()
    (vault / 'h.md').write_text('---\ntitle: Hyperion\nrating: 5\nread_date: 2026-10-20\n---\n')
    (vault / 'p.md').write_text('---\ntitle: Persuasion\nrating: 2\nread_date: 2024-01-01\n---\n')
    return tmp_path, ratings_path, vault


def test_end_to_end_recommends_unread_library_and_outside(workspace: Workspace) -> None:
    tmp_path, ratings_path, vault = workspace
    result = recommend_books(
        Mode.NEXT,
        vault,
        ratings_path,
        tmp_path / 'cache.json',
        3,
        2,
        TODAY,
        fetch_book=fake_fetch_book,
        fetch_subject=fake_fetch_subject,
        pause=0,
    )
    library_titles = [p.book.title for p in result.library]
    assert set(library_titles[:3]) == {'Dune', 'Neuromancer', 'Ubik'}  # sci-fi first, not Emma/Ulysses
    assert 'Hyperion' not in library_titles
    assert [p.book.title for p in result.outside] == ['Foundation']  # Dune is already owned
    assert result.reads == 2 and result.library_without_subjects == 1


def test_empty_readlist_is_an_error(workspace: Workspace) -> None:
    tmp_path, ratings_path, _ = workspace
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(ValueError):
        recommend_books(
            Mode.NEXT,
            empty,
            ratings_path,
            tmp_path / 'c.json',
            5,
            2,
            TODAY,
            fetch_book=fake_fetch_book,
            fetch_subject=fake_fetch_subject,
            pause=0,
        )


def test_enrich_caches_hits_and_misses(tmp_path: Path) -> None:
    calls = []

    def fetch(title: str, author: str | None) -> OpenLibraryBook | None:
        calls.append(title)
        return fake_fetch_book(title, author)

    books = [Book('Dune', None), Book('Nothing Known', None)]
    cache = tmp_path / 'c' / 'cache.json'
    first = enrich(books, cache, fetch, pause=0)
    second = enrich(books, cache, fetch, pause=0)
    assert calls == ['Dune', 'Nothing Known']
    assert first == second
    assert first[0].subjects == ('science fiction', 'space opera') and first[1].subjects == ()


def test_find_match_tolerates_accents_but_not_different_books() -> None:
    library = [Book('Abaddón, Exterminatorul', None), Book('Al cincilea munte', None)]
    assert find_match('abaddon exterminatorul', library) is library[0]
    assert find_match('Al cincilea as', library) is None
