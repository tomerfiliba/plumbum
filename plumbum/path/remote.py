from __future__ import annotations

import builtins
import copy
import errno
import os
import typing
import urllib.request as urllib
from contextlib import contextmanager

from plumbum.commands import ProcessExecutionError, shquote
from plumbum.path.base import FSUser, Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from plumbum.machines.remote import BaseRemoteMachine

    from .._compat.typing import Self


class StatRes:
    """POSIX-like stat result"""

    _tup: tuple[int, int, int, int, int, int, int, float, float, float]

    def __init__(
        self, tup: tuple[int, int, int, int, int, int, int, float, float, float]
    ):
        self._tup = copy.copy(tup)

    def __getitem__(self, index: int) -> int | float:
        return self._tup[index]

    @property
    def st_mode(self) -> int:
        return self._tup[0]

    @property
    def st_ino(self) -> int:
        return self._tup[1]

    @property
    def st_dev(self) -> int:
        return self._tup[2]

    @property
    def st_nlink(self) -> int:
        return self._tup[3]

    @property
    def st_uid(self) -> int:
        return self._tup[4]

    @property
    def st_gid(self) -> int:
        return self._tup[5]

    @property
    def st_size(self) -> int:
        return self._tup[6]

    @property
    def st_atime(self) -> float:
        return self._tup[7]

    @property
    def st_mtime(self) -> float:
        return self._tup[8]

    @property
    def st_ctime(self) -> float:
        return self._tup[9]

    # Aliases for backward compatibility / convenience
    mode = st_mode
    ino = st_ino
    dev = st_dev
    nlink = st_nlink
    uid = st_uid
    gid = st_gid
    size = st_size
    atime = st_atime
    mtime = st_mtime
    ctime = st_ctime


