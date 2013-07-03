from __future__ import with_statement
import os
import six
import threading
import sys
from contextlib import contextmanager
from plumbum.local_machine import local

try:
    import thread
except ImportError:
    pass
else:
    threading.get_ident = thread.get_ident


try:
    import fcntl
    
    @contextmanager
    def locked_file(fileno, blocking = True):
        fcntl.flock(fileno, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(fileno, fcntl.LOCK_UN)

except ImportError:
    import msvcrt
    from pywintypes import error as WinError
    from win32file import LockFileEx, UnlockFile, OVERLAPPED
    from win32con import LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY
    
    @contextmanager
    def locked_file(fileno, blocking = True):
        hndl = msvcrt.get_osfhandle(fileno)
        try:
            LockFileEx(hndl, LOCKFILE_EXCLUSIVE_LOCK | (0 if blocking else LOCKFILE_FAIL_IMMEDIATELY), 
                0xffffffff, 0xffffffff, OVERLAPPED())
        except WinError:
            _, ex, _ = sys.exc_info()
            raise WindowsError(*ex.args)
        try:
            yield
        finally:
            UnlockFile(hndl, 0, 0, 0xffffffff, 0xffffffff)


class AtomicFile(object):
    CHUNK_SIZE = 32 * 1024
    
    def __init__(self, filename, ignore_deletion = False):
        self._path = local.path(filename)
        self._ignore_deletion = ignore_deletion
        self._thdlock = threading.Lock()
        self._owned_by = None
        self._fileobj = None
        self.reopen()

    def __repr__(self):
        return "<AtomicFile: %s>" % (self._path,) if self._fileobj else "<AtomicFile: closed>"

    def __del__(self):
        self.close()
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    
    def close(self):
        if self._fileobj is not None:
            self._fileobj.close()
            self._fileobj = None
    
    def reopen(self):
        self.close()
        self._fileobj = os.fdopen(os.open(str(self._path), os.O_CREAT | os.O_RDWR, 384), "r+", 0)

    @contextmanager
    def locked(self, blocking = True):
        if self._owned_by == threading.get_ident():
            yield
            return
        with self._thdlock:
            with locked_file(self._fileobj.fileno(), blocking):
                if not self._path.exists() and not self._ignore_deletion:
                    raise ValueError("Atomic file removed from filesystem")
                self._owned_by = threading.get_ident()
                try:
                    yield
                finally:
                    self._owned_by = None

    def delete(self):
        with self.locked():
            self._path.delete()

    def _read_all(self):
        self._fileobj.seek(0)
        data = []
        while True:
            buf = self._fileobj.read(self.CHUNK_SIZE)
            data.append(buf)
            if len(buf) < self.CHUNK_SIZE:
                break
        return six.b("").join(data)
        
    def read_atomic(self):
        with self.locked():
            return self._read_all()

    def read_shared(self):
        return self._read_all()

    def write_atomic(self, data):
        with self.locked():
            self._fileobj.seek(0)
            while data:
                chunk = data[:self.CHUNK_SIZE]
                self._fileobj.write(chunk)
                data = data[len(chunk):]
            self._fileobj.flush()
            self._fileobj.truncate()


class AtomicCounterFile(object):
    def __init__(self, atomicfile):
        self.atomicfile = atomicfile

    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self.atomicfile.close()

    @classmethod
    def open(cls, filename):
        return cls(AtomicFile(filename))

    def next(self):
        with self.atomicfile.locked():
            curr = self.atomicfile.read_atomic().decode("utf8")
            if not curr:
                curr = 0
            else:
                curr = int(curr)
            self.atomicfile.write_atomic(str(curr + 1).encode("utf8"))
            return curr


class PidFileTaken(SystemExit):
    pass


@contextmanager
def pid_file(filename):
    with AtomicFile(filename) as af:
        got_lock = False
        try:
            with af.locked(blocking = False):
                got_lock = True
                af.write_atomic(str(os.getpid()).encode("utf8"))
                yield
        except (IOError, OSError):
            if got_lock:
                raise
            else:
                try:
                    pid = af.read_shared().strip().decode("utf8")
                except (IOError, OSError):
                    pid = "Unknown"
                raise PidFileTaken("PID file %r taken by %s" % (filename, pid))




