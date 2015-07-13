import os
from select import select
from subprocess import PIPE
import sys

from plumbum.commands.processes import run_proc, ProcessExecutionError


#===================================================================================================
# execution modifiers (background, foreground)
#===================================================================================================
class ExecutionModifier(object):
    __slots__ = ["retcode"]
    def __init__(self, retcode = 0):
        self.retcode = retcode
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.retcode)
    @classmethod
    def __call__(cls, retcode):
        return cls(retcode)

class Future(object):
    """Represents a "future result" of a running process. It basically wraps a ``Popen``
    object and the expected exit code, and provides poll(), wait(), returncode, stdout,
    and stderr.
    """
    def __init__(self, proc, expected_retcode, timeout = None):
        self.proc = proc
        self._expected_retcode = expected_retcode
        self._timeout = timeout
        self._returncode = None
        self._stdout = None
        self._stderr = None
    def __repr__(self):
        return "<Future %r (%s)>" % (self.proc.argv, self._returncode if self.ready() else "running",)
    def poll(self):
        """Polls the underlying process for termination; returns ``False`` if still running,
        or ``True`` if terminated"""
        if self.proc.poll() is not None:
            self.wait()
        return self._returncode is not None
    ready = poll
    def wait(self):
        """Waits for the process to terminate; will raise a
        :class:`plumbum.commands.ProcessExecutionError` in case of failure"""
        if self._returncode is not None:
            return
        self._returncode, self._stdout, self._stderr = run_proc(self.proc,
            self._expected_retcode, self._timeout)
    @property
    def stdout(self):
        """The process' stdout; accessing this property will wait for the process to finish"""
        self.wait()
        return self._stdout
    @property
    def stderr(self):
        """The process' stderr; accessing this property will wait for the process to finish"""
        self.wait()
        return self._stderr
    @property
    def returncode(self):
        """The process' returncode; accessing this property will wait for the process to finish"""
        self.wait()
        return self._returncode

class BG(ExecutionModifier):
    """
    An execution modifier that runs the given command in the background, returning a
    :class:`Future <plumbum.commands.Future>` object. In order to mimic shell syntax, it applies
    when you right-and it with a command. If you wish to expect a different return code
    (other than the normal success indicate by 0), use ``BG(retcode)``. Example::

        future = sleep[5] & BG       # a future expecting an exit code of 0
        future = sleep[5] & BG(7)    # a future expecting an exit code of 7

    .. note::

       When processes run in the **background** (either via ``popen`` or
       :class:`& BG <plumbum.commands.BG>`), their stdout/stderr pipes might fill up,
       causing them to hang. If you know a process produces output, be sure to consume it
       every once in a while, using a monitoring thread/reactor in the background.
       For more info, see `#48 <https://github.com/tomerfiliba/plumbum/issues/48>`_
    """
    __slots__ = []
    def __rand__(self, cmd):
        return Future(cmd.popen(), self.retcode)

BG = BG()
"""
An execution modifier that runs the given command in the background, returning a
:class:`Future <plumbum.commands.Future>` object. In order to mimic shell syntax, it applies
when you right-and it with a command. If you wish to expect a different return code
(other than the normal success indicate by 0), use ``BG(retcode)``. Example::

    future = sleep[5] & BG       # a future expecting an exit code of 0
    future = sleep[5] & BG(7)    # a future expecting an exit code of 7

.. note::

   When processes run in the **background** (either via ``popen`` or
   :class:`& BG <plumbum.commands.BG>`), their stdout/stderr pipes might fill up,
   causing them to hang. If you know a process produces output, be sure to consume it
   every once in a while, using a monitoring thread/reactor in the background.
   For more info, see `#48 <https://github.com/tomerfiliba/plumbum/issues/48>`_
"""

