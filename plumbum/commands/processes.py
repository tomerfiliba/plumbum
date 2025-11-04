from __future__ import annotations

import atexit
import contextlib
import enum
import heapq
import sys
import time
import typing
from queue import Empty as QueueEmpty
from queue import Queue
from threading import Thread
from typing import Any

from plumbum.lib import IS_WIN32

if typing.TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable, Container, Generator, Sequence
    from typing import IO, Literal


# ===================================================================================================
# utility functions
# ===================================================================================================
def _check_process(
    proc: subprocess.Popen[str],
    retcode: int | Container[int] | None,
    timeout: float | None,
    stdout: str,
    stderr: str,
) -> tuple[int, str, str]:
    proc.verify(retcode, timeout, stdout, stderr)  # type: ignore[attr-defined]
    return proc.returncode, stdout, stderr


def _get_piped_streams(proc: subprocess.Popen[Any] | None) -> list[tuple[int, IO[Any]]]:
    """Get a list of all valid standard streams for proc that were opened with PIPE option.

    If proc was started from a Pipeline command, this function assumes it will have a
    "srcproc" member pointing to the previous command in the pipeline. That link will
    be used to traverse all started processes started from the pipeline, the list will
    include stdout/stderr streams opened as PIPE for all commands in the pipeline.
    If that was not the case, some processes could write to pipes no one reads from
    which would result in process stalling after the pipe's buffer is filled.

    Streams that were closed (because they were redirected to the input of a subsequent command)
    are not included in the result
    """
    streams = []

    def add_stream(type_: int, stream: IO[Any] | None) -> None:
        if stream is None or stream.closed:
            return
        streams.append((type_, stream))

    while proc:
        add_stream(1, proc.stderr)
        add_stream(0, proc.stdout)
        proc = getattr(proc, "srcproc", None)

    return streams


def _iter_lines_posix(
    proc: subprocess.Popen[bytes],
    decode: Callable[[bytes], str],
    linesize: int,
    line_timeout: float | None = None,
) -> Generator[tuple[int, str], None, None]:
    from selectors import EVENT_READ, DefaultSelector

    streams = _get_piped_streams(proc)

    # Python 3.4+ implementation
    def selector() -> Generator[tuple[int, str], None, None]:
        sel = DefaultSelector()
        for stream_type, stream in streams:
            sel.register(stream, EVENT_READ, stream_type)
        while True:
            ready = sel.select(line_timeout)
            if not ready and line_timeout:
                raise ProcessLineTimedOut(
                    "popen line timeout expired",
                    getattr(proc, "argv", None),
                    getattr(proc, "machine", None),
                )
            for key, _mask in ready:
                # We pass the stream to the selector, so we get a stream out
                yield key.data, decode(key.fileobj.readline(linesize))  # type: ignore[union-attr]

    for ret in selector():
        yield ret
        if proc.poll() is not None:
            break
    for stream_type, stream in streams:
        for line in stream:
            yield stream_type, decode(line)


def _iter_lines_win32(
    proc: subprocess.Popen[bytes],
    decode: Callable[[bytes], str],
    linesize: int,
    line_timeout: float | None = None,
) -> Generator[tuple[int, str], None, None]:
    class Piper(Thread):
        def __init__(self, fd: int, pipe: IO[bytes]) -> None:
            super().__init__(name=f"PlumbumPiper{fd}Thread")
            self.pipe = pipe
            self.fd = fd
            self.empty = False
            self.daemon = True
            super().start()

        def read_from_pipe(self) -> bytes:
            return self.pipe.readline(linesize)

        def run(self) -> None:
            for line in iter(self.read_from_pipe, b""):
                queue.put((self.fd, decode(line)))
            # self.pipe.close()

    if line_timeout is None:
        line_timeout = float("inf")

    queue = Queue[tuple[int, str]]()
    assert proc.stdout
    assert proc.stderr
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


_iter_lines = _iter_lines_win32 if IS_WIN32 else _iter_lines_posix


