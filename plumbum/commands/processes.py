import atexit
import heapq
import time
from queue import Empty as QueueEmpty
from queue import Queue
from threading import Thread

from plumbum.lib import IS_WIN32


# ===================================================================================================
# utility functions
# ===================================================================================================
def _check_process(proc, retcode, timeout, stdout, stderr):
    proc.verify(retcode, timeout, stdout, stderr)
    return proc.returncode, stdout, stderr


def _iter_lines_posix(proc, decode, linesize, line_timeout=None):
    from selectors import EVENT_READ, DefaultSelector

    # Python 3.4+ implementation
    def selector():
        sel = DefaultSelector()
        sel.register(proc.stdout, EVENT_READ, 0)
        sel.register(proc.stderr, EVENT_READ, 1)
        while True:
            ready = sel.select(line_timeout)
            if not ready and line_timeout:
                raise ProcessLineTimedOut(
                    "popen line timeout expired",
                    getattr(proc, "argv", None),
                    getattr(proc, "machine", None),
                )
            for key, _mask in ready:
                yield key.data, decode(key.fileobj.readline(linesize))

    for ret in selector():
        yield ret
        if proc.poll() is not None:
            break
    for line in proc.stdout:
        yield 0, decode(line)
    for line in proc.stderr:
        yield 1, decode(line)


def _iter_lines_win32(proc, decode, linesize, line_timeout=None):
    class Piper(Thread):
        def __init__(self, fd, pipe):
            super().__init__(name=f"PlumbumPiper{fd}Thread")
            self.pipe = pipe
            self.fd = fd
            self.empty = False
            self.daemon = True
            super().start()

        def read_from_pipe(self):
            return self.pipe.readline(linesize)

        def run(self):
            for line in iter(self.read_from_pipe, b""):
                queue.put((self.fd, decode(line)))
            # self.pipe.close()

    if line_timeout is None:
        line_timeout = float("inf")
    queue = Queue()
    pipers = [Piper(0, proc.stdout), Piper(1, proc.stderr)]
    last_line_ts = time.time()
    empty = True
    while True:
        try:
            yield queue.get_nowait()
            last_line_ts = time.time()
            empty = False
        except QueueEmpty:
            empty = True
        if time.time() - last_line_ts > line_timeout:
            raise ProcessLineTimedOut(
                "popen line timeout expired",
                getattr(proc, "argv", None),
                getattr(proc, "machine", None),
            )
        if proc.poll() is not None:
            break
        if empty:
            time.sleep(0.1)

    for piper in pipers:
        piper.join()

    while True:
        try:
            yield queue.get_nowait()
        except QueueEmpty:
            break


if IS_WIN32:
    _iter_lines = _iter_lines_win32
else:
    _iter_lines = _iter_lines_posix


# ===================================================================================================
# Exceptions
# ===================================================================================================
class ProcessExecutionError(EnvironmentError):
    """Represents the failure of a process. When the exit code of a terminated process does not
    match the expected result, this exception is raised by :func:`run_proc
    <plumbum.commands.run_proc>`. It contains the process' return code, stdout, and stderr, as
    well as the command line used to create the process (``argv``)
    """

    def __init__(self, argv, retcode, stdout, stderr, message=None, host=None):

        # we can't use 'super' here since EnvironmentError only keeps the first 2 args,
        # which leads to failuring in loading this object from a pickle.dumps.
        Exception.__init__(self, argv, retcode, stdout, stderr)

        self.message = message
        self.host = host
        self.argv = argv
        self.retcode = retcode
        if isinstance(stdout, bytes):
            stdout = ascii(stdout)
        if isinstance(stderr, bytes):
            stderr = ascii(stderr)
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        # avoid an import cycle
        from plumbum.commands.base import shquote_list

        stdout = "\n              | ".join(str(self.stdout).splitlines())
        stderr = "\n              | ".join(str(self.stderr).splitlines())
        cmd = " ".join(shquote_list(self.argv))
        lines = []
        if self.message:
            lines = [self.message, "\nReturn code:  | ", str(self.retcode)]
        else:
            lines = ["Unexpected exit code: ", str(self.retcode)]
        cmd = "\n              | ".join(cmd.splitlines())
        lines += ["\nCommand line: | ", cmd]
        if self.host:
            lines += ["\nHost:         | ", self.host]
        if stdout:
            lines += ["\nStdout:       | ", stdout]
        if stderr:
            lines += ["\nStderr:       | ", stderr]
        return "".join(lines)


class ProcessTimedOut(Exception):
    """Raises by :func:`run_proc <plumbum.commands.run_proc>` when a ``timeout`` has been
    specified and it has elapsed before the process terminated"""

    def __init__(self, msg, argv):
        Exception.__init__(self, msg, argv)
        self.argv = argv


class ProcessLineTimedOut(Exception):
    """Raises by :func:`iter_lines <plumbum.commands.iter_lines>` when a ``line_timeout`` has been
    specified and it has elapsed before the process yielded another line"""

    def __init__(self, msg, argv, machine):
        Exception.__init__(self, msg, argv, machine)
        self.argv = argv
        self.machine = machine


class CommandNotFound(AttributeError):
    """Raised by :func:`local.which <plumbum.machines.local.LocalMachine.which>` and
    :func:`RemoteMachine.which <plumbum.machines.remote.RemoteMachine.which>` when a
    command was not found in the system's ``PATH``"""

    def __init__(self, program, path):
        super().__init__(self, program, path)
        self.program = program
        self.path = path


