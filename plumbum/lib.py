from __future__ import annotations

import inspect
import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from io import IOBase, StringIO
from typing import Any, TextIO

IS_WIN32 = sys.platform == "win32"


class ProcInfo:
    def __init__(self, pid: int, uid: int, stat: str, args: str):
        self.pid = pid
        self.uid = uid
        self.stat = stat
        self.args = args

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.pid!r}, {self.uid!r}, {self.stat!r}, {self.args!r})"


@contextmanager
def captured_stdout(stdin: str = "") -> Generator[TextIO, None, None]:
    """
    Captures stdout (similar to the redirect_stdout in Python 3.4+, but with slightly different arguments)
    """
    prevstdin = sys.stdin
    prevstdout = sys.stdout
    sys.stdin = StringIO(stdin)
    sys.stdout = StringIO()
    try:
        yield sys.stdout
    finally:
        sys.stdin = prevstdin
        sys.stdout = prevstdout


class StaticProperty:
    """This acts like a static property, allowing access via class or object.
    This is a non-data descriptor."""

    def __init__(self, function: Callable[[], Any]):
        self._function = function
        self.__doc__ = function.__doc__

    def __get__(self, obj: object, klass: object = None) -> Any:
        return self._function()


def getdoc(obj: object) -> str | None:
    """
    This gets a docstring if available, and cleans it, but does not look up docs in
    inheritance tree (Pre Python 3.5 behavior of ``inspect.getdoc``).
    """
    try:
        doc = obj.__doc__
    except AttributeError:
        return None
    if not isinstance(doc, str):
        return None
    return inspect.cleandoc(doc)


def read_fd_decode_safely(fd: IOBase, size: int = 4096) -> tuple[bytes, str]:
    """
    This reads a utf-8 file descriptor and returns a chunk, growing up to
    three bytes if needed to decode the character at the end.

    Returns the data and the decoded text.
    """
    data = os.read(fd.fileno(), size)
    for _ in range(3):
        try:
            return data, data.decode("utf-8")
        except UnicodeDecodeError as e:
            if e.reason != "unexpected end of data":
                raise
            data += os.read(fd.fileno(), 1)

    return data, data.decode("utf-8")
