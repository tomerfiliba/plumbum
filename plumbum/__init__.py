r"""
Plumbum Shell Combinators
-------------------------
A wrist-handy library for writing shell-like scripts in Python, that can serve
as a ``Popen`` replacement, and much more::

    >>> from plumbum.cmd import ls, grep, wc, cat
    >>> ls()
    'build.py\ndist\ndocs\nLICENSE\nplumbum\nREADME.rst\nsetup.py\ntests\ntodo.txt\n'
    >>> chain = ls["-a"] | grep["-v", "py"] | wc["-l"]
    >>> print(chain)
    /bin/ls -a | /bin/grep -v py | /usr/bin/wc -l
    >>> chain()
    '12\n'
    >>> ((ls["-a"] | grep["-v", "py"]) > "/tmp/foo.txt")()
    ''
    >>> ((cat < "/tmp/foo.txt") | wc["-l"])()
    '12\n'
    >>> from plumbum import local, FG, BG
    >>> with local.cwd("/tmp"):
    ...     (ls | wc["-l"]) & FG
    ...
    13              # printed directly to the interpreter's stdout
    >>> (ls | wc["-l"]) & BG
    <Future ['/usr/bin/wc', '-l'] (running)>
    >>> f = _
    >>> f.stdout    # will wait for the process to terminate
    '9\n'

Plumbum includes local/remote path abstraction, working directory and environment
manipulation, process execution, remote process execution over SSH, tunneling,
SCP-based upload/download, and a {arg|opt}parse replacement for the easy creation
of command-line interface (CLI) programs.

See https://plumbum.readthedocs.io for full details
"""

import sys

# Avoids a circular import error later
import plumbum.path  # noqa: F401
from plumbum.commands import (
    BG,
    ERROUT,
    FG,
    NOHUP,
    RETCODE,
    TEE,
    TF,
    CommandNotFound,
    ProcessExecutionError,
    ProcessLineTimedOut,
    ProcessTimedOut,
)
from plumbum.machines import BaseRemoteMachine, PuttyMachine, SshMachine, local
from plumbum.path import LocalPath, Path, RemotePath
from plumbum.version import version

__author__ = "Tomer Filiba (tomerfiliba@gmail.com)"
__version__ = version

__all__ = (
    "BG",
    "ERROUT",
    "FG",
    "NOHUP",
    "RETCODE",
    "TEE",
    "TF",
    "CommandNotFound",
    "ProcessExecutionError",
    "ProcessLineTimedOut",
    "ProcessTimedOut",
    "BaseRemoteMachine",
    "PuttyMachine",
    "SshMachine",
    "local",
    "LocalPath",
    "Path",
    "RemotePath",
    "__author__",
    "__version__",
    "cmd",
)

# ===================================================================================================
# Module hack: ``from plumbum.cmd import ls``
# Can be replaced by a real module with __getattr__ after Python 3.6 is dropped
# ===================================================================================================


if sys.version_info < (3, 7):
    from types import ModuleType
    from typing import List

    class LocalModule(ModuleType):
        """The module-hack that allows us to use ``from plumbum.cmd import some_program``"""

        __all__ = ()  # to make help() happy
        __package__ = __name__

        def __getattr__(self, name):
            try:
                return local[name]
            except CommandNotFound:
                raise AttributeError(name) from None

        __path__: List[str] = []
        __file__ = __file__

    cmd = LocalModule(__name__ + ".cmd", LocalModule.__doc__)
    sys.modules[cmd.__name__] = cmd
else:
    from . import cmd


def __dir__():
    "Support nice tab completion"
    return __all__
