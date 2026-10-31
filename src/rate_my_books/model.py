"""Profiles and ranking for the two modes.

taste: long-term profile from every read book, weighted by how much you liked it.
next:  the same weights decayed by age, and a score that favours *adjacent* books,
       i.e. close to your recent reads but contributing some subjects they don't have.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np

from rate_my_books.catalog import Book
from rate_my_books.features import SUBJECT_PREFIX, FeatureSpace, label, mean_rating, quality, tokens


class Mode(StrEnum):
    TASTE = 'taste'
    NEXT = 'next'


@dataclass(frozen=True)
class Read:
    book: Book
    rating: float | None = None
    read_date: date | None = None


@dataclass(frozen=True)
class Params:
    half_life_days: float = 90.0
    undated_weight: float = 0.25  # decay applied to reads with no date in `next` mode
    unrated_affinity: float = 0.25  # how much an unrated read counts
    taste_sim: float = 0.75
    taste_quality: float = 0.25
    next_sim: float = 0.45
    next_novelty: float = 0.40  # only earned by books that already overlap with recent reads
    next_quality: float = 0.15
    recent_threshold: float = 0.1  # a subject is "recent" above this share of the profile peak
    mmr_lambda: float = 0.3  # penalty for resembling an already chosen pick


DEFAULT_PARAMS = Params()


@dataclass(frozen=True)
class Pick:
    book: Book
    score: float
    reasons: list[str]


def affinity(rating: float | None, params: Params) -> float:
    """1-5 star rating -> [-1, 1]; 3 stars is neutral, below pushes the profile away."""
    return params.unrated_affinity if rating is None else (rating - 3.0) / 2.0


def decay(read_date: date | None, today: date, params: Params) -> float:
    if read_date is None:
        return params.undated_weight
    age = max((today - read_date).days, 0)
    return float(0.5 ** (age / params.half_life_days))


def build_profile(reads: Sequence[Read], space: FeatureSpace, mode: Mode, today: date, params: Params) -> np.ndarray:
    profile = np.zeros(len(space.vocab))
    for r in reads:
        weight = affinity(r.rating, params)
        if mode == Mode.NEXT:
            weight *= decay(r.read_date, today, params)
        profile += weight * space.vectorize(r.book)
    norm = np.linalg.norm(profile)
    return profile / norm if norm else profile


def _cosine(profile: np.ndarray, vec: np.ndarray) -> float:
    norm = np.linalg.norm(vec)
    return float(profile @ vec / norm) if norm else 0.0


def _novelty(book: Book, recent: set[str]) -> float:
    """Share of the book's subjects that your recent reads don't have, peaking at one half."""
    subjects = [t for t in tokens(book) if t.startswith(SUBJECT_PREFIX)]
    if not subjects:
        return 0.0
    fresh = sum(1 for t in subjects if t not in recent) / len(subjects)
    return 4 * fresh * (1 - fresh)


def top_subjects(profile: np.ndarray, space: FeatureSpace, n: int) -> list[str]:
    order = np.argsort(-profile)[:n]
    return [label(space.names[i]) for i in order if profile[i] > 0 and space.names[i].startswith(SUBJECT_PREFIX)]


def recommend(
    mode: Mode,
    reads: Sequence[Read],
    candidates: Sequence[Book],
    space: FeatureSpace,
    k: int,
    today: date,
    params: Params = DEFAULT_PARAMS,
) -> list[Pick]:
    if mode not in Mode:
        raise ValueError(f'unknown mode {mode!r}')
    profile = build_profile(reads, space, mode, today, params)
    prior = mean_rating([r.book for r in reads] + list(candidates))
    peak = profile.max() if profile.size else 0.0
    recent = {space.names[i] for i in np.nonzero(profile > params.recent_threshold * peak)[0]} if peak > 0 else set()

    vectors = [space.vectorize(b) for b in candidates]
    scores = []
    for book, vec in zip(candidates, vectors, strict=False):
        sim, q = _cosine(profile, vec), quality(book, prior)
        if mode == Mode.TASTE:
            scores.append(params.taste_sim * sim + params.taste_quality * q)
        else:
            scores.append(
                params.next_sim * sim + params.next_novelty * _novelty(book, recent) + params.next_quality * q
            )

    picks: list[Pick] = []
    chosen: list[int] = []
    remaining = set(range(len(candidates)))
    while remaining and len(picks) < k:

        def adjusted(i: int) -> float:
            # a book with no known subjects gets no diversity credit for being "different"
            if chosen and not vectors[i].any():
                return scores[i] - params.mmr_lambda
            overlap = max((_cosine(vectors[j], vectors[i]) for j in chosen), default=0.0)
            return scores[i] - params.mmr_lambda * overlap

        best = max(remaining, key=adjusted)
        remaining.discard(best)
        chosen.append(best)
        picks.append(
            Pick(
                candidates[best],
                scores[best],
                _reasons(mode, candidates[best], vectors[best], reads, space, profile, recent),
            )
        )
    return picks


def _reasons(
    mode: Mode,
    book: Book,
    vec: np.ndarray,
    reads: Sequence[Read],
    space: FeatureSpace,
    profile: np.ndarray,
    recent: set[str],
) -> list[str]:
    reasons = []
    shared = sorted(
        (i for i in np.nonzero((vec > 0) & (profile > 0))[0]),
        key=lambda i: -profile[i] * vec[i],
    )[:3]
    if shared:
        reasons.append('matches ' + ', '.join(label(space.names[i]) for i in shared))
    if mode == Mode.NEXT:
        fresh = [
            label(t) for t in tokens(book) if t.startswith(SUBJECT_PREFIX) and t not in recent and t in space.vocab
        ][:2]
        if fresh:
            reasons.append('adds ' + ', '.join(fresh))
    liked = [r for r in reads if (r.rating or 0) >= 4]
    if liked and vec.any():
        nearest = max(liked, key=lambda r: _cosine(space.vectorize(r.book), vec))
        if _cosine(space.vectorize(nearest.book), vec) > 0:
            reasons.append(f'like "{nearest.book.title}"')
    return reasons