# ===================================================================================================
# Timeout thread
# ===================================================================================================
class MinHeap:
    def __init__(self, items=()):
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


_timeout_queue = Queue()  # type: ignore[var-annotated]
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
                proc, time_to_kill = _timeout_queue.get(timeout=timeout)
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
                except OSError:
                    pass
    except Exception:
        if _shutting_down:
            # to prevent all sorts of exceptions during interpreter shutdown
            pass
        else:
            raise


bgthd = Thread(target=_timeout_thread_func, name="PlumbumTimeoutThread")
bgthd.daemon = True
bgthd.start()


def _register_proc_timeout(proc, timeout):
    if timeout is not None:
        _timeout_queue.put((proc, time.time() + timeout))


def _shutdown_bg_threads():
    global _shutting_down  # pylint: disable=global-statement
    _shutting_down = True
    # Make sure this still exists (don't throw error in atexit!)
    if _timeout_queue:
        _timeout_queue.put((SystemExit, 0))
        # grace period
        bgthd.join(0.1)


atexit.register(_shutdown_bg_threads)


# ===================================================================================================
# run_proc
# ===================================================================================================
def run_proc(proc, retcode, timeout=None):
    """Waits for the given process to terminate, with the expected exit code

    :param proc: a running Popen-like object, with all the expected methods.

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
    _register_proc_timeout(proc, timeout)
    stdout, stderr = proc.communicate()
    proc._end_time = time.time()
    if not stdout:
        stdout = b""
    if not stderr:
        stderr = b""
    if getattr(proc, "custom_encoding", None):
        stdout = stdout.decode(proc.custom_encoding, "ignore")
        stderr = stderr.decode(proc.custom_encoding, "ignore")

    return _check_process(proc, retcode, timeout, stdout, stderr)


# ===================================================================================================
# iter_lines
# ===================================================================================================

BY_POSITION = object()
BY_TYPE = object()
DEFAULT_ITER_LINES_MODE = BY_POSITION
DEFAULT_BUFFER_SIZE = _INFINITE = float("inf")


def iter_lines(
    proc,
    retcode=0,
    timeout=None,
    linesize=-1,
    line_timeout=None,
    buffer_size=None,
    mode=None,
    _iter_lines=_iter_lines,
):
    """Runs the given process (equivalent to run_proc()) and yields a tuples of (out, err) line pairs.
    If the exit code of the process does not match the expected one, :class:`ProcessExecutionError
    <plumbum.commands.ProcessExecutionError>` is raised.

    :param retcode: The expected return code of this process (defaults to 0).
                    In order to disable exit-code validation, pass ``None``. It may also
                    be a tuple (or any iterable) of expected exit codes.

    :param timeout: The maximal amount of time (in seconds) to allow the process to run.
                    ``None`` means no timeout is imposed; otherwise, if the process hasn't
                    terminated after that many seconds, the process will be forcefully
                    terminated an exception will be raised

    :param linesize: Maximum number of characters to read from stdout/stderr at each iteration.
                    ``-1`` (default) reads until a b'\\n' is encountered.

    :param line_timeout: The maximal amount of time (in seconds) to allow between consecutive lines in either stream.
                    Raise an :class:`ProcessLineTimedOut <plumbum.commands.ProcessLineTimedOut>` if the timeout has
                    been reached. ``None`` means no timeout is imposed.

    :param buffer_size: Maximum number of lines to keep in the stdout/stderr buffers, in case of a ProcessExecutionError.
                    Default is ``None``, which defaults to DEFAULT_BUFFER_SIZE (which is infinite by default).
                    ``0`` will disable bufferring completely.

    :param mode: Controls what the generator yields. Defaults to DEFAULT_ITER_LINES_MODE (which is BY_POSITION by default)
                - BY_POSITION (default): yields ``(out, err)`` line tuples, where either item may be ``None``
                - BY_TYPE: yields ``(fd, line)`` tuples, where ``fd`` is 1 (stdout) or 2 (stderr)

    :returns: An iterator of (out, err) line tuples.
    """
    if mode is None:
        mode = DEFAULT_ITER_LINES_MODE

    if buffer_size is None:
        buffer_size = DEFAULT_BUFFER_SIZE
    buffer_size: int

    assert mode in (BY_POSITION, BY_TYPE)

    encoding = getattr(proc, "custom_encoding", None) or "utf-8"
    decode = lambda s: s.decode(encoding, errors="replace").rstrip()

    _register_proc_timeout(proc, timeout)

    buffers = [[], []]
    for t, line in _iter_lines(proc, decode, linesize, line_timeout):

        # verify that the proc hasn't timed out yet
        proc.verify(timeout=timeout, retcode=None, stdout=None, stderr=None)

        buffer = buffers[t]
        if buffer_size > 0:
            buffer.append(line)
            if buffer_size < _INFINITE:
                del buffer[:-buffer_size]

        if mode is BY_POSITION:
            ret = [None, None]
            ret[t] = line
            yield tuple(ret)
        elif mode is BY_TYPE:
            yield (t + 1), line  # 1=stdout, 2=stderr

    # this will take care of checking return code and timeouts
    _check_process(proc, retcode, timeout, *("\n".join(s) + "\n" for s in buffers))
