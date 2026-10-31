"""Settings from the environment or a .env file.

A value like op://vault/item/field is read from 1Password with the `op` CLI, only when that setting is asked for.
The real environment wins over the .env file.
"""

import os
import subprocess
from pathlib import Path
from typing import Self

from dotenv import dotenv_values

DEFAULT_ENV_FILE = Path('.env')
OP_PREFIX = 'op://'
OP_TIMEOUT_SECONDS = 30


class SettingsError(Exception):
    """A setting could not be loaded."""


def _read_from_1password(reference: str) -> str:
    try:
        done = subprocess.run(['op', 'read', reference], capture_output=True, text=True, timeout=OP_TIMEOUT_SECONDS)
    except FileNotFoundError:
        raise SettingsError(f'{reference} needs the 1Password CLI (`op`), which was not found on PATH') from None
    except subprocess.TimeoutExpired:
        raise SettingsError(f'`op read {reference}` timed out after {OP_TIMEOUT_SECONDS}s') from None
    if done.returncode != 0:
        raise SettingsError(f'`op read {reference}` failed: {done.stderr.strip()}')
    return done.stdout.removesuffix('\n')


class Settings:
    def __init__(self, file_values: dict[str, str]) -> None:
        self._file_values = file_values
        self._resolved: dict[str, str] = {}

    @classmethod
    def load(cls, env_file: Path | None) -> Self:
        """Read `env_file`, or ./.env when it is None (which may be absent)."""
        path = env_file or DEFAULT_ENV_FILE
        if not path.is_file():
            if env_file is not None:
                raise SettingsError(f'Env file does not exist: {env_file}')
            return cls({})
        return cls({k: v for k, v in dotenv_values(path).items() if v is not None})

    def get(self, name: str) -> str | None:
        if name in self._resolved:
            return self._resolved[name]
        value = os.environ.get(name) or self._file_values.get(name)
        if value and value.startswith(OP_PREFIX):
            value = _read_from_1password(value)
        if value:
            self._resolved[name] = value
        return value or None
