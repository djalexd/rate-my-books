import importlib
from datetime import date
from pathlib import Path
from typing import NoReturn

import pytest

from rate_my_books import cli
from rate_my_books.catalog import Book
from rate_my_books.model import Mode, Pick
from rate_my_books.rating import RatedBook, load_ratings, save_ratings
from rate_my_books.readlist import load_readlist
from rate_my_books.service import Recommendations
from rate_my_books.viewer import ranked


@pytest.mark.parametrize('module', ['rating', 'viewer', 'cli', 'sources'])
def test_modules_import_without_side_effects(module: str) -> None:
    importlib.import_module(f'rate_my_books.{module}')


def test_ratings_round_trip(tmp_path: Path) -> None:
    books = [RatedBook('Dune - Herbert', '/books/dune.mobi', 4.3, 1000), RatedBook('Nope - X', '/books/n.mobi', 0.0, 0)]
    save_ratings(books, tmp_path / 'r.json')
    assert load_ratings(tmp_path / 'r.json') == books


def test_ranked_drops_unrated_and_prefers_popular() -> None:
    obscure = RatedBook('obscure', 'p', 4.5, 10)
    popular = RatedBook('popular', 'p', 4.4, 1_000_000)
    unrated = RatedBook('unrated', 'p', 0.0, 0)
    assert ranked([obscure, unrated, popular]) == [popular, obscure]


def test_add_writes_a_note_and_is_idempotent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ['add', '--readlist-dir', str(tmp_path), '--title', 'The Aleph', '--author', 'Borges', '--rating', '5']
    assert cli.main([*argv, '--date', '2026-10-01']) == 0
    assert cli.main(argv) == 0
    (entry,) = load_readlist(tmp_path)
    assert (entry.title, entry.rating, entry.read_date) == ('The Aleph', 5.0, date(2026, 10, 1))
    assert 'Read-list entry' in capsys.readouterr().out


def test_missing_readlist_dir_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv('READLIST_DIR', raising=False)
    assert cli.main(['taste']) == 1
    assert 'READLIST_DIR' in capsys.readouterr().err
    assert cli.main(['taste', '--readlist-dir', str(tmp_path / 'missing')]) == 1


def test_recommend_command_passes_options_and_prints_picks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}

    def fake_recommend(**kwargs: object) -> Recommendations:
        seen.update(kwargs)
        pick = Pick(Book('Solaris', 'Lem', 4.2, 100), 0.9, ['matches science fiction'])
        return Recommendations([pick], [], reads=3, library_size=10, library_without_subjects=2)

    monkeypatch.setattr(cli, 'recommend_books', fake_recommend)
    code = cli.main(['next', '--readlist-dir', str(tmp_path), '--library-picks', '1', '--half-life', '30'])
    out = capsys.readouterr().out
    assert code == 0
    assert seen['mode'] is Mode.NEXT and seen['library_picks'] == 1
    assert 'Solaris (Lem)' in out and 'matches science fiction' in out and '(none)' in out


def test_rate_requires_dropbox_token(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv('ACCESS_TOKEN', raising=False)
    assert cli.main(['rate', '--path', '/books']) == 1
    assert 'ACCESS_TOKEN' in capsys.readouterr().err


def test_rate_reads_token_from_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv('ACCESS_TOKEN', raising=False)
    (tmp_path / '.env').write_text('ACCESS_TOKEN=from-file\n')
    seen: dict[str, str] = {}

    def fake_rate(token: str, path: str, limit: int | None) -> list[RatedBook]:
        seen['token'] = token
        return []

    monkeypatch.setattr(cli, 'rate_library', fake_rate)
    assert cli.main(['rate', '--path', '/books']) == 0
    assert seen['token'] == 'from-file'


def test_view_never_touches_1password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / '.env').write_text('ACCESS_TOKEN=op://Private/Dropbox/token\n')
    save_ratings([], tmp_path / 'ratings.json')

    def boom(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError('op was called')

    monkeypatch.setattr('rate_my_books.settings.subprocess.run', boom)
    assert cli.main(['view']) == 0


def test_missing_env_file_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(['--env-file', 'nope.env', 'view']) == 1
    assert 'nope.env' in capsys.readouterr().err


def test_missing_1password_cli_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv('ACCESS_TOKEN', raising=False)
    (tmp_path / '.env').write_text('ACCESS_TOKEN=op://Private/Dropbox/token\n')

    def not_installed(*args: object, **kwargs: object) -> NoReturn:
        raise FileNotFoundError('op')

    monkeypatch.setattr('rate_my_books.settings.subprocess.run', not_installed)
    assert cli.main(['rate', '--path', '/books']) == 1
    assert '1Password CLI' in capsys.readouterr().err
