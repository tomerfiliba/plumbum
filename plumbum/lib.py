import inspect
import os
import sys
from contextlib import contextmanager
from io import StringIO

IS_WIN32 = sys.platform == "win32"


def _setdoc(super):  # @ReservedAssignment
    """This inherits the docs on the current class. Not really needed for Python 3.5,
    due to new behavior of inspect.getdoc, but still doesn't hurt."""

    def deco(func):
        func.__doc__ = getattr(getattr(super, func.__name__, None), "__doc__", None)
        return func

    return deco


class ProcInfo:
    def __init__(self, pid, uid, stat, args):
        self.pid = pid
        self.uid = uid
        self.stat = stat
        self.args = args

    def __repr__(self):
        return "ProcInfo({!r}, {!r}, {!r}, {!r})".format(
            self.pid, self.uid, self.stat, self.args
        )


@contextmanager
def captured_stdout(stdin=""):
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

    def __init__(self, function):
        self._function = function
        self.__doc__ = function.__doc__

    def __get__(self, obj, klass=None):
        return self._function()


def getdoc(object):
    """
    This gets a docstring if available, and cleans it, but does not look up docs in
    inheritance tree (Pre 3.5 behavior of ``inspect.getdoc``).
    """
    try:
        doc = object.__doc__
    except AttributeError:
        return None
    if not isinstance(doc, str):
        return None
    return inspect.cleandoc(doc)


def read_fd_decode_safely(fd, size=4096):
    """
    This reads a utf-8 file descriptor and returns a chunk, growing up to
    three bytes if needed to decode the character at the end.

    Returns the data and the decoded text.
    """
    data = os.read(fd.fileno(), size)
    for i in range(4):
        try:
            return data, data.decode("utf-8")
        except UnicodeDecodeError as e:
            if e.reason != "unexpected end of data":
                raise
            if i == 3:
                raise
            data += os.read(fd.fileno(), 1)
