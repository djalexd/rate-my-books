"""Rank rated books, favouring well-rated ones that many people have rated."""

import math

from rate_my_books.rating import RatedBook


def adjusted_rating(book: RatedBook) -> float:
    if book.ratings_count > 0:
        return 0.7 * book.rating + 0.3 * math.log10(book.ratings_count)
    return book.rating


def ranked(books: list[RatedBook]) -> list[RatedBook]:
    """Books with a rating, best first."""
    return sorted((b for b in books if b.rating > 0.0), key=adjusted_rating, reverse=True)
