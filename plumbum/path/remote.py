from __future__ import with_statement
import errno
from contextlib import contextmanager
from plumbum.path.base import Path, FSUser
from plumbum.lib import _setdoc, six
from plumbum.commands import shquote


class StatRes(object):
    """POSIX-like stat result"""
    def __init__(self, tup):
        self._tup = tuple(tup)
    def __getitem__(self, index):
        return self._tup[index]
    st_mode = mode = property(lambda self: self[0])
    st_ino = ino = property(lambda self: self[1])
    st_dev = dev = property(lambda self: self[2])
    st_nlink = nlink = property(lambda self: self[3])
    st_uid = uid = property(lambda self: self[4])
    st_gid = gid = property(lambda self: self[5])
    st_size = size = property(lambda self: self[6])
    st_atime = atime = property(lambda self: self[7])
    st_mtime = mtime = property(lambda self: self[8])
    st_ctime = ctime = property(lambda self: self[9])


class RemotePath(Path):
    """The class implementing remote-machine paths"""

    __slots__ = ["_path", "remote"]
    def __init__(self, remote, *parts):
        if not parts:
            raise TypeError("At least one path part is require (none given)")
        self.remote = remote
        windows = (self.remote.uname.lower() == "windows")
        normed = []
        parts = (self.remote.cwd,) + parts
        for p in parts:
            if windows:
                plist = str(p).replace("\\", "/").split("/")
            else:
                plist = str(p).split("/")
            if not plist[0]:
                plist.pop(0)
                del normed[:]
            for item in plist:
                if item == "" or item == ".":
                    continue
                if item == "..":
                    if normed:
                        normed.pop(-1)
                else:
                    normed.append(item)
        if windows:
            self.CASE_SENSITIVE = False
            self._path = "\\".join(normed)
        else:
            self._path = "/" + "/".join(normed)

    def _form(self, *parts):
        return RemotePath(self.remote, *parts)

    def __str__(self):
        return self._path

    @property
    @_setdoc(Path)
    def basename(self):
        if not "/" in str(self):
            return str(self)
        return str(self).rsplit("/", 1)[1]

    @property
    @_setdoc(Path)
    def dirname(self):
        if not "/" in str(self):
            return str(self)
        return self.__class__(self.remote, str(self).rsplit("/", 1)[0])

    @property
    @_setdoc(Path)
    def uid(self):
        uid, name = self.remote._path_getuid(self)
        return FSUser(int(uid), name)

    @property
    @_setdoc(Path)
    def gid(self):
        gid, name = self.remote._path_getgid(self)
        return FSUser(int(gid), name)

    def _get_info(self):
        return (self.remote, self._path)

    @_setdoc(Path)
    def join(self, *parts):
        return RemotePath(self.remote, self, *parts)

    @_setdoc(Path)
    def list(self):
        if not self.isdir():
            return []
        return [self.join(fn) for fn in self.remote._path_listdir(self)]

    @_setdoc(Path)
    def isdir(self):
        res = self.remote._path_stat(self)
        if not res:
            return False
        return res.text_mode == "directory"

    @_setdoc(Path)
    def isfile(self):
        res = self.remote._path_stat(self)
        if not res:
            return False
        return res.text_mode in ("regular file", "regular empty file")

    @_setdoc(Path)
    def exists(self):
        return self.remote._path_stat(self) is not None

    @_setdoc(Path)
    def stat(self):
        res = self.remote._path_stat(self)
        if res is None:
            raise OSError(errno.ENOENT)
        return res

    @_setdoc(Path)
    def glob(self, pattern):
        return [RemotePath(self.remote, m) for m in self.remote._path_glob(self, pattern)]

    @_setdoc(Path)
    def delete(self):
        if not self.exists():
            return
        self.remote._path_delete(self)

    @_setdoc(Path)
    def move(self, dst):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, six.string_types):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine), "
                "got %r" % (dst,))
        self.remote._path_move(self, dst)

    @_setdoc(Path)
    def copy(self, dst, override = False):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, six.string_types):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine), "
                "got %r" % (dst,))
        if override:
            if isinstance(dst, six.string_types):
                dst = RemotePath(self.remote, dst)
            dst.remove()
        self.remote._path_copy(self, dst)

    @_setdoc(Path)
    def mkdir(self):
        self.remote._path_mkdir(self)

    @_setdoc(Path)
    def read(self):
        return self.remote._path_read(self)
    @_setdoc(Path)
    def write(self, data):
        self.remote._path_write(self, data)

    @_setdoc(Path)
    def chown(self, owner = None, group = None, recursive = None):
        self.remote._path_chown(self, owner, group, self.isdir() if recursive is None else recursive)
    @_setdoc(Path)
    def chmod(self, mode):
        self.remote._path_chmod(mode, self)

    @_setdoc(Path)
    def link(self, dst):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, six.string_types):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine), "
                "got %r" % (dst,))
        self.remote._path_link(self, dst, False)

    @_setdoc(Path)
    def symlink(self, dst):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, six.string_types):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine), "
                "got %r" % (dst,))
        self.remote._path_link(self, dst, True)


class RemoteWorkdir(RemotePath):
    """Remote working directory manipulator"""

    def __init__(self, remote):
        self.remote = remote
        self._path = self.remote._session.run("pwd")[1].strip()
    def __hash__(self):
        raise TypeError("unhashable type")

    def chdir(self, newdir):
        """Changes the current working directory to the given one"""
        self.remote._session.run("cd %s" % (shquote(newdir),))
        self._path = self.remote._session.run("pwd")[1].strip()

    def getpath(self):
        """Returns the current working directory as a
        `remote path <plumbum.path.remote.RemotePath>` object"""
        return RemotePath(self.remote, self)

    @contextmanager
    def __call__(self, newdir):
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.

        :param newdir: The destination director (a string or a
                       :class:`RemotePath <plumbum.path.remote.RemotePath>`)
        """
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)



