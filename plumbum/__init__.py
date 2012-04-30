from plumbum.base import FG, BG, ProcessExecutionError, CommandNotFound
from plumbum.localcmd import local
from plumbum.ssh import SshContext
from plumbum.path import Path
from plumbum.remotecmd import Remote
from plumbum.version import version as __version__


def rm(*paths):
    for p in paths:
        if isinstance(p, Path):
            p.delete()
        elif isinstance(p, str):
            local.path(p).delete()
        elif hasattr(p, "__iter__"):
            rm(*p)
        else:
            raise TypeError("Cannot delete %r" % (p,))
