from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's real .env (and ratings.json, .cache) out of the tests."""
    monkeypatch.chdir(tmp_path)
