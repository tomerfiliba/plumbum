from __future__ import with_statement
import time
import atexit
import heapq
from subprocess import Popen
from threading import Thread
from plumbum.lib import ascii, bytes, IS_WIN32, six
try:
    from queue import Queue, Empty as QueueEmpty
except ImportError:
    from Queue import Queue, Empty as QueueEmpty


if not hasattr(Popen, "kill"):
    # python 2.5 compatibility
    import os
    import sys
    import signal
    if IS_WIN32:
        import _subprocess

        def _Popen_terminate(self):
            """taken from subprocess.py of python 2.7"""
            try:
                _subprocess.TerminateProcess(self._handle, 1)
            except OSError:
                ex = sys.exc_info()[1]
                # ERROR_ACCESS_DENIED (winerror 5) is received when the
                # process already died.
                if ex.winerror != 5:
                    raise
                rc = _subprocess.GetExitCodeProcess(self._handle)
                if rc == _subprocess.STILL_ACTIVE:
                    raise
                self.returncode = rc
        
        Popen.kill = _Popen_terminate
        Popen.terminate = _Popen_terminate
    else:
        def _Popen_kill(self):
            os.kill(self.pid, signal.SIGKILL)
        def _Popen_terminate(self):
            os.kill(self.pid, signal.SIGTERM)
        def _Popen_send_signal(self, sig):
            os.kill(self.pid, sig)
        Popen.kill = _Popen_kill
        Popen.terminate = _Popen_kill
        Popen.send_signal = _Popen_send_signal

#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(EnvironmentError):
    """Represents the failure of a process. When the exit code of a terminated process does not
    match the expected result, this exception is raised by :func:`run_proc
    <plumbum.commands.run_proc>`. It contains the process' return code, stdout, and stderr, as
    well as the command line used to create the process (``argv``)
    """
    def __init__(self, argv, retcode, stdout, stderr):
        Exception.__init__(self, argv, retcode, stdout, stderr)
        self.argv = argv
        self.retcode = retcode
        if isinstance(stdout, bytes) and not isinstance(stderr, str):
            stdout = ascii(stdout)
        if isinstance(stderr, bytes) and not isinstance(stderr, str):
            stderr = ascii(stderr)
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        stdout = "\n         | ".join(self.stdout.splitlines())
        stderr = "\n         | ".join(self.stderr.splitlines())
        lines = ["Command line: %r" % (self.argv,), "Exit code: %s" % (self.retcode)]
        if stdout:
            lines.append("Stdout:  | %s" % (stdout,))
        if stderr:
            lines.append("Stderr:  | %s" % (stderr,))
        return "\n".join(lines)

class ProcessTimedOut(Exception):
    """Raises by :func:`run_proc <plumbum.commands.run_proc>` when a ``timeout`` has been
    specified and it has elapsed before the process terminated"""
    def __init__(self, msg, argv):
        Exception.__init__(self, msg, argv)
        self.argv = argv

class CommandNotFound(Exception):
    """Raised by :func:`local.which <plumbum.machines.local.LocalMachine.which>` and
    :func:`RemoteMachine.which <plumbum.machines.remote.RemoteMachine.which>` when a
    command was not found in the system's ``PATH``"""
    def __init__(self, program, path):
        Exception.__init__(self, program, path)
        self.program = program
        self.path = path

#===================================================================================================
# Timeout thread
#===================================================================================================
class MinHeap(object):
    def __init__(self, items = ()):
        self._items = list(items)
        heapq.heapify(self._items)
    def __len__(self):
        return len(self._items)
    def push(self, item):
        heapq.heappush(self._items, item)
    def pop(self):
        heapq.heappop(self._items)
    def peek(self):
        return self._items[0]

_timeout_queue = Queue()
_shutting_down = False

def _timeout_thread_func():
    waiting = MinHeap()
    try:
        while not _shutting_down:
            if waiting:
                ttk, _ = waiting.peek()
                timeout = max(0, ttk - time.time())
            else:
                timeout = None
            try:
                proc, time_to_kill = _timeout_queue.get(timeout = timeout)
                if proc is SystemExit:
                    # terminate
                    return
                waiting.push((time_to_kill, proc))
            except QueueEmpty:
                pass
            now = time.time()
            while waiting:
                ttk, proc = waiting.peek()
                if ttk > now:
                    break
                waiting.pop()
                try:
                    if proc.poll() is None:
                        proc.kill()
                        proc._timed_out = True
                except EnvironmentError:
                    pass
    except Exception:
        if _shutting_down:
            # to prevent all sorts of exceptions during interpreter shutdown
            pass
        else:
            raise

bgthd = Thread(target = _timeout_thread_func, name = "PlumbumTimeoutThread")
bgthd.setDaemon(True)
bgthd.start()

def _shutdown_bg_threads():
    global _shutting_down
    _shutting_down = True
    _timeout_queue.put((SystemExit, 0))
    # grace period
    bgthd.join(0.1)

atexit.register(_shutdown_bg_threads)

#===================================================================================================
# run_proc
#===================================================================================================
def run_proc(proc, retcode, timeout = None):
    """Waits for the given process to terminate, with the expected exit code

    :param proc: a running Popen-like object

    :param retcode: the expected return (exit) code of the process. It defaults to 0 (the
                    convention for success). If ``None``, the return code is ignored.
                    It may also be a tuple (or any object that supports ``__contains__``)
                    of expected return codes.

    :param timeout: the number of seconds (a ``float``) to allow the process to run, before
                    forcefully terminating it. If ``None``, not timeout is imposed; otherwise
                    the process is expected to terminate within that timeout value, or it will
                    be killed and :class:`ProcessTimedOut <plumbum.cli.ProcessTimedOut>`
                    will be raised

    :returns: A tuple of (return code, stdout, stderr)
    """
    if timeout is not None:
        _timeout_queue.put((proc, time.time() + timeout))
    stdout, stderr = proc.communicate()
    proc._end_time = time.time()
    if not stdout:
        stdout = six.b("")
    if not stderr:
        stderr = six.b("")
    if getattr(proc, "encoding", None):
        stdout = stdout.decode(proc.encoding, "ignore")
        stderr = stderr.decode(proc.encoding, "ignore")

    if getattr(proc, "_timed_out", False):
        raise ProcessTimedOut("Process did not terminate within %s seconds" % (timeout,),
            getattr(proc, "argv", None))

    if retcode is not None:
        if hasattr(retcode, "__contains__"):
            if proc.returncode not in retcode:
                raise ProcessExecutionError(getattr(proc, "argv", None), proc.returncode,
                    stdout, stderr)
        elif proc.returncode != retcode:
            raise ProcessExecutionError(getattr(proc, "argv", None), proc.returncode,
                stdout, stderr)
    return proc.returncode, stdout, stderr



