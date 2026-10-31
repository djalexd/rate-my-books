import pytest

from rate_my_books import openlibrary
from rate_my_books.openlibrary import OpenLibraryBook, find_book


def ol(title: str, author: str, subjects: list[str]) -> OpenLibraryBook:
    return OpenLibraryBook(title, author, subjects, 4.0, 100)


def test_clean_subjects_splits_fused_tags_and_drops_junk() -> None:
    cleaned = openlibrary._clean_subjects(
        [
            'Fiction, Science Fiction, General',
            'Fiction (fictional works by one author)',
            'nyt:combined-print-and-e-book-fiction=2020-01-01',
            'Open_syllabus_project',
        ]
    )
    assert cleaned == ['fiction', 'science fiction']


def test_find_book_prefers_close_title_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        openlibrary,
        '_search',
        lambda params: [
            ol('Something Else Entirely', 'A', ['x']),
            ol('Concert din muzică de Bach', 'A', ['romanian literature']),
        ],
    )
    found = find_book('Concert de muzica de Bach', 'A')
    assert found is not None
    assert found.subjects == ['romanian literature']


def test_find_book_falls_back_to_authors_common_subjects(monkeypatch: pytest.MonkeyPatch) -> None:
    works = [
        ol('Work 1', 'Philip K. Dick', ['science fiction', 'dystopias']),
        ol('Work 2', 'Philip K. Dick', ['science fiction', 'time travel']),
        ol('Other Person', 'Someone Else', ['cooking', 'cooking']),
    ]
    monkeypatch.setattr(
        openlibrary, '_search', lambda params: works if 'author' in params and 'title' not in params else []
    )
    found = find_book('Omul din Castelul Inalt', 'Philip K. Dick')
    assert found is not None
    assert found.title == 'Omul din Castelul Inalt'
    assert found.subjects == ['science fiction']  # only subjects shared by at least two of the author's works
    assert found.rating is None


def test_find_book_without_author_and_no_match_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openlibrary, '_search', lambda params: [])
    assert find_book('Nothing') is None
