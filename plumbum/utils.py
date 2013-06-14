from __future__ import with_statement
import six
import sys
import os
import subprocess
import signal
import errno
import time
import traceback
from plumbum.path import Path
from plumbum.local_machine import local, LocalPath
from plumbum.commands import ProcessExecutionError


def delete(*paths):
    """Deletes the given paths. The arguments can be either strings,
    :class:`local paths <plumbum.local_machine.LocalPath>`,
    :class:`remote paths <plumbum.remote_machine.RemotePath>`, or iterables of such.
    No error is raised if any of the paths does not exist (it is silently ignored)
    """
    for p in paths:
        if isinstance(p, Path):
            p.delete()
        elif isinstance(p, six.string_types):
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

def _posix_daemonize(command, cwd = "/"):
    """run ``command`` as a daemon: fork a child process to setpid, redirect std handles to /dev/null, 
    umask, close all fds, chdir to ``cwd``, then fork and exec ``command``. Returns a ``Popen`` process that
    can be used to poll/wait for the executed command (but keep in mind that you cannot access std handles) 
    """
    MAX_SIZE = 16384
    rfd, wfd = os.pipe()
    argv = command.formulate()
    firstpid = os.fork()
    if firstpid == 0:
        # first child: become session leader,
        os.close(rfd)
        rc = 0
        try:
            os.setsid()
            os.umask(0)
            stdin = open(os.devnull, "r")
            stdout = open(os.devnull, "w")
            stderr = open(os.devnull, "w")
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            proc = command.popen(cwd = cwd, close_fds = True, stdin = stdin.fileno(), 
                stdout = stdout.fileno(), stderr = stderr.fileno())
            os.write(wfd, str(proc.pid))
        except:
            rc = 1
            tbtext = "".join(traceback.format_exception(*sys.exc_info()))[-MAX_SIZE:]
            os.write(wfd, tbtext)
        finally:
            os.close(wfd)
            os._exit(rc)
    else:
        # wait for first child to die
        os.close(wfd)
        _, rc = os.waitpid(firstpid, 0)
        output = os.read(rfd, MAX_SIZE)
        if rc == 0 and output.isdigit():
            secondpid = int(output)
        else:
            raise ProcessExecutionError(argv, rc, "", output)
        proc = subprocess.Popen.__new__(subprocess.Popen)
        proc._child_created = True
        proc.returncode = None
        proc.stdout = None
        proc.stdin = None
        proc.stderr = None
        proc.pid = secondpid
        proc.universal_newlines = False
        proc._input = None
        proc._communication_started = False
        proc.args = argv
        proc.argv = argv
        
        def poll(self = proc):
            if self.returncode is None:
                try:
                    os.kill(self.pid, 0)
                except OSError:
                    ex = sys.exc_info()[1]
                    if ex.errno == errno.ESRCH:
                        # process does not exist
                        self.returncode = 0
                    else:
                        raise
            return self.returncode
        
        def wait(self = proc):
            while self.returncode is None:
                if self.poll() is None:
                    time.sleep(0.5)
            return proc.returncode                
        
        proc.poll = poll
        proc.wait = wait
        return proc


def _win32_daemonize(command, cwd = "/"):
    """run ``command`` as a "windows daemon": detach from controlling console and create a new process group.
    This means that the command will not receive console events and would survive its parent's termination. 
    Returns a ``Popen`` object.
    """
    DETACHED_PROCESS = 0x00000008
    stdin = open(os.devnull, "r")
    stdout = open(os.devnull, "w")
    stderr = open(os.devnull, "w")
    return command.popen(cwd = cwd, stdin = stdin.fileno(), stdout = stdout.fileno(), stderr = stderr.fileno(), 
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS)


if sys.platform == "win32":
    daemonize = _win32_daemonize
else:
    daemonize = _posix_daemonize


