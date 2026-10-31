from datetime import date, timedelta

from rate_my_books.catalog import Book
from rate_my_books.features import FeatureSpace, quality
from rate_my_books.model import Mode, Params, Read, decay, recommend

TODAY = date(2026, 10, 31)


def book(
    title: str,
    subjects: list[str],
    author: str | None = None,
    rating: float = 4.0,
    count: int = 1000,
    source: str = 'library',
) -> Book:
    return Book(title, author, rating, count, tuple(subjects), source)


def space_for(*groups: list[Book]) -> FeatureSpace:
    # unrelated filler keeps IDF positive for subjects that appear in every test book
    filler = [book(f'filler{i}', [f'filler{i}']) for i in range(6)]
    return FeatureSpace([b for g in groups for b in g] + filler, min_df=1, max_df_ratio=1.0)


def test_decay_halves_each_half_life() -> None:
    p = Params(half_life_days=90)
    assert decay(TODAY, TODAY, p) == 1.0
    assert abs(decay(TODAY - timedelta(days=90), TODAY, p) - 0.5) < 1e-9
    assert decay(None, TODAY, p) == p.undated_weight


def test_quality_shrinks_toward_prior_with_few_ratings() -> None:
    popular = quality(book('a', [], rating=4.5, count=100000), prior_mean=3.8)
    obscure = quality(book('b', [], rating=4.5, count=3), prior_mean=3.8)
    assert popular > obscure


def test_taste_ranks_liked_subjects_first_and_disliked_last() -> None:
    reads = [
        Read(book('r1', ['scifi', 'space']), rating=5),
        Read(book('r2', ['scifi', 'robots']), rating=5),
        Read(book('r3', ['romance']), rating=1),
    ]
    scifi, romance, other = book('c1', ['scifi', 'robots']), book('c2', ['romance']), book('c3', ['history'])
    space = space_for([r.book for r in reads], [scifi, romance, other])
    picks = recommend(Mode.TASTE, reads, [romance, other, scifi], space, 3, TODAY)
    assert [p.book.title for p in picks][0] == 'c1'
    assert [p.book.title for p in picks][-1] == 'c2'
    assert any('scifi' in reason for reason in picks[0].reasons)


def test_next_follows_recent_reads_not_old_favourites() -> None:
    reads = [
        Read(book('old', ['fantasy', 'dragons']), rating=5, read_date=TODAY - timedelta(days=700)),
        Read(book('new', ['history', 'rome']), rating=5, read_date=TODAY - timedelta(days=5)),
    ]
    fantasy, history = book('fantasy-pick', ['fantasy', 'dragons']), book('history-pick', ['history', 'rome'])
    space = space_for([r.book for r in reads], [fantasy, history])
    nxt = recommend(Mode.NEXT, reads, [fantasy, history], space, 1, TODAY)
    assert nxt[0].book.title == 'history-pick'
    taste = recommend(Mode.TASTE, reads, [fantasy, history], space, 2, TODAY)
    assert abs(taste[0].score - taste[1].score) < 1e-9  # equally liked overall


def test_next_prefers_adjacent_over_identical() -> None:
    reads = [Read(book('r', ['latin america', 'magical realism', 'novel']), rating=5, read_date=TODAY)]
    same = book('same', ['latin america', 'magical realism', 'novel'])
    adjacent = book('adjacent', ['latin america', 'magical realism', 'essays', 'politics'])
    space = space_for([reads[0].book], [same, adjacent])
    picks = recommend(Mode.NEXT, reads, [same, adjacent], space, 2, TODAY)
    assert picks[0].book.title == 'adjacent'
    assert any(r.startswith('adds') for r in picks[0].reasons)


def test_mmr_spreads_picks_across_clusters() -> None:
    reads = [Read(book('r', ['a', 'b', 'c']), rating=5)]
    twin1, twin2 = book('twin1', ['a', 'b', 'c']), book('twin2', ['a', 'b', 'c'])
    other = book('other', ['a', 'b', 'c', 'x'])
    space = space_for([reads[0].book], [twin1, twin2, other])
    picks = recommend(Mode.TASTE, reads, [twin1, twin2, other], space, 2, TODAY, Params(mmr_lambda=2.0))
    assert {p.book.title for p in picks} != {'twin1', 'twin2'}


def test_books_without_subjects_do_not_crash_and_fall_back_to_quality() -> None:
    reads = [Read(book('r', ['a', 'b']), rating=5)]
    empty = book('empty', [], rating=4.8, count=50000)
    space = space_for([reads[0].book], [empty])
    assert recommend(Mode.TASTE, reads, [empty], space, 1, TODAY)[0].score > 0
