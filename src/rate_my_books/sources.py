"""Where the library comes from: files in a Dropbox folder."""

from collections.abc import Iterator

import dropbox  # type: ignore[import-untyped,unused-ignore]
from dropbox.files import Metadata  # type: ignore[import-untyped,unused-ignore]


def list_dropbox_folder(client: dropbox.Dropbox, path: str) -> Iterator[Metadata]:
    """All entries directly under `path`, following Dropbox pagination."""
    result = client.files_list_folder(path)
    while True:
        yield from result.entries
        if not result.has_more:
            return
        result = client.files_list_folder_continue(result.cursor)
