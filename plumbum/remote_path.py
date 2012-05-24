import os
import errno
from tempfile import NamedTemporaryFile
from plumbum.path import Path
from plumbum.lib import _setdoc

class RemotePath(Path):
    """The class implementing remote-machine paths"""

    __slots__ = ["_path", "remote"]
    def __init__(self, remote, *parts):
        self.remote = remote
        normed = []
        parts = (self.remote.cwd,) + parts
        for p in parts:
            plist = str(p).replace("\\", "/").split("/")
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
        return str(self).rsplit("/", 1)[0]

    def _get_info(self):
        return (self.remote, self._path)

    @_setdoc(Path)
    def join(self, *parts):
        return RemotePath(self.remote, self, *parts)

    @_setdoc(Path)
    def list(self):
        if not self.isdir():
            return []
        files = self.remote._session.run("ls -a %s" % (self,))[1].splitlines()
        files.remove(".")
        files.remove("..")
        return [self.join(fn) for fn in files]

    @_setdoc(Path)
    def isdir(self):
        res = self._stat()
        if not res:
            return False
        return res[0] in ("directory")

    @_setdoc(Path)
    def isfile(self):
        res = self._stat()
        if not res:
            return False
        return res[0] in ("regular file", "regular empty file")

    @_setdoc(Path)
    def exists(self):
        return self._stat() is not None

    def _stat(self):
        rc, out, _ = self.remote._session.run(
            "stat -c '%F,%f,%i,%d,%h,%u,%g,%s,%X,%Y,%Z' " + shquote(self), retcode = None)
        if rc != 0:
            return None
        statres = out.strip().split(",")
        mode = statres.pop(0).lower()
        return mode, os.stat_result(statres)

    @_setdoc(Path)
    def stat(self):
        res = self._stat()
        if res is None:
            raise OSError(errno.ENOENT)
        return res[1]

    @_setdoc(Path)
    def glob(self, pattern):
        matches = self.remote._session.run("for fn in %s/%s; do echo $fn; done" % (self, pattern))[1].splitlines()
        if len(matches) == 1 and not self._stat(matches[0]):
            return [] # pattern expansion failed
        return [RemotePath(self.remote, m) for m in matches]

    @_setdoc(Path)
    def delete(self):
        if not self.exists():
            return
        self.remote._session.run("rm -rf %s" % (shquote(self),))

    @_setdoc(Path)
    def move(self, dst):
        if isinstance(dst, RemotePath) and dst.remote is not self.remote:
            raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine)")
        self.remote._session.run("mv %s %s" % (shquote(self), shquote(dst)))

    @_setdoc(Path)
    def copy(self, dst, override = False):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine)", repr(dst))
        if override:
            if isinstance(dst, str):
                dst = RemotePath(self.remote, dst)
            dst.remove()
        self.remote._session.run("cp -r %s %s" % (shquote(self), shquote(dst)))

    @_setdoc(Path)
    def mkdir(self):
        self.remote._session.run("mkdir -p %s" % (shquote(self),))

    @_setdoc(Path)
    def read(self):
        return self.remote["cat"](self)

    @_setdoc(Path)
    def write(self, data):
        if self.remote.encoding and isinstance(data, str) and not isinstance(data, bytes):
            data = data.encode(self.remote.encoding)
        with NamedTemporaryFile() as f:
            f.write(data)
            f.flush()
            f.seek(0)
            self.remote.upload(f.name, self)
