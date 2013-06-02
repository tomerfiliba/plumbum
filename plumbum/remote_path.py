from __future__ import with_statement
import errno
import six
from plumbum.path import Path, FSUser
from plumbum.lib import _setdoc


class RemotePath(Path):
    """The class implementing remote-machine paths"""

    __slots__ = ["_path", "remote"]
    def __init__(self, remote, *parts):
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





