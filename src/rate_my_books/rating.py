"""Rate the books in a Dropbox folder with their Goodreads average rating."""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import dropbox  # type: ignore[import-untyped,unused-ignore]

from rate_my_books.goodreads import get_best_rating
from rate_my_books.sources import list_dropbox_folder

BOOK_EXTENSION = '.mobi'


@dataclass(frozen=True)
class RatedBook:
    """`rating` 0 means not found on Goodreads, -1 means the request failed."""

    name: str
    path: str
    rating: float
    ratings_count: int


def rate_library(access_token: str, folder: str, limit: int | None = None, pause: float = 1.0) -> list[RatedBook]:
    client = dropbox.Dropbox(access_token)
    files = [e for e in list_dropbox_folder(client, folder) if e.name.endswith(BOOK_EXTENSION)]
    if limit and limit > 0:
        print(f'Limiting to {limit} out of {len(files)} books')
        files = files[:limit]
    else:
        print(f'Checking ratings for {len(files)} books')
    rated: list[RatedBook] = []
    for entry in files:
        name = entry.name.removesuffix(BOOK_EXTENSION)
        rating, count = get_best_rating(name)
        print(f'{name} - {rating}')
        rated.append(RatedBook(name, entry.path_display, rating, count))
        time.sleep(pause)
    return rated


def save_ratings(books: list[RatedBook], path: Path) -> None:
    path.write_text(json.dumps([asdict(b) for b in books]), encoding='utf-8')


def load_ratings(path: Path) -> list[RatedBook]:
    return [
        RatedBook(item['name'], item['path'], item['rating'], item['ratings_count'])
        for item in json.loads(path.read_text(encoding='utf-8'))
    ]