# ===================================================================================================
# Exceptions
# ===================================================================================================
class ProcessExecutionError(OSError):
    """Represents the failure of a process. When the exit code of a terminated process does not
    match the expected result, this exception is raised by :func:`run_proc
    <plumbum.commands.run_proc>`. It contains the process' return code, stdout, and stderr, as
    well as the command line used to create the process (``argv``)
    """

    def __init__(
        self,
        argv: list[str],
        retcode: int,
        stdout: str | bytes,
        stderr: str | bytes,
        message: str | None = None,
        *,
        host: str | None = None,
    ):
        # we can't use 'super' here since OSError only keeps the first 2 args,
        # which leads to failing in loading this object from a pickle.dumps.
        # pylint: disable-next=non-parent-init-called
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

    def __str__(self) -> str:
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

    def __init__(self, msg: str, argv: list[str]):
        Exception.__init__(self, msg, argv)
        self.argv = argv


class ProcessLineTimedOut(Exception):
    """Raises by :func:`iter_lines <plumbum.commands.iter_lines>` when a ``line_timeout`` has been
    specified and it has elapsed before the process yielded another line"""

    def __init__(self, msg: str, argv: list[str] | None, machine: str | None):
        Exception.__init__(self, msg, argv, machine)
        self.argv = argv
        self.machine = machine


class CommandNotFound(AttributeError):
    """Raised by :func:`local.which <plumbum.machines.local.LocalMachine.which>` and
    :func:`RemoteMachine.which <plumbum.machines.remote.RemoteMachine.which>` when a
    command was not found in the system's ``PATH``"""

    def __init__(self, program: object, path: object):
        super().__init__(self, program, path)
        self.program = program
        self.path = path


