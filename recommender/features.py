"""Sparse-ish book vectors: IDF-weighted subjects and authors, plus a quality score."""
import math
from collections import Counter
from typing import Dict, List, Optional, Sequence

import numpy as np

from recommender.catalog import Book
from recommender.text import normalize

SUBJECT_PREFIX = 's:'
AUTHOR_PREFIX = 'a:'


def tokens(book: Book) -> List[str]:
    found = [SUBJECT_PREFIX + s for s in book.subjects]
    if book.author:
        found.append(AUTHOR_PREFIX + normalize(book.author))
    return found


def label(token: str) -> str:
    return token.split(':', 1)[1]


class FeatureSpace:
    """Vocabulary built from a corpus; tokens seen in fewer than `min_df` books or in more
    than `max_df_ratio` of them carry no signal and are dropped."""

    def __init__(
        self,
        corpus: Sequence[Book],
        min_df: int = 2,
        max_df_ratio: float = 0.5,
        author_weight: float = 0.5,
    ) -> None:
        df = Counter(t for book in corpus for t in set(tokens(book)))
        n = len(corpus)
        kept = sorted(t for t, c in df.items() if c >= min_df and c / n <= max_df_ratio)
        self.vocab: Dict[str, int] = {t: i for i, t in enumerate(kept)}
        self.names: List[str] = kept
        self.weights = np.array([
            math.log(n / df[t]) * (author_weight if t.startswith(AUTHOR_PREFIX) else 1.0)
            for t in kept
        ])

    def vectorize(self, book: Book) -> np.ndarray:
        vec = np.zeros(len(self.vocab))
        for t in tokens(book):
            i = self.vocab.get(t)
            if i is not None:
                vec[i] = self.weights[i]
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec


def quality(book: Book, prior_mean: float, prior_weight: float = 200.0) -> float:
    """Bayesian-shrunk 0-5 rating mapped to [0, 1]: few ratings pull toward the prior."""
    n = book.rating_count or 0
    r = book.rating if book.rating is not None else prior_mean
    shrunk = (n * r + prior_weight * prior_mean) / (n + prior_weight)
    return float(min(1.0, max(0.0, (shrunk - 3.0) / 2.0)))


def mean_rating(books: Sequence[Book], default: float = 3.8) -> float:
    rated: List[Optional[float]] = [b.rating for b in books if b.rating]
    return float(sum(r for r in rated if r) / len(rated)) if rated else default
