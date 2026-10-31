from datetime import date
from pathlib import Path

from rate_my_books.readlist import add_entry, load_readlist
from rate_my_books.text import normalize, split_title_author


def test_normalize_strips_accents_and_punctuation() -> None:
    assert normalize('Abaddón, Exterminatorul!') == 'abaddon exterminatorul'


def test_split_title_author_uses_last_separator() -> None:
    assert split_title_author('Aliens - Misiune - Foo Bar') == ('Aliens - Misiune', 'Foo Bar')
    assert split_title_author('Just A Title') == ('Just A Title', None)


def test_load_reads_frontmatter_and_ignores_other_notes(tmp_path: Path) -> None:
    (tmp_path / 'a.md').write_text(
        '---\ntitle: The Aleph\nauthor: Borges\nrating: 5\nread_date: 2026-10-01\n---\nnotes'
    )
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'sub' / 'b.md').write_text('---\ntitle: "Colon: In Title"\n---\n')
    (tmp_path / 'daily.md').write_text('# no frontmatter')
    (tmp_path / 'other.md').write_text('---\ntags: [x]\n---\n')
    entries = {e.title: e for e in load_readlist(tmp_path)}
    assert set(entries) == {'The Aleph', 'Colon: In Title'}
    assert entries['The Aleph'].rating == 5.0
    assert entries['The Aleph'].read_date == date(2026, 10, 1)
    assert entries['Colon: In Title'].rating is None


def test_add_entry_round_trips_and_is_idempotent(tmp_path: Path) -> None:
    path = add_entry(tmp_path, 'Title: With Colon', 'Some Author', 4, date(2026, 10, 30))
    again = add_entry(tmp_path, 'title with colon', 'some author', 2)
    assert again == path
    assert len(list(tmp_path.glob('*.md'))) == 1
    (entry,) = load_readlist(tmp_path)
    assert (entry.title, entry.author, entry.rating, entry.read_date) == (
        'Title: With Colon',
        'Some Author',
        4.0,
        date(2026, 10, 30),
    )
