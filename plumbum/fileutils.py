import os
import six
import thread
import sys
from contextlib import contextmanager

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
    
    def __init__(self, filename):
        self._thdlock = thread.allocate_lock()
        self._owned_by = None
        self.fileobj = os.fdopen(os.open(filename, os.O_CREAT | os.O_RDWR, 384), "r+")
        self.fileobj.seek(0)
    
    def __repr__(self):
        return "<AtomicFile %r>" % (self.fileobj,)
    
    def __del__(self):
        self.close()
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    
    def close(self):
        if self.fileobj is not None:
            self.fileobj.close()
            self.fileobj = None
    
    @contextmanager
    def locked(self, blocking = True):
        if self._owned_by == thread.get_ident():
            yield
            return
        with self._thdlock:
            with locked_file(self.fileobj.fileno(), blocking):
                self._owned_by = thread.get_ident()
                self.fileobj.seek(0)
                try:
                    yield
                finally:
                    self._owned_by = None
    
    def write_atomic(self, data):
        with self.locked():
            while data:
                chunk = data[:self.CHUNK_SIZE]
                self.fileobj.write(chunk)
                data = data[len(chunk):]
            self.fileobj.truncate()
    
    def read_atomic(self):
        with self.locked():
            data = []
            while True:
                buf = self.fileobj.read(self.CHUNK_SIZE)
                if not buf:
                    break
                data.append(buf)
            return six.b("").join(buf)


class PidFileTaken(SystemExit):
    pass

@contextmanager
def pid_file(filename):
    with AtomicFile(filename) as af:
        got_lock = False
        try:
            with af.locked(blocking = False):
                got_lock = True
                yield
        except (IOError, OSError):
            if got_lock:
                raise
            else:
                raise PidFileTaken(filename)


if __name__ == "__main__":
    af = AtomicFile("tmp.txt")
    with af.locked():
        af.write_atomic("hello world")
        try:
            with pid_file("tmp.txt"):
                pass
        except PidFileTaken:
            print "taken"


