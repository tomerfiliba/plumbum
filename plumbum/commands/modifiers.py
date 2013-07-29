from plumbum.commands.processes import run_proc


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
        """Polls the underlying process for termination; returns ``None`` if still running,
        or the process' returncode if terminated"""
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
    use ``BG(retcode)``. Example::

        vim & FG       # run vim in the foreground, expecting an exit code of 0
        vim & FG(7)    # run vim in the foreground, expecting an exit code of 7
    """
    __slots__ = []
    def __rand__(self, cmd):
        cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)

FG = FG()
"""
An execution modifier that runs the given command in the foreground, passing it the
current process' stdin, stdout and stderr. Useful for interactive programs that require
a TTY. There is no return value.

In order to mimic shell syntax, it applies when you right-and it with a command.
If you wish to expect a different return code (other than the normal success indicate by 0),
use ``BG(retcode)``. Example::

    vim & FG       # run vim in the foreground, expecting an exit code of 0
    vim & FG(7)    # run vim in the foreground, expecting an exit code of 7
"""

class Tee(object):
    def __init__(self, *streams):
        self.streams = streams





