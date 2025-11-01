from __future__ import annotations

import builtins
import itertools
import operator
import os
import typing
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable, Iterator
from functools import reduce
from typing import IO, SupportsIndex, TypeVar

from .._compat.typing import Self

FLAGS = {"f": os.F_OK, "w": os.W_OK, "r": os.R_OK, "x": os.X_OK}

P = TypeVar("P", bound="Path")


class FSUser(int):
    """A special object that represents a file-system user. It derives from ``int``, so it behaves
    just like a number (``uid``/``gid``), but also have a ``.name`` attribute that holds the
    string-name of the user, if given (otherwise ``None``)
    """

    name: str | None

    def __new__(cls, val: int, name: str | None = None) -> Self:
        self = int.__new__(cls, val)
        self.name = name
        return self


class Path(str, ABC):
    """An abstraction over file system paths. This class is abstract, and the two implementations
    are :class:`LocalPath <plumbum.machines.local.LocalPath>` and
    :class:`RemotePath <plumbum.path.remote.RemotePath>`.
    """

    CASE_SENSITIVE = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self}>"

    def __truediv__(self, other: str | Self) -> Self:
        """Joins two paths"""
        return self.join(other)

    @typing.overload
    def __getitem__(self, key: str | Path) -> Self: ...

    @typing.overload
    def __getitem__(self, key: SupportsIndex | slice) -> str: ...

    def __getitem__(self, key: str | Path | SupportsIndex | slice) -> Self | str:
        if isinstance(key, (str, Path)):
            return self / key
        return str(self)[key]

    def __floordiv__(self, expr: str) -> list[Self]:
        """Returns a (possibly empty) list of paths that matched the glob-pattern under this path"""
        return self.glob(expr)

    def __iter__(self) -> Iterator[Self]:
        """Iterate over the files in this directory"""
        return iter(self.list())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Path):
            return self._get_info() == other._get_info()
        if isinstance(other, str):
            if self.CASE_SENSITIVE:
                return str(self) == other

            return str(self).lower() == other.lower()

        return NotImplemented

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __gt__(self, other: object) -> bool:
        return str(self) > str(other)

    def __ge__(self, other: object) -> bool:
        return str(self) >= str(other)

    def __lt__(self, other: object) -> bool:
        return str(self) < str(other)

    def __le__(self, other: object) -> bool:
        return str(self) <= str(other)

    def __hash__(self) -> int:
        return hash(str(self)) if self.CASE_SENSITIVE else hash(str(self).lower())

    def __bool__(self) -> bool:
        return bool(str(self))

    def __fspath__(self) -> str:
        """Added for Python 3.6 support"""
        return str(self)

    def __contains__(self, item: object) -> bool:
        """Paths should support checking to see if an file or folder is in them."""
        try:
            return (self / item.name).exists()  # type: ignore[attr-defined]
        except AttributeError:
            return (self / item).exists()  # type: ignore[operator]

    @abstractmethod
    def _form(self, *parts: typing.Any) -> Self:
        pass

    def up(self, count: int = 1) -> Self:
        """Go up in ``count`` directories (the default is 1)"""
        return self.join("../" * count)

    def walk(
        self,
        filter: Callable[[Self], bool] = lambda _: True,  # pylint: disable=redefined-builtin
        dir_filter: Callable[[Self], bool] = lambda _: True,
    ) -> Generator[Self, None, None]:
        """traverse all (recursive) sub-elements under this directory, that match the given filter.
        By default, the filter accepts everything; you can provide a custom filter function that
        takes a path as an argument and returns a boolean

        :param filter: the filter (predicate function) for matching results. Only paths matching
                       this predicate are returned. Defaults to everything.
        :param dir_filter: the filter (predicate function) for matching directories. Only directories
                           matching this predicate are recursed into. Defaults to everything.
        """
        for p in self.list():
            if filter(p):
                yield p
            if p.is_dir() and dir_filter(p):
                yield from p.walk(filter, dir_filter)

    @property
    @abstractmethod
    def name(self) -> str:
        """The basename component of this path"""

    @property
    def basename(self) -> str:
        """Included for compatibility with older Plumbum code"""
        warnings.warn("Use .name instead", FutureWarning, stacklevel=2)
        return self.name

    @property
    @abstractmethod
    def stem(self) -> str:
        """The name without an extension, or the last component of the path"""

    @property
    @abstractmethod
    def dirname(self) -> Self:
        """The dirname component of this path"""

    @property
    @abstractmethod
    def root(self) -> str:
        """The root of the file tree (`/` on Unix)"""

    @property
    @abstractmethod
    def drive(self) -> str:
        """The drive letter (on Windows)"""

    @property
    @abstractmethod
    def suffix(self) -> str:
        """The suffix of this file"""

    @property
    @abstractmethod
    def suffixes(self) -> list[str]:
        """This is a list of all suffixes"""

    @property
    @abstractmethod
    def uid(self) -> FSUser:
        """The user that owns this path. The returned value is a :class:`FSUser <plumbum.path.FSUser>`
        object which behaves like an ``int`` (as expected from ``uid``), but it also has a ``.name``
        attribute that holds the string-name of the user"""

    @property
    @abstractmethod
    def gid(self) -> FSUser:
        """The group that owns this path. The returned value is a :class:`FSUser <plumbum.path.FSUser>`
        object which behaves like an ``int`` (as expected from ``gid``), but it also has a ``.name``
        attribute that holds the string-name of the group"""

    @abstractmethod
    def as_uri(self, scheme: str = ...) -> str:
        """Returns a universal resource identifier. Use ``scheme`` to force a scheme."""

    @abstractmethod
    def _get_info(self) -> str | tuple[str, str]:
        pass

    @abstractmethod
    def join(self, *parts: str) -> Self:  # type: ignore[override]
        """Joins this path with any number of paths"""

    @abstractmethod
    def list(self) -> builtins.list[Self]:
        """Returns the files in this directory"""

    @abstractmethod
    def iterdir(self) -> Iterable[Self]:
        """Returns an iterator over the directory. Might be slightly faster on Python 3.5 than .list()"""

    @abstractmethod
    def is_dir(self) -> bool:
        """Returns ``True`` if this path is a directory, ``False`` otherwise"""

    def isdir(self) -> bool:
        """Included for compatibility with older Plumbum code"""
        warnings.warn("Use .is_dir() instead", FutureWarning, stacklevel=2)
        return self.is_dir()

    @abstractmethod
    def is_file(self) -> bool:
        """Returns ``True`` if this path is a regular file, ``False`` otherwise"""

    def isfile(self) -> bool:
        """Included for compatibility with older Plumbum code"""
        warnings.warn("Use .is_file() instead", FutureWarning, stacklevel=2)
        return self.is_file()

    def islink(self) -> bool:
        """Included for compatibility with older Plumbum code"""
        warnings.warn("Use is_symlink instead", FutureWarning, stacklevel=2)
        return self.is_symlink()

    @abstractmethod
    def is_symlink(self) -> bool:
        """Returns ``True`` if this path is a symbolic link, ``False`` otherwise"""

    @abstractmethod
    def exists(self) -> bool:
        """Returns ``True`` if this path exists, ``False`` otherwise"""

    @abstractmethod
    def stat(self) -> os.stat_result:
        """Returns the os.stats for a file"""

    @abstractmethod
    def with_name(self, name: str) -> Self:
        """Returns a path with the name replaced"""

    @abstractmethod
    def with_suffix(self, suffix: str, depth: int | None = 1) -> Self:
        """Returns a path with the suffix replaced. Up to last ``depth`` suffixes will be
        replaced. None will replace all suffixes. If there are less than ``depth`` suffixes,
        this will replace all suffixes. ``.tar.gz`` is an example where ``depth=2`` or
        ``depth=None`` is useful"""

    def preferred_suffix(self, suffix: str) -> Self:
        """Adds a suffix if one does not currently exist (otherwise, no change). Useful
        for loading files with a default suffix"""
        return self if len(self.suffixes) > 0 else self.with_suffix(suffix)

    @abstractmethod
    def glob(self, pattern: str) -> builtins.list[Self]:
        """Returns a (possibly empty) list of paths that matched the glob-pattern under this path"""

    @abstractmethod
    def delete(self) -> None:
        """Deletes this path (recursively, if a directory)"""

    @abstractmethod
    def move(self, dst: Self) -> Self:
        """Moves this path to a different location"""

    def rename(self, newname: str) -> Self:
        """Renames this path to the ``new name`` (only the basename is changed)"""
        return self.move(self.up() / newname)

    @abstractmethod
    def copy(self, dst: Self, override: bool | None = None) -> Self:
        """Copies this path (recursively, if a directory) to the destination path "dst".
        Raises TypeError if dst exists and override is False.
        Will overwrite if override is True.
        Will silently fail to copy if override is None (the default)."""

    @abstractmethod
    def mkdir(
        self, mode: int = 0o777, parents: bool = True, exist_ok: bool = True
    ) -> None:
        """
        Creates a directory at this path.

        :param mode: **Currently only implemented for local paths!** Numeric mode to use for directory
                     creation, which may be ignored on some systems. The current implementation
                     reproduces the behavior of ``os.mkdir`` (i.e., the current umask is first masked
                     out), but this may change for remote paths. As with ``os.mkdir``, it is recommended
                     to call :func:`chmod` explicitly if you need to be sure.
        :param parents: If this is true (the default), the directory's parents will also be created if
                        necessary.
        :param exist_ok: If this is true (the default), no exception will be raised if the directory
                         already exists (otherwise ``OSError``).

        Note that the defaults for ``parents`` and ``exist_ok`` are the opposite of what they are in
        Python's own ``pathlib`` - this is to maintain backwards-compatibility with Plumbum's behaviour
        from before they were implemented.
        """

    @abstractmethod
    def open(self, mode: str = "r", *, encoding: str | None = None) -> IO:
        """opens this path as a file"""

    @abstractmethod
    def read(self, encoding: str | None = None) -> str | bytes:
        """returns the contents of this file as a ``str``. By default the data is read
        as text, but you can specify the encoding, e.g., ``'latin1'`` or ``'utf8'``"""

    @abstractmethod
    def write(self, data: str | bytes, encoding: str | None = None) -> None:
        """writes the given data to this file. By default the data is written as-is
        (either text or binary), but you can specify the encoding, e.g., ``'latin1'``
        or ``'utf8'``"""

    @abstractmethod
    def touch(self) -> None:
        """Update the access time. Creates an empty file if none exists."""

    @abstractmethod
    def chown(
        self,
        owner: int | str | None = None,
        group: int | str | None = None,
        recursiv: bool | None = None,
    ) -> None:
        """Change ownership of this path.

        :param owner: The owner to set (either ``uid`` or ``username``), optional
        :param group: The group to set (either ``gid`` or ``groupname``), optional
        :param recursive: whether to change ownership of all contained files and subdirectories.
                          Only meaningful when ``self`` is a directory. If ``None``, the value
                          will default to ``True`` if ``self`` is a directory, ``False`` otherwise.
        """

    @abstractmethod
    def chmod(self, mode: int) -> None:
        """Change the mode of path to the numeric mode.

        :param mode: file mode as for os.chmod
        """

    @staticmethod
    def _access_mode_to_flags(mode: int, flags: dict[str, int] | None = None) -> int:
        if flags is None:
            flags = FLAGS

        if isinstance(mode, str):
            return reduce(operator.or_, [flags[m] for m in mode.lower()], 0)

        return mode

    @abstractmethod
    def access(self, mode: int = 0) -> bool:
        """Test file existence or permission bits

        :param mode: a bitwise-or of access bits, or a string-representation thereof:
                     ``'f'``, ``'x'``, ``'r'``, ``'w'`` for ``os.F_OK``, ``os.X_OK``,
                     ``os.R_OK``, ``os.W_OK``
        """

    @abstractmethod
    def link(self, dst: Self) -> None:
        """Creates a hard link from ``self`` to ``dst``

        :param dst: the destination path
        """

    @abstractmethod
    def symlink(self, dst: Self) -> None:
        """Creates a symbolic link from ``self`` to ``dst``

        :param dst: the destination path
        """

    @abstractmethod
    def unlink(self) -> None:
        """Deletes a symbolic link"""

    def split(self, *_args: object, **_kargs: object) -> builtins.list[str]:
        """Splits the path on directory separators, yielding a list of directories, e.g,
        ``"/var/log/messages"`` will yield ``['var', 'log', 'messages']``.
        """
        parts = []
        path = self
        while path != path.dirname:
            parts.append(path.name)
            path = path.dirname
        return parts[::-1]

    @property
    def parts(self) -> tuple[str, ...]:
        """Splits the directory into parts, including the base directory, returns a tuple"""
        return (self.drive + self.root, *self)

    def relative_to(self, source: Self) -> RelativePath:
        """Computes the "relative path" require to get from ``source`` to ``self``. They satisfy the invariant
        ``source_path + (target_path - source_path) == target_path``. For example::

            /var/log/messages - /var/log/messages = []
            /var/log/messages - /var              = [log, messages]
            /var/log/messages - /                 = [var, log, messages]
            /var/log/messages - /var/tmp          = [.., log, messages]
            /var/log/messages - /opt              = [.., var, log, messages]
            /var/log/messages - /opt/lib          = [.., .., var, log, messages]
        """
        if isinstance(source, str):
            source = self._form(source)
        parts = self.split()
        baseparts = source.split()
        ancestors = len(
            list(itertools.takewhile(lambda p: p[0] == p[1], zip(parts, baseparts)))
        )
        return RelativePath([".."] * (len(baseparts) - ancestors) + parts[ancestors:])

    def __sub__(self, other: Self) -> RelativePath:
        """Same as ``self.relative_to(other)``"""
        return self.relative_to(other)

    @classmethod
    def _glob(
        cls, pattern: str | Iterable[str], fn: Callable[[str], builtins.list[str]]
    ) -> builtins.list[Self]:
        """Applies a glob string or list/tuple/iterable to the current path, using ``fn``"""
        if isinstance(pattern, str):
            return [cls(p) for p in fn(pattern)]  # type: ignore[abstract]

        results = {
            cls(value)  # type: ignore[abstract]
            for single_pattern in pattern
            for value in fn(single_pattern)
        }
        return sorted(results)

    def resolve(self, strict: bool = False) -> Self:  # noqa: ARG002
        """Added to allow pathlib like syntax. Does nothing since
        Plumbum paths are always absolute. Does not (currently) resolve
        symlinks."""
        # TODO: Resolve symlinks here
        return self

    @property
    def parents(self) -> tuple[str, ...]:
        """Pathlib like sequence of ancestors"""
        as_list = (
            reduce(lambda x, y: self._form(x) / y, self.parts[:i], self.parts[0])
            for i in range(len(self.parts) - 1, 0, -1)
        )
        return tuple(as_list)

    @property
    def parent(self) -> str:
        """Pathlib like parent of the path."""
        return self.parents[0]