class FG(ExecutionModifier):
    """
    An execution modifier that runs the given command in the foreground, passing it the
    current process' stdin, stdout and stderr. Useful for interactive programs that require
    a TTY. There is no return value.

    In order to mimic shell syntax, it applies when you right-and it with a command.
    If you wish to expect a different return code (other than the normal success indicate by 0),
    use ``FG(retcode)``. Example::

        vim & FG       # run vim in the foreground, expecting an exit code of 0
        vim & FG(7)    # run vim in the foreground, expecting an exit code of 7
    """
    __slots__ = []
    def __rand__(self, cmd):
        cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)

FG = FG()


class TEE(ExecutionModifier):
    """Run a command, dumping its stdout/stderr to the current process's stdout
    and stderr, but ALSO return them.  Useful for interactive programs that
    expect a TTY but also have valuable output.

    Use as:

        ls["-l"] & TEE

    Returns a tuple of (return code, stdout, stderr), just like ``run()``.
    """
    def __init__(self, retcode=0, buffered=True):
        """`retcode` is the return code to expect to mean "success".  Set
        `buffered` to False to disable line-buffering the output, which may
        cause stdout and stderr to become more entangled than usual.
        """
        self.retcode = retcode
        self.buffered = buffered

    @classmethod
    def __call__(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __rand__(self, cmd):
        with cmd.bgrun(retcode=self.retcode, stdin=None, stdout=PIPE, stderr=PIPE) as p:
            outbuf = []
            errbuf = []
            out = p.stdout
            err = p.stderr
            buffers = {out: outbuf, err: errbuf}
            tee_to = {out: sys.stdout, err: sys.stderr}
            while p.poll() is None:
                ready, _, _ = select((out, err), (), ())
                for fd in ready:
                    buf = buffers[fd]
                    data = os.read(fd.fileno(), 4096)
                    if not data:  # eof
                        continue

                    # Python conveniently line-buffers stdout and stderr for
                    # us, so all we need to do is write to them
                    tee_to[fd].write(data.decode('utf-8'))
                    # And then "unbuffered" is just flushing after each write
                    if not self.buffered:
                        tee_to[fd].flush()

                    buf.append(data)

            stdout = ''.join([x.decode('utf-8') for x in outbuf])
            stderr = ''.join([x.decode('utf-8') for x in errbuf])
            return p.returncode, stdout, stderr

TEE = TEE()

class TF(ExecutionModifier):
    """
    An execution modifier that runs the given command, but returns True/False depending on the retcode.
    This returns True if the expected exit code is returned, and false if it is not.
    This is useful for checking true/false bash commands.

    If you wish to expect a different return code (other than the normal success indicate by 0),
    use ``TF(retcode)``. If you want to run the process in the forground, then use
    ``TF(FG=True)``.

    Example::

        local['touch']['/root/test'] & TF * Returns False, since this cannot be touched
        local['touch']['/root/test'] & TF(1) # Returns True
        local['touch']['/root/test'] & TF(FG=True) * Returns False, will show error message
    """

    def __init__(self, retcode=0, FG=False):
        """`retcode` is the return code to expect to mean "success".  Set
        `FG` to True to run in the foreground.
        """
        self.retcode = retcode
        self.foreground = FG

    @classmethod
    def __call__(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __rand__(self, cmd):
        try:
            if self.foreground:
                cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)
            else:
                cmd(retcode = self.retcode)
            return True
        except ProcessExecutionError:
            return False

TF = TF()


class RETCODE(ExecutionModifier):
    """
    An execution modifier that runs the given command, causing it to run and return the retcode.
    This is useful for working with bash commands that have important retcodes but not very
    useful output.

    If you want to run the process in the forground, then use ``RETCODE(FG=True)``.

    Example::

        local['touch']['/root/test'] & RETCODE # Returns 1, since this cannot be touched
        local['touch']['/root/test'] & RETCODE(FG=True) * Returns 1, will show error message
    """

    def __init__(self,  FG=False):
        """`FG` to True to run in the foreground.
        """
        self.foreground = FG

    @classmethod
    def __call__(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __rand__(self, cmd):
            if self.foreground:
                return cmd.run(retcode = None, stdin = None, stdout = None, stderr = None)[0]
            else:
                return cmd.run(retcode = None)[0]

RETCODE = RETCODE()