class RemotePath(Path):
    """The class implementing remote-machine paths"""

    remote: BaseRemoteMachine

    def __new__(cls, remote: BaseRemoteMachine, *parts: str) -> Self:
        if not parts:
            raise TypeError("At least one path part is required (none given)")
        windows = remote.uname.lower() == "windows"
        normed: list[str] = []

        parts = tuple(
            map(str, parts)
        )  # force the paths into string, so subscription works properly
        # Simple skip if path is absolute
        if parts[0] and parts[0][0] not in ("/", "\\"):
            cwd = (
                remote._cwd
                if hasattr(remote, "_cwd")
                else remote._session.run("pwd")[1].strip()
            )
            parts = (cwd, *parts)

        for p in parts:
            if windows:
                plist = str(p).replace("\\", "/").split("/")
            else:
                plist = str(p).split("/")
            if not plist[0]:
                plist.pop(0)
                del normed[:]
            for item in plist:
                if item in {"", "."}:
                    continue
                if item == "..":
                    if normed:
                        normed.pop(-1)
                else:
                    normed.append(item)
        if windows:
            self = super().__new__(cls, "\\".join(normed))
            self.CASE_SENSITIVE = False  # On this object only
        else:
            self = super().__new__(cls, "/" + "/".join(normed))
            self.CASE_SENSITIVE = True

        self.remote = remote
        return self

    def _form(self, *parts: str) -> Self:
        return self.__class__(self.remote, *parts)

    @property
    def _path(self) -> str:
        return str(self)

    @property
    def name(self) -> str:
        if "/" not in str(self):
            return str(self)
        return str(self).rsplit("/", 1)[1]

    @property
    def dirname(self) -> Self | str:  # type: ignore[override]
        if "/" not in str(self):
            return str(self)
        return self.__class__(self.remote, str(self).rsplit("/", 1)[0])

    @property
    def suffix(self) -> str:
        return "." + self.name.rsplit(".", 1)[1]

    @property
    def suffixes(self) -> list[str]:
        name = self.name
        exts = []
        while "." in name:
            name, ext = name.rsplit(".", 1)
            exts.append("." + ext)
        return list(reversed(exts))

    @property
    def uid(self) -> FSUser:
        uid, name = self.remote._path_getuid(self)
        return FSUser(int(uid), name)

    @property
    def gid(self) -> FSUser:
        gid, name = self.remote._path_getgid(self)
        return FSUser(int(gid), name)

    def _get_info(self) -> tuple[BaseRemoteMachine, str]:  # type: ignore[override]
        return (self.remote, self._path)

    def join(self, *parts: str) -> Self:  # type: ignore[override]
        return self.__class__(self.remote, self, *parts)

    def list(self) -> list[Self]:
        if not self.is_dir():
            return []
        return [self.join(fn) for fn in self.remote._path_listdir(self)]

    def iterdir(self) -> Iterable[Self]:
        if not self.is_dir():
            return ()
        return (self.join(fn) for fn in self.remote._path_listdir(self))

    def is_dir(self) -> bool:
        res = self.remote._path_stat(self)
        if not res:
            return False
        return res.text_mode == "directory"

    def is_file(self) -> bool:
        res = self.remote._path_stat(self)
        if not res:
            return False
        return res.text_mode in ("regular file", "regular empty file")

    def is_symlink(self) -> bool:
        res = self.remote._path_stat(self)
        if not res:
            return False
        return res.text_mode == "symbolic link"

    def exists(self) -> bool:
        return self.remote._path_stat(self) is not None

    def stat(self) -> StatRes:  # type: ignore[override]
        res = self.remote._path_stat(self)
        if res is None:
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), "")
        return res

    def with_name(self, name: str) -> Self:
        return self.__class__(self.remote, self.dirname) / name

    def with_suffix(self, suffix: str, depth: int | None = 1) -> Self:
        if (suffix and not suffix.startswith(".")) or suffix == ".":
            raise ValueError(f"Invalid suffix {suffix!r}")
        name = self.name
        depth = len(self.suffixes) if depth is None else min(depth, len(self.suffixes))
        for _ in range(depth):
            name, _ = name.rsplit(".", 1)
        return self.__class__(self.remote, self.dirname) / (name + suffix)

    def glob(self, pattern: str) -> builtins.list[Self]:
        return self._glob(
            pattern,
            lambda pat: [
                RemotePath(self.remote, m) for m in self.remote._path_glob(self, pat)
            ],
        )

    def delete(self) -> None:
        if not self.exists():
            return
        self.remote._path_delete(self)

    unlink = delete

    def move(self, dst: RemotePath | str) -> Self:
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError(
                f"dst must be a string or a RemotePath (to the same remote machine), got {dst!r}"
            )
        return self.remote._path_move(self, dst)

    def copy(self, dst: RemotePath | str, override: bool | None = False) -> Self:
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError(
                f"dst must be a string or a RemotePath (to the same remote machine), got {dst!r}"
            )
        if override:
            if isinstance(dst, str):
                dst = RemotePath(self.remote, dst)
            dst.delete()
        else:
            if isinstance(dst, str):
                dst = RemotePath(self.remote, dst)
            if dst.exists():
                raise TypeError("Override not specified and dst exists")

        return self.remote._path_copy(self, dst)

    def mkdir(
        self, mode: int | None = None, parents: bool = True, exist_ok: bool = True
    ) -> None:
        if parents and exist_ok:
            self.remote._path_mkdir(self, mode=mode, minus_p=True)
        else:
            if parents and len(self.parts) > 1:
                self.remote._path_mkdir(self.parent, mode=mode, minus_p=True)
            try:
                self.remote._path_mkdir(self, mode=mode, minus_p=False)
            except ProcessExecutionError as ex:
                if "File exists" not in ex.stderr:
                    raise

                if not exist_ok:
                    raise OSError(
                        errno.EEXIST, "File exists (on remote end)", str(self)
                    ) from None

    def read(self, encoding=None):
        data = self.remote._path_read(self)
        if encoding:
            return data.decode(encoding)
        return data

    def write(self, data, encoding=None):
        if encoding:
            data = data.encode(encoding)
        self.remote._path_write(self, data)

    def touch(self):
        self.remote._path_touch(str(self))

    def chown(self, owner=None, group=None, recursive=None):
        self.remote._path_chown(
            self, owner, group, self.is_dir() if recursive is None else recursive
        )

    def chmod(self, mode):
        self.remote._path_chmod(mode, self)

    def access(self, mode=0):
        mode = self._access_mode_to_flags(mode)
        res = self.remote._path_stat(self)
        if res is None:
            return False
        mask = res.st_mode & 0x1FF
        return ((mask >> 6) & mode) or ((mask >> 3) & mode)

    def link(self, dst):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError(
                f"dst must be a string or a RemotePath (to the same remote machine), got {dst!r}"
            )
        self.remote._path_link(self, dst, False)

    def symlink(self, dst):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError(
                "dst must be a string or a RemotePath (to the same remote machine), got {dst!r}"
            )
        self.remote._path_link(self, dst, True)

    def open(self, mode="r", bufsize=-1, *, encoding=None):
        """
        Opens this path as a file.

        Only works for ParamikoMachine-associated paths for now.
        """
        if encoding is not None:
            raise NotImplementedError(
                "encoding not supported for ParamikoMachine paths"
            )

        if hasattr(self.remote, "sftp") and hasattr(self.remote.sftp, "open"):
            return self.remote.sftp.open(self, mode, bufsize)

        raise NotImplementedError(
            "RemotePath.open only works for ParamikoMachine-associated paths for now"
        )

    def as_uri(self, scheme="ssh"):
        suffix = urllib.pathname2url(str(self))
        return f"{scheme}://{self.remote._fqhost}{suffix}"

    @property
    def stem(self):
        return self.name.rsplit(".")[0]

    @property
    def root(self):
        return "/"

    @property
    def drive(self):
        return ""


class RemoteWorkdir(RemotePath):
    """Remote working directory manipulator"""

    def __new__(cls, remote):
        return super().__new__(cls, remote, remote._session.run("pwd")[1].strip())

    def __hash__(self):
        raise TypeError("unhashable type")

    def chdir(self, newdir):
        """Changes the current working directory to the given one"""
        self.remote._session.run(f"cd {shquote(newdir)}")
        if hasattr(self.remote, "_cwd"):
            del self.remote._cwd
        return self.__class__(self.remote)

    def getpath(self):
        """Returns the current working directory as a
        `remote path <plumbum.path.remote.RemotePath>` object"""
        return RemotePath(self.remote, self)

    @contextmanager
    def __call__(self, newdir):
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.

        :param newdir: The destination director (a string or a
                       :class:`RemotePath <plumbum.path.remote.RemotePath>`)
        """
        prev = self._path
        changed_dir = self.chdir(newdir)
        try:
            yield changed_dir
        finally:
            self.chdir(prev)
