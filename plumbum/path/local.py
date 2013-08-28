from __future__ import with_statement
import os
import sys
import glob
import shutil
import errno
import logging
from contextlib import contextmanager
from plumbum.lib import _setdoc, IS_WIN32
from plumbum.path.base import Path, FSUser
from plumbum.path.remote import RemotePath
try:
    from pwd import getpwuid, getpwnam
    from grp import getgrgid, getgrnam
except ImportError:
    def getpwuid(x):
        return (None,)
    def getgrgid(x):
        return (None,)
    def getpwnam(x):
        raise OSError("`getpwnam` not supported")
    def getgrnam(x):
        raise OSError("`getgrnam` not supported")

logger = logging.getLogger("plumbum.local")


#===================================================================================================
# Local Paths
#===================================================================================================
class LocalPath(Path):
    """The class implementing local-machine paths"""

    __slots__ = ["_path"]
    CASE_SENSITIVE = not IS_WIN32

    def __init__(self, *parts):
        if not parts:
            raise TypeError("At least one path part is require (none given)")
        if any(isinstance(path, RemotePath) for path in parts):
            raise TypeError("LocalPath cannot be constructed from %r" % (parts,))
        self._path = os.path.normpath(os.path.join(*(str(p) for p in parts)))
    def __new__(cls, *parts):
        if len(parts) == 1 and isinstance(parts[0], cls):
            return parts[0]
        return object.__new__(cls)
    def __str__(self):
        return self._path
    def _get_info(self):
        return self._path
    def __getstate__(self):
        return {"_path" : self._path}

    def _form(self, *parts):
        return LocalPath(*parts)

    @property
    @_setdoc(Path)
    def basename(self):
        return os.path.basename(str(self))

    @property
    @_setdoc(Path)
    def dirname(self):
        return LocalPath(os.path.dirname(str(self)))

    @property
    @_setdoc(Path)
    def uid(self):
        uid = self.stat().st_uid
        name = getpwuid(uid)[0]
        return FSUser(uid, name)

    @property
    @_setdoc(Path)
    def gid(self):
        gid = self.stat().st_gid
        name = getgrgid(gid)[0]
        return FSUser(gid, name)

    @_setdoc(Path)
    def join(self, *others):
        return LocalPath(self, *others)

    @_setdoc(Path)
    def list(self):
        return [self / fn for fn in os.listdir(str(self))]

    @_setdoc(Path)
    def isdir(self):
        return os.path.isdir(str(self))

    @_setdoc(Path)
    def isfile(self):
        return os.path.isfile(str(self))

    @_setdoc(Path)
    def exists(self):
        return os.path.exists(str(self))

    @_setdoc(Path)
    def stat(self):
        return os.stat(str(self))

    @_setdoc(Path)
    def glob(self, pattern):
        return [LocalPath(fn) for fn in glob.glob(str(self / pattern))]

    @_setdoc(Path)
    def delete(self):
        if not self.exists():
            return
        if self.isdir():
            shutil.rmtree(str(self))
        else:
            os.remove(str(self))

    @_setdoc(Path)
    def move(self, dst):
        if isinstance(dst, RemotePath):
            raise TypeError("Cannot move local path %s to %r" % (self, dst))
        shutil.move(str(self), str(dst))
        return LocalPath(dst)

    @_setdoc(Path)
    def copy(self, dst, override = False):
        if isinstance(dst, RemotePath):
            raise TypeError("Cannot copy local path %s to %r" % (self, dst))
        dst = LocalPath(dst)
        if override:
            dst.delete()
        if self.isdir():
            shutil.copytree(str(self), str(dst))
        else:
            shutil.copy2(str(self), str(dst))
        return dst

    @_setdoc(Path)
    def mkdir(self):
        if not self.exists():
            try:
                os.makedirs(str(self))
            except OSError:
                # directory might already exist (a race with other threads/processes)
                _, ex, _ = sys.exc_info()
                if ex.errno != errno.EEXIST:
                    raise

    @_setdoc(Path)
    def open(self, mode = "r"):
        return open(str(self), mode)

    @_setdoc(Path)
    def read(self):
        with self.open() as f:
            return f.read()

    @_setdoc(Path)
    def write(self, data):
        with self.open("w") as f:
            f.write(data)

    @_setdoc(Path)
    def chown(self, owner = None, group = None, recursive = None):
        if not hasattr(os, "chown"):
            raise OSError("os.chown() not supported")
        uid = self.uid if owner is None else (owner if isinstance(owner, int) else getpwnam(owner)[2])
        gid = self.gid if group is None else (group if isinstance(group, int) else getgrnam(group)[2])
        os.chown(str(self), uid, gid)
        if recursive or (recursive is None and self.isdir()):
            for subpath in self.walk():
                os.chown(str(subpath), uid, gid)

    @_setdoc(Path)
    def chmod(self, mode):
        if not hasattr(os, "chmod"):
            raise OSError("os.chmod() not supported")
        os.chmod(str(self), mode)

    @_setdoc(Path)
    def link(self, dst):
        if isinstance(dst, RemotePath):
            raise TypeError("Cannot create a hardlink from local path %s to %r" % (self, dst))
        if hasattr(os, "link"):
            os.link(str(self), str(dst))
        else:
            from plumbum.machines.local import local
            # windows: use mklink
            if self.isdir():
                local["cmd"]("/C", "mklink", "/D", "/H", str(dst), str(self))
            else:
                local["cmd"]("/C", "mklink", "/H", str(dst), str(self))
    @_setdoc(Path)
    def symlink(self, dst):
        if isinstance(dst, RemotePath):
            raise TypeError("Cannot create a symlink from local path %s to %r" % (self, dst))
        if hasattr(os, "symlink"):
            os.symlink(str(self), str(dst))
        else:
            from plumbum.machines.local import local
            # windows: use mklink
            if self.isdir():
                local["cmd"]("/C", "mklink", "/D", str(dst), str(self))
            else:
                local["cmd"]("/C", "mklink", str(dst), str(self))


class LocalWorkdir(LocalPath):
    """Working directory manipulator"""

    __slots__ = []
    def __init__(self):
        LocalPath.__init__(self, os.getcwd())
    def __hash__(self):
        raise TypeError("unhashable type")
    def __new__(cls):
        return object.__new__(cls)

    def chdir(self, newdir):
        """Changes the current working directory to the given one

        :param newdir: The destination director (a string or a ``LocalPath``)
        """
        if isinstance(newdir, RemotePath):
            raise TypeError("newdir cannot be %r" % (newdir,))
        logger.debug("Chdir to %s", newdir)
        os.chdir(str(newdir))
        self._path = os.path.normpath(os.getcwd())
    def getpath(self):
        """Returns the current working directory as a ``LocalPath`` object"""
        return LocalPath(self._path)
    @contextmanager
    def __call__(self, newdir):
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.

        :param newdir: The destination director (a string or a ``LocalPath``)
        """
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)


