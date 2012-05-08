from __future__ import with_statement
from plumbum.path import Path
from plumbum.local_machine import local, LocalPath


def delete(*paths):
    """Deletes the given paths. The arguments can be either strings, 
    :class:`local paths <plumbum.local_machine.LocalPath>`, 
    :class:`remote paths <plumbum.remote_machine.RemotePath>`, or iterables of such.
    No error is raised if any of the paths does not exist (it is silently ignored)
    """
    for p in paths:
        if isinstance(p, Path):
            p.delete()
        elif isinstance(p, str):
            local.path(p).delete()
        elif hasattr(p, "__iter__"):
            delete(*p)
        else:
            raise TypeError("Cannot delete %r" % (p,))

def _move(src, dst):
    ret = copy(src, dst)
    delete(src)
    return ret

def move(src, dst):
    """Moves the source path onto the destination path; ``src`` and ``dst`` can be either
    strings, :class:`LocalPaths <plumbum.local_machine.LocalPath>` or 
    :class:`RemotePath <plumbum.remote_machine.RemotePath>`; any combination of the three will 
    work.
    """
    if not isinstance(src, Path):
        src = local.path(src)
    if not isinstance(dst, Path):
        dst = local.path(dst)
    
    if isinstance(src, LocalPath):
        if isinstance(dst, LocalPath):
            return src.move(dst)
        else:
            return _move(src, dst)
    else:
        if isinstance(dst, LocalPath):
            return _move(src, dst)
        elif src.remote == dst.remote:
            return src.move(dst)
        else:
            return _move(src, dst)

def copy(src, dst):
    """
    Copy (recursively) the source path onto the destination path; ``src`` and ``dst`` can be 
    either strings, :class:`LocalPaths <plumbum.local_machine.LocalPath>` or 
    :class:`RemotePath <plumbum.remote_machine.RemotePath>`; any combination of the three will 
    work. 
    """
    if not isinstance(src, Path):
        src = local.path(src)
    if not isinstance(dst, Path):
        dst = local.path(dst)
    
    if isinstance(src, LocalPath):
        if isinstance(dst, LocalPath):
            return src.copy(dst)
        else:
            dst.remote.upload(src, dst)
            return dst
    else:
        if isinstance(dst, LocalPath):
            src.remote.download(src, dst)
            return dst
        elif src.remote == dst.remote:
            return src.copy(dst)
        else:
            with local.tempdir() as tmp:
                copy(src, tmp)
                copy(tmp / src.basename, dst)
            return dst



