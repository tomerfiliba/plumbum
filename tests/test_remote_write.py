"""Remote file writes must leave their upload source readable on Windows."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from plumbum.machines.remote import BaseRemoteMachine


class UploadRecorder:
    _path_write = BaseRemoteMachine._path_write

    def __init__(self, encoding="utf-8", fail=False):
        self.custom_encoding = encoding
        self.fail = fail
        self.source = None
        self.destination = None
        self.contents = None

    def upload(self, source, destination):
        self.source = Path(source)
        if os.name != "nt":
            assert stat.S_IMODE(self.source.stat().st_mode) == 0o600
        # Like scp, an upload opens the file by name using a separate handle.
        self.contents = self.source.read_bytes()
        self.destination = destination
        if self.fail:
            raise RuntimeError("upload failed")


@pytest.mark.parametrize(
    ("data", "encoding", "expected"),
    [
        (b"hello\x00world", None, b"hello\x00world"),
        (bytearray(b"hello"), None, b"hello"),
        ("\u00e9", "utf-8", b"\xc3\xa9"),
        ("\u00e9", "latin-1", b"\xe9"),
        (b"", None, b""),
    ],
)
def test_write_upload_source_is_readable_and_removed(data, encoding, expected):
    remote = UploadRecorder(encoding)

    remote._path_write("/remote/file", data)

    assert remote.contents == expected
    assert remote.destination == "/remote/file"
    assert not remote.source.exists()


def test_write_removes_upload_source_on_failure():
    remote = UploadRecorder(fail=True)

    with pytest.raises(RuntimeError, match="upload failed"):
        remote._path_write("/remote/file", b"contents")

    assert remote.contents == b"contents"
    assert not remote.source.exists()
