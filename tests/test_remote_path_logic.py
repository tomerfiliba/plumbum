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


_SAME = object()


class _FakeRemote:
    def __init__(self, statres, lstatres=_SAME):
        self._statres = statres
        self._lstatres = statres if lstatres is _SAME else lstatres
        self.unlinked: list[str] = []
        self.deleted: list[str] = []

    def _path_stat(self, _path):
        return self._statres

    def _path_lstat(self, _path):
        return self._lstatres

    def _path_unlink(self, path):
        self.unlinked.append(str(path))

    def _path_delete(self, path):
        self.deleted.append(str(path))


def _make_path(statres, lstatres=_SAME):
    # Bypass RemotePath.__new__, which would require a real remote machine.
    # RemotePath subclasses ``str``, so build it via ``str.__new__`` with the
    # path text and attach a fake remote.
    p = str.__new__(RemotePath, "/tmp/thing")
    p.remote = _FakeRemote(statres, lstatres)
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


def test_access_combined_mode_requires_all_bits():
    # r--r--r--: readable but not writable, so R_OK|W_OK must fail.
    p = _make_path(_make_statres(0o444, "regular file"))
    assert p.access("r") is True
    assert p.access("rw") is False
    assert p.access(os.R_OK | os.W_OK) is False
    p = _make_path(_make_statres(0o600, "regular file"))
    assert p.access("rw") is True
    assert p.access("rwx") is False


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


def test_unlink_symlink_to_directory():
    # Backends whose stat follows symlinks (Paramiko) report a symlink to a
    # directory as a directory; unlink must consult the link metadata instead.
    p = _make_path(
        _make_statres(0o755, "directory"),
        lstatres=_make_statres(0o777, "symbolic link"),
    )
    p.unlink()
    assert p.remote.unlinked == [str(p)]
    assert p.remote.deleted == []


def test_unlink_dangling_symlink():
    # stat on a dangling symlink reports "missing", but the link itself exists
    # and must still be removed.
    p = _make_path(None, lstatres=_make_statres(0o777, "symbolic link"))
    p.unlink()
    assert p.remote.unlinked == [str(p)]
