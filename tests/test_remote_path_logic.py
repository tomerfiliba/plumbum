"""Pure-logic tests for RemotePath that do not require a live SSH connection.

These exercise RemotePath.access (permission-bit math, F_OK existence) and
RemotePath.unlink (refusing to recursively delete a directory) by constructing
the object without invoking ``__new__`` (which would need a real remote) and
stubbing the ``remote`` attribute with a tiny fake.
"""

from __future__ import annotations

import errno
import os

import pytest

from plumbum.path.remote import RemotePath, RemoteStatRes


def _make_statres(st_mode: int, text_mode: str) -> RemoteStatRes:
    res = RemoteStatRes((st_mode, 0, 0, 1, 0, 0, 0, 0.0, 0.0, 0.0))
    res.text_mode = text_mode
    return res


class _FakeRemote:
    def __init__(self, statres):
        self._statres = statres
        self.unlinked: list[str] = []
        self.deleted: list[str] = []

    def _path_stat(self, _path):
        return self._statres

    def _path_unlink(self, path):
        self.unlinked.append(str(path))

    def _path_delete(self, path):
        self.deleted.append(str(path))


def _make_path(statres):
    # Bypass RemotePath.__new__, which would require a real remote machine.
    # RemotePath subclasses ``str``, so build it via ``str.__new__`` with the
    # path text and attach a fake remote.
    p = str.__new__(RemotePath, "/tmp/thing")
    p.remote = _FakeRemote(statres)
    p.CASE_SENSITIVE = True
    return p


def test_access_existence_f_ok():
    # A file with no permission bits set still "exists" for F_OK / mode 0.
    p = _make_path(_make_statres(0o000, "regular file"))
    assert p.access() is True
    assert p.access(os.F_OK) is True
    assert p.access("f") is True


def test_access_missing_returns_false():
    p = _make_path(None)
    assert p.access() is False
    assert p.access("r") is False


def test_access_world_readable_reports_readable():
    # World-readable only (0o004): owner/group bits are clear, "other" is set.
    p = _make_path(_make_statres(0o004, "regular file"))
    assert p.access("r") is True
    assert p.access("w") is False


def test_access_owner_and_group_bits():
    p = _make_path(_make_statres(0o640, "regular file"))  # rw-r-----
    assert p.access("r") is True
    assert p.access("w") is True
    assert p.access("x") is False


def test_unlink_removes_file_non_recursively():
    p = _make_path(_make_statres(0o644, "regular file"))
    p.unlink()
    assert p.remote.unlinked == [str(p)]
    assert p.remote.deleted == []


def test_unlink_removes_symlink():
    p = _make_path(_make_statres(0o777, "symbolic link"))
    p.unlink()
    assert p.remote.unlinked == [str(p)]


def test_unlink_refuses_directory():
    p = _make_path(_make_statres(0o755, "directory"))
    with pytest.raises(OSError) as exc:
        p.unlink()
    assert exc.value.errno == errno.EISDIR
    assert p.remote.unlinked == []
    assert p.remote.deleted == []


def test_unlink_missing_is_noop():
    p = _make_path(None)
    p.unlink()  # should not raise
    assert p.remote.unlinked == []
