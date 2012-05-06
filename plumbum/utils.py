from __future__ import with_statement
from plumbum.path import Path
from plumbum.local_machine import local, LocalPath


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

def mv(src, dst):
    if not isinstance(src, Path):
        src = local.path(src)
    if not isinstance(dst, Path):
        dst = local.path(dst)
    if isinstance(src, LocalPath):
        if isinstance(dst, LocalPath):
            src.move(dst)
        else:
            cp(src, dst)
            rm(src)
    else:
        if isinstance(dst, LocalPath):
            cp(src, dst)
            rm(src)
        elif src.remote == dst.remote:
            src.move(dst)
        else:
            cp(src, dst)
            rm(src)

def cp(src, dst):
    """
    Copy (recursively) ``src`` into ``dst``. Here, ``src`` and ``dst`` can be strings or any paths
    (local or remote ones), the function will take care of the details.
    """
    if not isinstance(src, Path):
        src = local.path(src)
    if not isinstance(dst, Path):
        dst = local.path(dst)
    if isinstance(src, LocalPath):
        if isinstance(dst, LocalPath):
            src.copy(dst)
        else:
            dst.remote.upload(src, dst)
    else:
        if isinstance(dst, LocalPath):
            src.remote.dowload(src, dst)
        elif src.remote == dst.remote:
            src.copy(dst)
        else:
            with local.tempdir() as tmp:
                cp(src, tmp)
                cp(tmp, dst)