class RelativePath:
    """
    Relative paths are the "delta" required to get from one path to another.
    Note that relative path do not point at anything, and thus are not paths.
    Therefore they are system agnostic (but closed under addition)
    Paths are always absolute and point at "something", whether existent or not.

    Relative paths are created by subtracting paths (``Path.relative_to``)
    """

    def __init__(self, parts: list[str]):
        self.parts = parts

    def __str__(self) -> str:
        return "/".join(self.parts)

    def __iter__(self) -> Iterator[str]:
        return iter(self.parts)

    def __len__(self) -> int:
        return len(self.parts)

    @typing.overload
    def __getitem__(self, index: SupportsIndex) -> str: ...

    @typing.overload
    def __getitem__(self, index: slice) -> list[str]: ...

    def __getitem__(self, index: SupportsIndex | slice) -> list[str] | str:
        return self.parts[index]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.parts!r})"

    def __eq__(self, other: object) -> bool:
        return str(self) == str(other)

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __gt__(self, other: object) -> bool:
        return str(self) > str(other)

    def __ge__(self, other: object) -> bool:
        return str(self) >= str(other)

    def __lt__(self, other: object) -> bool:
        return str(self) < str(other)

    def __le__(self, other: object) -> bool:
        return str(self) <= str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __bool__(self) -> bool:
        return bool(str(self))

    def up(self, count: int = 1) -> Self:
        return self.__class__(self.parts[:-count])

    def __radd__(self, path: P) -> P:
        return path.join(*self.parts)
