import subprocess
from pathlib import Path

import pytest

from rate_my_books.settings import Settings, SettingsError


class FakeOp:
    """Stands in for `op read`; records the references it was asked for."""

    def __init__(self, secrets: dict[str, str] | None = None, returncode: int = 0, stderr: str = '') -> None:
        self.secrets = secrets or {}
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        out = self.secrets.get(cmd[-1], '') + '\n' if self.returncode == 0 else ''
        return subprocess.CompletedProcess(cmd, self.returncode, out, self.stderr)


@pytest.fixture
def op(monkeypatch: pytest.MonkeyPatch) -> FakeOp:
    fake = FakeOp({'op://Private/Dropbox/token': 's3cret'})
    monkeypatch.setattr('rate_my_books.settings.subprocess.run', fake)
    return fake


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('ACCESS_TOKEN', raising=False)
    monkeypatch.delenv('READLIST_DIR', raising=False)


def write_env(text: str) -> Path:
    path = Path('.env')
    path.write_text(text)
    return path


def test_reads_value_from_default_env_file() -> None:
    write_env('READLIST_DIR=/vault/books\n')
    assert Settings.load(None).get('READLIST_DIR') == '/vault/books'


def test_parses_quotes_comments_and_export() -> None:
    write_env('# comment\nexport READLIST_DIR="/my vault/books"\n')
    assert Settings.load(None).get('READLIST_DIR') == '/my vault/books'


def test_real_environment_beats_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    write_env('READLIST_DIR=/from/file\n')
    monkeypatch.setenv('READLIST_DIR', '/from/env')
    assert Settings.load(None).get('READLIST_DIR') == '/from/env'


def test_missing_default_env_file_is_fine() -> None:
    assert Settings.load(None).get('READLIST_DIR') is None


def test_missing_explicit_env_file_is_an_error() -> None:
    with pytest.raises(SettingsError, match='nope.env'):
        Settings.load(Path('nope.env'))


def test_explicit_env_file(tmp_path: Path) -> None:
    custom = tmp_path / 'custom.env'
    custom.write_text('READLIST_DIR=/custom\n')
    assert Settings.load(custom).get('READLIST_DIR') == '/custom'


def test_plain_values_never_call_op(op: FakeOp) -> None:
    write_env('READLIST_DIR=/vault/books\n')
    Settings.load(None).get('READLIST_DIR')
    assert op.calls == []


def test_op_reference_is_resolved_and_cached(op: FakeOp) -> None:
    write_env('ACCESS_TOKEN=op://Private/Dropbox/token\n')
    settings = Settings.load(None)
    assert settings.get('ACCESS_TOKEN') == 's3cret'
    assert settings.get('ACCESS_TOKEN') == 's3cret'
    assert op.calls == [['op', 'read', 'op://Private/Dropbox/token']]


def test_op_reference_in_real_environment_is_resolved(op: FakeOp, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ACCESS_TOKEN', 'op://Private/Dropbox/token')
    assert Settings.load(None).get('ACCESS_TOKEN') == 's3cret'


def test_only_the_requested_setting_is_resolved(op: FakeOp) -> None:
    write_env('ACCESS_TOKEN=op://Private/Dropbox/token\nREADLIST_DIR=op://Private/Vault/path\n')
    Settings.load(None).get('ACCESS_TOKEN')
    assert [c[-1] for c in op.calls] == ['op://Private/Dropbox/token']


def test_missing_op_binary_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_installed(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError('op')

    monkeypatch.setattr('rate_my_books.settings.subprocess.run', not_installed)
    write_env('ACCESS_TOKEN=op://Private/Dropbox/token\n')
    with pytest.raises(SettingsError, match='1Password CLI'):
        Settings.load(None).get('ACCESS_TOKEN')


def test_op_failure_reports_op_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        'rate_my_books.settings.subprocess.run', FakeOp(returncode=1, stderr='[ERROR] item not found\n')
    )
    write_env('ACCESS_TOKEN=op://Private/Dropbox/token\n')
    with pytest.raises(SettingsError, match=r'op://Private/Dropbox/token.*item not found'):
        Settings.load(None).get('ACCESS_TOKEN')


def test_op_timeout_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def hangs(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr('rate_my_books.settings.subprocess.run', hangs)
    write_env('ACCESS_TOKEN=op://Private/Dropbox/token\n')
    with pytest.raises(SettingsError, match='timed out'):
        Settings.load(None).get('ACCESS_TOKEN')
