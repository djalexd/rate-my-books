"""Turn the book files of a Dropbox folder into read-list notes.

File names are normalized into a title and an author, and the note keeps the Dropbox location:

    Dune - Frank Herbert.mobi              -> Dune / Frank Herbert
    Abatia 2 - Blestemul Abatiei - Dan Dobos.mobi -> Abatia 2 - Blestemul Abatiei / Dan Dobos
    Inferno_Brown_Dan.pdf                  -> Inferno / Dan Brown   (Title_Surname_Name)
"""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import dropbox  # type: ignore[import-untyped,unused-ignore]

from rate_my_books.readlist import ReadEntry, add_entry, find_entry, load_readlist
from rate_my_books.sources import list_dropbox_folder
from rate_my_books.text import split_title_author

BOOK_EXTENSIONS = frozenset({'.mobi', '.epub', '.azw3', '.pdf'})
_UNDERSCORE_NAME = re.compile(r'^(?P<title>.+?)_(?P<surname>[^_]+)_(?P<name>[^_]+)$')


@dataclass(frozen=True)
class ImportedBook:
    title: str
    author: str | None
    dropbox_path: str


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def parse_book_file(dropbox_path: str) -> ImportedBook | None:
    """The book a Dropbox file holds, or None when it is not a book file."""
    path = PurePosixPath(dropbox_path)
    if path.suffix.lower() not in BOOK_EXTENSIONS:
        return None
    stem = path.stem
    match = _UNDERSCORE_NAME.match(stem) if ' - ' not in stem else None
    author: str | None
    if match:
        title, author = match['title'], f'{match["name"]} {match["surname"]}'
    else:
        title, author = split_title_author(stem)
    title = _clean(title.replace('_', ' '))
    if not title:
        return None
    return ImportedBook(title, _clean(author) if author else None, dropbox_path)


def list_books(access_token: str, folder: str) -> list[ImportedBook]:
    client = dropbox.Dropbox(access_token)
    parsed = (parse_book_file(e.path_display) for e in list_dropbox_folder(client, folder))
    return [book for book in parsed if book is not None]


def import_books(directory: Path, books: list[ImportedBook], dry_run: bool = False) -> list[tuple[ImportedBook, bool]]:
    """Write a note per book that is not listed yet; returns each book with whether it was new.

    Notes get no rating and no read date: Dropbox knows neither. With `dry_run` nothing is written.
    """
    known: list[ReadEntry] = load_readlist(directory)
    results: list[tuple[ImportedBook, bool]] = []
    for book in books:
        is_new = find_entry(known, book.title, book.author, book.dropbox_path) is None
        if is_new:
            note = directory / f'{book.title}.md'
            if not dry_run:
                note = add_entry(directory, book.title, book.author, dropbox_path=book.dropbox_path, dated=False)
            known.append(ReadEntry(book.title, book.author, None, None, note, book.dropbox_path))
        results.append((book, is_new))
    return results
