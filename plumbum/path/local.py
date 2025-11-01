from __future__ import annotations

import builtins
import errno
import glob
import logging
import os
import shutil
import urllib.parse as urlparse
import urllib.request as urllib
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import IO

from plumbum.lib import IS_WIN32
from plumbum.path.base import FSUser, Path
from plumbum.path.remote import RemotePath

from .._compat.typing import Self

try:
    from grp import getgrgid, getgrnam
    from pwd import getpwnam, getpwuid
except ImportError:

    def getpwuid(_x):  # type: ignore[misc]
        return (None,)

    def getgrgid(_x):  # type: ignore[misc]
        return (None,)

    def getpwnam(_x):  # type: ignore[misc]
        raise OSError("`getpwnam` not supported")

    def getgrnam(_x):  # type: ignore[misc]
        raise OSError("`getgrnam` not supported")


logger = logging.getLogger("plumbum.local")

_EMPTY = object()


# ===================================================================================================
# Local Paths
# ===================================================================================================
class LocalPath(Path):
    """The class implementing local-machine paths"""

    CASE_SENSITIVE = not IS_WIN32

    def __new__(cls, *parts: str) -> Self:
        if (
            len(parts) == 1
            and isinstance(parts[0], cls)
            and not isinstance(parts[0], LocalWorkdir)
        ):
            return parts[0]
        if not parts:
            raise TypeError("At least one path part is required (none given)")
        if any(isinstance(path, RemotePath) for path in parts):
            raise TypeError(f"LocalPath cannot be constructed from {parts!r}")
        return super().__new__(
            cls, os.path.normpath(os.path.join(*(str(p) for p in parts)))
        )

    @property
    def _path(self) -> str:
        return str(self)

    def _get_info(self) -> str:
        return self._path

    def _form(self, *parts: str) -> Self:
        return self.__class__(*parts)

    @property
    def name(self) -> str:
        return os.path.basename(str(self))

    @property
    def dirname(self) -> Self:
        return self.__class__(os.path.dirname(str(self)))

    @property
    def suffix(self) -> str:
        return os.path.splitext(str(self))[1]

    @property
    def suffixes(self) -> list[str]:
        exts = []
        base = str(self)
        while True:
            base, ext = os.path.splitext(base)
            if ext:
                exts.append(ext)
            else:
                return list(reversed(exts))

    @property
    def uid(self) -> FSUser:
        uid = self.stat().st_uid
        name = getpwuid(uid)[0]
        return FSUser(uid, name)

    @property
    def gid(self) -> FSUser:
        gid = self.stat().st_gid
        name = getgrgid(gid)[0]
        return FSUser(gid, name)

    def join(self, *others: str) -> Self:  # type: ignore[override]
        return self.__class__(self, *others)

    def list(self) -> list[Self]:
        return [self / fn for fn in os.listdir(str(self))]

    def iterdir(self) -> Iterator[Self]:
        try:
            return (self / fn.name for fn in os.scandir(str(self)))
        except AttributeError:
            return (self / fn for fn in os.listdir(str(self)))

    def is_dir(self) -> bool:
        return os.path.isdir(str(self))

    def is_file(self) -> bool:
        return os.path.isfile(str(self))

    def is_symlink(self) -> bool:
        return os.path.islink(str(self))

    def exists(self) -> bool:
        return os.path.exists(str(self))

    def stat(self) -> os.stat_result:
        return os.stat(str(self))

    def with_name(self, name: str) -> Self:
        return self.__class__(self.dirname) / name

    @property
    def stem(self) -> str:
        return self.name.rsplit(os.path.extsep)[0]

    def with_suffix(self, suffix: str, depth: int | None = 1) -> Self:
        if (
            suffix and not suffix.startswith(os.path.extsep)
        ) or suffix == os.path.extsep:
            raise ValueError(f"Invalid suffix {suffix!r}")
        name = self.name
        depth = len(self.suffixes) if depth is None else min(depth, len(self.suffixes))
        for _ in range(depth):
            name, _ = os.path.splitext(name)
        return self.__class__(self.dirname) / (name + suffix)

    def glob(self, pattern: str) -> builtins.list[Self]:
        return self._glob(
            pattern,
            lambda pat: [
                self.__class__(m)
                for m in glob.glob(os.path.join(glob.escape(str(self)), pat))
            ],
        )

    def delete(self) -> None:
        if not self.exists():
            return
        if self.is_dir():
            shutil.rmtree(str(self))
        else:
            try:
                os.remove(str(self))
            except OSError as ex:  # pragma: no cover
                # file might already been removed (a race with other threads/processes)
                if ex.errno != errno.ENOENT:
                    raise

    def move(self, dst: LocalPath) -> Self:
        if isinstance(dst, RemotePath):
            raise TypeError(f"Cannot move local path {self} to {dst!r}")
        shutil.move(str(self), str(dst))
        return self.__class__(dst)

    def copy(self, dst: LocalPath, override: bool | None = None) -> Self:
        if isinstance(dst, RemotePath):
            raise TypeError(f"Cannot copy local path {self} to {dst!r}")
        dst = self.__class__(dst)
        if override is False and dst.exists():
            raise TypeError("File exists and override was not specified")
        if override:
            dst.delete()
        if self.is_dir():
            shutil.copytree(str(self), str(dst))
        else:
            dst_dir = LocalPath(dst).dirname
            if not dst_dir.exists():
                dst_dir.mkdir()
            shutil.copy2(str(self), str(dst))
        return dst

    def mkdir(self, mode=0o777, parents=True, exist_ok=True):
        if not self.exists() or not exist_ok:
            try:
                if parents:
                    os.makedirs(str(self), mode)
                else:
                    os.mkdir(str(self), mode)
            except OSError as ex:  # pragma: no cover
                # directory might already exist (a race with other threads/processes)
                if ex.errno != errno.EEXIST or not exist_ok:
                    raise

    def open(self, mode: str = "r", encoding: str | None = None) -> IO:
        return open(
            str(self),
            mode,
            encoding=encoding,
        )

    def read(self, encoding: str | None = None, mode: str = "r") -> str | bytes:
        if encoding and "b" not in mode:
            mode = mode + "b"
        with self.open(mode) as f:
            data = f.read()
            if encoding:
                return data.decode(encoding)
            return data

    def write(
        self, data: str | bytes, encoding: str | None = None, mode: str | None = None
    ) -> None:
        if encoding:
            if isinstance(data, bytes):
                msg = "Must write string data if encoding given"
                raise TypeError(msg)
            data = data.encode(encoding)
        if mode is None:
            mode = "w" if isinstance(data, str) else "wb"
        with self.open(mode) as f:
            f.write(data)

    def touch(self) -> None:
        with open(str(self), "a", encoding="utf-8"):
            os.utime(str(self), None)

    def chown(
        self,
        owner: int | str | None = None,
        group: int | str | None = None,
        recursive: bool | None = None,
    ) -> None:
        if not hasattr(os, "chown"):
            raise OSError("os.chown() not supported")
        uid = (
            self.uid
            if owner is None
            else (owner if isinstance(owner, int) else getpwnam(owner)[2])
        )
        gid = (
            self.gid
            if group is None
            else (group if isinstance(group, int) else getgrnam(group)[2])
        )
        os.chown(str(self), uid, gid)
        if recursive or (recursive is None and self.is_dir()):
            for subpath in self.walk():
                os.chown(str(subpath), uid, gid)

    def chmod(self, mode: int) -> None:
        if not hasattr(os, "chmod"):
            raise OSError("os.chmod() not supported")
        os.chmod(str(self), mode)

    def access(self, mode: int = 0) -> bool:
        return os.access(str(self), self._access_mode_to_flags(mode))

    def link(self, dst: LocalPath) -> None:
        if isinstance(dst, RemotePath):
            raise TypeError(
                f"Cannot create a hardlink from local path {self} to {dst!r}"
            )
        if hasattr(os, "link"):
            os.link(str(self), str(dst))
        else:
            from plumbum.machines.local import local

            # windows: use mklink
            if self.is_dir():
                local["cmd"]("/C", "mklink", "/D", "/H", str(dst), str(self))
            else:
                local["cmd"]("/C", "mklink", "/H", str(dst), str(self))

    def symlink(self, dst: LocalPath) -> None:
        if isinstance(dst, RemotePath):
            raise TypeError(
                f"Cannot create a symlink from local path {self} to {dst!r}"
            )
        if hasattr(os, "symlink"):
            os.symlink(str(self), str(dst))
        else:
            from plumbum.machines.local import local

            # windows: use mklink
            if self.is_dir():
                local["cmd"]("/C", "mklink", "/D", str(dst), str(self))
            else:
                local["cmd"]("/C", "mklink", str(dst), str(self))

    def unlink(self) -> None:
        try:
            if hasattr(os, "symlink") or not self.is_dir():
                os.unlink(str(self))
            else:
                # windows: use rmdir for directories and directory symlinks
                os.rmdir(str(self))
        except OSError as ex:  # pragma: no cover
            # file might already been removed (a race with other threads/processes)
            if ex.errno != errno.ENOENT:
                raise

    def as_uri(self, scheme: str = "file") -> str:
        return urlparse.urljoin(f"{scheme}://", urllib.pathname2url(str(self)))

    @property
    def drive(self) -> str:
        return os.path.splitdrive(str(self))[0]

    @property
    def root(self) -> str:
        return os.path.sep


class LocalWorkdir(LocalPath):
    """Working directory manipulator"""

    def __hash__(self) -> int:
        raise TypeError("unhashable type")

    def __new__(cls) -> Self:
        return super().__new__(cls, os.getcwd())

    def chdir(self, newdir: LocalPath | str) -> Self:
        """Changes the current working directory to the given one

        :param newdir: The destination director (a string or a ``LocalPath``)
        """
        if isinstance(newdir, RemotePath):
            raise TypeError(f"newdir cannot be {newdir!r}")
        logger.debug("Chdir to %s", newdir)
        os.chdir(str(newdir))
        return self.__class__()

    def getpath(self) -> LocalPath:
        """Returns the current working directory as a ``LocalPath`` object"""
        return LocalPath(self._path)

    @contextmanager
    def __call__(self, newdir: LocalPath | str) -> Generator[Self, None, None]:
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.

        :param newdir: The destination directory (a string or a ``LocalPath``)
        """
        prev = self._path
        newdir = self.chdir(newdir)
        try:
            yield newdir
        finally:
            self.chdir(prev)
