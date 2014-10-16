from __future__ import with_statement
from contextlib import contextmanager

from plumbum.machines import LocalMachine, BaseRemoteMachine
from plumbum.machines.session import ShellSession
from plumbum.commands.base import BaseCommand


class InvalidType(Exception):
    """Raised when parameter given is not the expected plumbum type"""


def flatten(seq, expected_types):
    for m in seq:
        if hasattr(m, "__iter__"):
            for m2 in flatten(m, expected_types):
                yield m2
        elif not isinstance(m, expected_types):
            raise InvalidType("%r" % m)
        else:
            yield m


def delegated(cls, fname, list_type=list):
    def method(self, *args, **kwargs):
        return list_type(getattr(m, fname)(*args, **kwargs) for m in self)
    method.__name__ = fname
    method.__doc__ = getattr(cls, fname).__doc__
    return method


class MultiProxy(object):

    ELEMENT_CLASS = None

    def __init__(self, *items):
        self._items = list(flatten(items, self.ELEMENT_CLASS))

    def __iter__(self):
        return iter(self._items)

    def __add__(self, other):
        return self.__class__(self._items, other)

    def __nonzero__(self):
        return bool(self._items)

    def __len__(self):
        return len(self._items)


class MultiCommand(MultiProxy):

    ELEMENT_CLASS = BaseCommand

    def __getitem__(self, args):
        return self.__class__(cmd[args] for cmd in self)

    def run(self, *args, **kwargs):
        with nested(*(command.bgrun(*args, **kwargs) for command in self)) as popens:
            return [p.run() for p in popens]

    def __call__(self, *args, **kwargs):
        return [ret[1] for ret in self.run(args, **kwargs)]


class MultiShellSession(MultiProxy):

    ELEMENT_CLASS = ShellSession

    alive = delegated(ShellSession,"alive")
    close = delegated(ShellSession,"close")
    popen = delegated(ShellSession,"popen")
    run = delegated(ShellSession,"run")


class MultiMachine(MultiProxy):

    ELEMENT_CLASS = (LocalMachine, BaseRemoteMachine)

    def filter(self, pred):
        return self.__class__(filter(pred, self))

    def unique(self):
        return self.__class__(set(self))

    def __contains__(self, cmd):
        try:
            self[cmd]
        except CommandNotFound:
            return False
        else:
            return True

    __getitem__ = delegated(BaseRemoteMachine, "__getitem__", MultiCommand)
    list_processes = delegated(BaseRemoteMachine, "list_processes")
    pgrep = delegated(BaseRemoteMachine, "pgrep")
    which = delegated(BaseRemoteMachine, "which")
    session = delegated(BaseRemoteMachine, "session", MultiShellSession)

    @property
    def python(self):
        return MultiCommand(m.python for m in self)



try:
    from contextlib import nested
except ImportError:
    nested = None

if not nested:
    try:
        from contextlib import ExitStack
    except ImportError:
        nested = None
    else:
        @contextmanager
        def nested(*managers):
            with ExitStack() as stack:
                yield [stack.enter_context(ctx) for ctx in managers]

if not nested:
    # we're probably on python 3.2, so we'll need to redefine the deprecated 'nested' function

    import sys

    @contextmanager
    def nested(*managers):
        exits = []
        vars = []
        exc = (None, None, None)
        try:
            for mgr in managers:
                exit, enter = mgr.__exit__, mgr.__enter__
                vars.append(enter())
                exits.append(exit)
            yield vars
        except:
            exc = sys.exc_info()
        finally:
            while exits:
                exit = exits.pop()
                try:
                    if exit(*exc):
                        exc = (None, None, None)
                except:
                    exc = sys.exc_info()
            if exc != (None, None, None):
                raise exc[0], exc[1], exc[2]
