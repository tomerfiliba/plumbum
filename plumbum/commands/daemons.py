from __future__ import annotations

import contextlib
import errno
import os
import signal
import subprocess
import sys
import time
import traceback
import typing

from plumbum.commands.processes import ProcessExecutionError

if typing.TYPE_CHECKING:
    from plumbum.commands.base import BaseCommand


class _fake_lock:
    """Needed to allow normal os.exit() to work without error"""

    @staticmethod
    def acquire(_: bool) -> bool:
        return True

    @staticmethod
    def release() -> None:
        pass


def posix_daemonize(
    command: BaseCommand,
    cwd: str,
    stdout: str | None = None,
    stderr: str | None = None,
    append: bool = True,
) -> subprocess.Popen[bytes]:
    if stdout is None:
        stdout = os.devnull
    if stderr is None:
        stderr = stdout

    MAX_SIZE = 16384
    rfd, wfd = os.pipe()
    argv = command.formulate()
    firstpid = os.fork()
    if firstpid == 0:
        # first child: become session leader
        os.close(rfd)
        rc = 0
        try:
            os.setsid()
            os.umask(0)
            stdin_file = open(os.devnull, encoding="utf-8")
            stdout_file = open(stdout, "a" if append else "w", encoding="utf-8")
            stderr_file = open(stderr, "a" if append else "w", encoding="utf-8")
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            proc_str = command.popen(
                cwd=cwd,
                close_fds=True,
                stdin=stdin_file.fileno(),
                stdout=stdout_file.fileno(),
                stderr=stderr_file.fileno(),
            )
            os.write(wfd, str(proc_str.pid).encode("utf8"))
        except Exception:
            rc = 1
            tbtext = "".join(traceback.format_exception(*sys.exc_info()))[-MAX_SIZE:]
            os.write(wfd, tbtext.encode("utf8"))
        finally:
            os.close(wfd)
            os._exit(rc)

    # wait for first child to die
    os.close(wfd)
    _, rc = os.waitpid(firstpid, 0)
    output: str | bytes = os.read(rfd, MAX_SIZE)
    assert isinstance(output, bytes)
    os.close(rfd)
    with contextlib.suppress(UnicodeError):
        output = output.decode("utf8")
    if rc == 0 and output.isdigit():
        secondpid = int(output)
    else:
        raise ProcessExecutionError(argv, rc, "", output)
    proc: subprocess.Popen[bytes] = subprocess.Popen.__new__(subprocess.Popen)  # type: ignore[arg-type]
    proc._child_created = True  # type: ignore[attr-defined]
    proc.returncode = None
    proc.stdout = None
    proc.stdin = None
    proc.stderr = None
    proc.pid = secondpid
    proc.universal_newlines = False
    proc._input = None  # type: ignore[attr-defined]
    proc._waitpid_lock = _fake_lock()  # type: ignore[attr-defined]
    proc._communication_started = False  # type: ignore[attr-defined]
    proc.args = argv
    proc.argv = argv  # type: ignore[attr-defined]

    def poll(self: subprocess.Popen[bytes] = proc) -> int | None:
        if self.returncode is None:
            try:
                os.kill(self.pid, 0)
            except OSError as ex:
                if ex.errno == errno.ESRCH:
                    # process does not exist
                    self.returncode = 0
                else:
                    raise
        return self.returncode

    def wait(self: subprocess.Popen[bytes] = proc) -> int:
        while self.returncode is None:
            if self.poll() is None:
                time.sleep(0.5)
        return proc.returncode

    proc.poll = poll  # type: ignore[method-assign]
    proc.wait = wait  # type: ignore[method-assign, assignment]
    return proc


def win32_daemonize(
    command: BaseCommand,
    cwd: str,
    stdout: str | None = None,
    stderr: str | None = None,
    append: bool = True,
) -> subprocess.Popen[str]:
    if stdout is None:
        stdout = os.devnull
    if stderr is None:
        stderr = stdout
    DETACHED_PROCESS = 0x00000008
    stdin_file = open(os.devnull, encoding="utf-8")
    stdout_file = open(stdout, "a" if append else "w", encoding="utf-8")
    stderr_file = open(stderr, "a" if append else "w", encoding="utf-8")
    return command.popen(
        cwd=cwd,
        stdin=stdin_file.fileno(),
        stdout=stdout_file.fileno(),
        stderr=stderr_file.fileno(),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,  # type: ignore[attr-defined]
    )
