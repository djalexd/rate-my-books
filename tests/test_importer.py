from pathlib import Path

import pytest

from rate_my_books import cli
from rate_my_books.importer import ImportedBook, import_books, parse_book_file
from rate_my_books.readlist import add_entry, load_readlist


@pytest.mark.parametrize(
    ('path', 'title', 'author'),
    [
        ('/books/Citite/Dune - Frank Herbert.mobi', 'Dune', 'Frank Herbert'),
        (
            '/books/Citite/De veghe in lanul se secara - J.D. Salinger.mobi',
            'De veghe in lanul se secara',
            'J.D. Salinger',
        ),
        (
            '/books/Citite/Abatia 2 - Blestemul Abatiei - Dan Dobos.mobi',
            'Abatia 2 - Blestemul Abatiei',
            'Dan Dobos',
        ),
        ('/books/Citite/Inferno_Brown_Dan.pdf', 'Inferno', 'Dan Brown'),
        ('/books/Citite/The_Da_Vinci_Code_Brown_Dan.PDF', 'The Da Vinci Code', 'Dan Brown'),
        ('/books/Citite/Only A Title.epub', 'Only A Title', None),
        ('/books/Citite/Two_Words.epub', 'Two Words', None),
        ('/books/Citite/  Spaced   Out  -  Some  Author .mobi', 'Spaced Out', 'Some Author'),
    ],
)
def test_parse_book_file_normalizes_title_and_author(path: str, title: str, author: str | None) -> None:
    assert parse_book_file(path) == ImportedBook(title, author, path)


@pytest.mark.parametrize('path', ['/books/Citite/cover.jpg', '/books/Citite/Subfolder', '/books/Citite/.mobi'])
def test_parse_book_file_ignores_other_files(path: str) -> None:
    assert parse_book_file(path) is None


def _books() -> list[ImportedBook]:
    return [
        ImportedBook('Dune', 'Frank Herbert', '/books/Dune - Frank Herbert.mobi'),
        ImportedBook('Solaris', 'Stanislaw Lem', '/books/Solaris - Stanislaw Lem.mobi'),
    ]


def test_import_writes_normalized_undated_notes_with_dropbox_path(tmp_path: Path) -> None:
    assert [is_new for _, is_new in import_books(tmp_path, _books())] == [True, True]
    entries = {e.title: e for e in load_readlist(tmp_path)}
    assert set(entries) == {'Dune', 'Solaris'}
    dune = entries['Dune']
    assert (dune.author, dune.rating, dune.read_date) == ('Frank Herbert', None, None)
    assert dune.dropbox_path == '/books/Dune - Frank Herbert.mobi'
    assert 'read_date' not in dune.path.read_text(encoding='utf-8')


def test_import_is_idempotent_and_skips_books_already_listed(tmp_path: Path) -> None:
    add_entry(tmp_path, 'dune', 'frank herbert', rating=5)
    first = import_books(tmp_path, _books())
    assert [is_new for _, is_new in first] == [False, True]
    assert [is_new for _, is_new in import_books(tmp_path, _books())] == [False, False]
    assert len(load_readlist(tmp_path)) == 2


def test_import_skips_the_same_book_twice_in_one_batch(tmp_path: Path) -> None:
    twice = [*_books(), ImportedBook('DUNE', 'Frank Herbert', '/books/other/dune.epub')]
    assert [is_new for _, is_new in import_books(tmp_path, twice)] == [True, True, False]


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    assert [is_new for _, is_new in import_books(tmp_path, _books(), dry_run=True)] == [True, True]
    assert list(tmp_path.iterdir()) == []


def test_cli_import_lists_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv('ACCESS_TOKEN', 'token')
    seen: list[tuple[str, str]] = []

    def fake_list_books(token: str, folder: str) -> list[ImportedBook]:
        seen.append((token, folder))
        return _books()

    monkeypatch.setattr(cli, 'list_books', fake_list_books)
    argv = ['import', '--path', '/books', '--readlist-dir', str(tmp_path)]

    assert cli.main([*argv, '--dry-run']) == 0
    assert list(tmp_path.iterdir()) == []
    assert 'Would add 2 notes' in capsys.readouterr().out

    assert cli.main(argv) == 0
    assert 'Added 2 notes' in capsys.readouterr().out
    assert cli.main(argv) == 0
    assert 'Added 0 notes, 2 already listed' in capsys.readouterr().out
    assert seen == [('token', '/books')] * 3


def test_cli_import_needs_a_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('ACCESS_TOKEN', raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(['import', '--path', '/books', '--readlist-dir', str(tmp_path)]) == 1
