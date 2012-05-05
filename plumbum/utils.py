from __future__ import with_statement
from plumbum.local_machine import local
from plumbum.path import Path


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
    if src._location == dst._location:
        src.move(dst)
    else:
        cp(src, dst)
        rm(src)

def cp(src, dst):
    if not isinstance(src, Path):
        src = local.path(src)
    if not isinstance(dst, Path):
        dst = local.path(dst)
    if src._location == dst._location:
        src.copy(dst)
    elif src._location == LocalPathLocation:
        dst._location.sshctx.upload(src, dst)
    elif dst._location == LocalPathLocation:
        dst._location.sshctx.download(src, dst)
    else:
        with local.mktemp() as tmp:
            cp(src, tmp)
            cp(tmp, dst)