# ===================================================================================================
# Timeout thread
# ===================================================================================================
class MinHeap:
    def __init__(self, items: Sequence[tuple[float, subprocess.Popen[str]]] = ()):
        self._items = list(items)
        heapq.heapify(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def push(self, item: tuple[float, subprocess.Popen[str]]) -> None:
        heapq.heappush(self._items, item)

    def pop(self) -> None:
        heapq.heappop(self._items)

    def peek(self) -> tuple[float, subprocess.Popen[str]]:
        return self._items[0]


_timeout_queue = Queue[tuple[Any, float]]()
_shutting_down = False


def _timeout_thread_func() -> None:
    waiting = MinHeap()
    try:
        while not _shutting_down:
            if waiting:
                ttk, _ = waiting.peek()
                timeout = max(0, ttk - time.time())
            else:
                timeout = None
            with contextlib.suppress(QueueEmpty):
                proc, time_to_kill = _timeout_queue.get(timeout=timeout)
                if proc is SystemExit:
                    # terminate
                    return
                waiting.push((time_to_kill, proc))
            now = time.time()
            while waiting:
                ttk, proc = waiting.peek()
                if ttk > now:
                    break
                waiting.pop()
                with contextlib.suppress(OSError):
                    if proc.poll() is None:
                        proc.kill()
                        proc._timed_out = True  # type: ignore[attr-defined]
    except Exception:
        if _shutting_down:
            # to prevent all sorts of exceptions during interpreter shutdown
            pass
        else:
            raise


bgthd = Thread(target=_timeout_thread_func, name="PlumbumTimeoutThread")
bgthd.daemon = True
bgthd.start()


def _register_proc_timeout(proc: subprocess.Popen[Any], timeout: float | None) -> None:
    if timeout is not None:
        _timeout_queue.put((proc, time.time() + timeout))


def _shutdown_bg_threads() -> None:
    global _shutting_down  # noqa: PLW0603
    _shutting_down = True
    # Make sure this still exists (don't throw error in atexit!)
    # TODO: not sure why this would be "falsey", though
    if _timeout_queue:  # type: ignore[truthy-bool]
        _timeout_queue.put((SystemExit, 0))
        # grace period
        bgthd.join(0.1)


atexit.register(_shutdown_bg_threads)


# ===================================================================================================
# run_proc
# ===================================================================================================
def run_proc(
    proc: subprocess.Popen[Any],
    retcode: int | None | Container[int],
    timeout: float | None = None,
) -> tuple[int, str, str]:
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
    proc._end_time = time.time()  # type: ignore[attr-defined]
    if not stdout:
        stdout = b""
    if not stderr:
        stderr = b""
    if custom_encoding := getattr(proc, "custom_encoding", None):
        stdout = stdout.decode(custom_encoding, "ignore")
        stderr = stderr.decode(custom_encoding, "ignore")

    return _check_process(proc, retcode, timeout, stdout, stderr)


# ===================================================================================================
# iter_lines
# ===================================================================================================


class Mode(enum.Enum):
    BY_POSITION = enum.auto()
    BY_TYPE = enum.auto()


BY_POSITION = Mode.BY_POSITION
BY_TYPE = Mode.BY_TYPE
DEFAULT_ITER_LINES_MODE = BY_POSITION

DEFAULT_BUFFER_SIZE = sys.maxsize


@typing.overload
def iter_lines(
    proc: subprocess.Popen[bytes],
    retcode: int = ...,
    timeout: float | None = ...,
    linesize: int = ...,
    line_timeout: float | None = ...,
    buffer_size: int | None = ...,
    *,
    mode: Literal[Mode.BY_POSITION] | None = ...,
    _iter_lines: Callable[
        [subprocess.Popen[bytes], Callable[[bytes], str], int, float | None],
        Generator[tuple[int, str], None, None],
    ] = _iter_lines,
) -> Generator[tuple[int, str], None, None]: ...


@typing.overload
def iter_lines(
    proc: subprocess.Popen[bytes],
    retcode: int = ...,
    timeout: float | None = ...,
    linesize: int = ...,
    line_timeout: float | None = ...,
    buffer_size: int | None = ...,
    *,
    mode: Literal[Mode.BY_TYPE],
    _iter_lines: Callable[
        [subprocess.Popen[bytes], Callable[[bytes], str], int, float | None],
        Generator[tuple[int, str], None, None],
    ] = _iter_lines,
) -> Generator[tuple[None, str] | tuple[str, None], None, None]: ...


def iter_lines(
    proc: subprocess.Popen[bytes],
    retcode: int = 0,
    timeout: float | None = None,
    linesize: int = -1,
    line_timeout: float | None = None,
    buffer_size: int | None = None,
    *,
    mode: Mode | None = None,
    _iter_lines: Callable[
        [subprocess.Popen[bytes], Callable[[bytes], str], int, float | None],
        Generator[tuple[int, str], None, None],
    ] = _iter_lines,
) -> Generator[tuple[int, str] | tuple[None, str] | tuple[str, None], None, None]:
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
                    ``0`` will disable buffering completely.

    :param mode: Controls what the generator yields. Defaults to DEFAULT_ITER_LINES_MODE (which is BY_POSITION by default)
                - BY_POSITION (default): yields ``(out, err)`` line tuples, where either item may be ``None``
                - BY_TYPE: yields ``(fd, line)`` tuples, where ``fd`` is 1 (stdout) or 2 (stderr)

    :returns: An iterator of (out, err) line tuples.
    """
    if mode is None:
        mode = DEFAULT_ITER_LINES_MODE

    if buffer_size is None:
        buffer_size = DEFAULT_BUFFER_SIZE

    assert mode in Mode

    encoding = getattr(proc, "custom_encoding", None) or "utf-8"
    decode = lambda s: s.decode(encoding, errors="replace").rstrip()  # noqa: E731

    _register_proc_timeout(proc, timeout)

    buffers: list[list[tuple[str | None, str | None] | str]] = [[], []]
    for t, line in _iter_lines(proc, decode, linesize, line_timeout):
        # verify that the proc hasn't timed out yet
        proc.verify(timeout=timeout, retcode=None, stdout=None, stderr=None)  # type: ignore[attr-defined]

        buffer = buffers[t]
        if buffer_size > 0:
            buffer.append(line)
            if buffer_size < sys.maxsize:
                del buffer[:-buffer_size]

        if mode is BY_POSITION:
            if t == 0:
                yield (line, None)
            else:
                yield (None, line)

        elif mode is BY_TYPE:
            yield (t + 1), line  # 1=stdout, 2=stderr

    # this will take care of checking return code and timeouts
    _check_process(proc, retcode, timeout, *("\n".join(s) + "\n" for s in buffers))  # type: ignore[arg-type]
