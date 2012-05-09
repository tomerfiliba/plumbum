import six
from tempfile import TemporaryFile
from subprocess import PIPE
import subprocess

if not six.PY3:
    bytes = str #@ReservedAssignment
    ascii = repr

#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(Exception):
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

class CommandNotFound(Exception):
    """Raised by :func:`local.which <plumbum.local_machine.LocalMachine.which>` and 
    :func:`RemoteMachine.which <plumbum.remote_machine.RemoteMachine.which>` when a 
    command was not found in the system's ``PATH``"""
    def __init__(self, program, path):
        Exception.__init__(self, program, path)
        self.program = program
        self.path = path

class RedirectionError(Exception):
    """Raised when an attempt is made to redirect an process' standard handle,
    which was already redirected to/from a file""" 


#===================================================================================================
# Utilities
#===================================================================================================
# modified from the stdlib pipes module for windows
_safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
_funnychars = '"`$\\'
def shquote(text):
    """Quotes the given text with shell escaping (assumes as syntax similar to ``sh``)"""
    if not text:
        return "''"
    text = str(text)
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = "".join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'

def shquote_list(seq):
    return [shquote(item) for item in seq]

def run_proc(proc, retcode):
    """Waits for the given process to terminate, with the expected exit code
    
    :param proc: a running Popen-like object
    
    :param retcode: the expected return (exit) code of the process. It defaults to 0 (the 
                    convention for success). If ``None``, the return code is ignored.
                    It may also be a tuple (or any object that supports ``__contains__``) 
                    of expected return codes. 

    :returns: A tuple of (return code, stdout, stderr)
    """
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = six.b("")
    if not stderr:
        stderr = six.b("")
    if getattr(proc, "encoding", None):
        stdout = stdout.decode(proc.encoding, "ignore")
        stderr = stderr.decode(proc.encoding, "ignore")
    
    if retcode is not None:
        if hasattr(retcode, "__contains__"):
            if proc.returncode not in retcode:
                raise ProcessExecutionError(getattr(proc, "argv", None), 
                    proc.returncode, stdout, stderr)
        elif proc.returncode != retcode:
            raise ProcessExecutionError(getattr(proc, "argv", None), 
                proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

#===================================================================================================
# Commands
#===================================================================================================
class BaseCommand(object):
    """Base of all command objects"""
    
    __slots__ = ["cwd", "env", "encoding"]
    
    def __str__(self):
        return " ".join(self.formulate())
    
    def __or__(self, other):
        """Creates a pipe with the other command"""
        return Pipeline(self, other)
    
    def __gt__(self, file):
        """Redirects the process' stdout to the given file"""
        return StdoutRedirection(self, file)
    
    def __ge__(self, file):
        """Redirects the process' stderr to the given file"""
        return StderrRedirection(self, file)
    
    def __lt__(self, file):
        """Redirects the given file into the process' stdin"""
        return StdinRedirection(self, file)
    def __lshift__(self, data):
        """Redirects the given data into the process' stdin"""
        return StdinDataRedirection(self, data)
    
    def __getitem__(self, args):
        """Creates a bound-command with the given arguments"""
        if not isinstance(args, (tuple, list)):
            args = (args,)
        if not args:
            return self
        if isinstance(self, BoundCommand):
            return BoundCommand(self.cmd, self.args + tuple(args))
        else:
            return BoundCommand(self, args)
    
    def __call__(self, *args, **kwargs):
        """A shortcut for `run(args)`, returning only the process' stdout"""
        return self.run(args, **kwargs)[1]

    def _get_encoding(self):
        raise NotImplementedError()

    def formulate(self, level = 0, args = ()):
        """Formulates the command into a command-line, i.e., a list of shell-quoted strings
        that can be executed by ``Popen`` or shells. 
        
        :param level: The nesting level of the formulation; it dictates how much shell-quoting
                      (if any) should be performed
        
        :param args: The arguments passed to this command (a tuple)
        
        :returns: A list of strings
        """
        raise NotImplementedError()

    def popen(self, args = (), **kwargs):
        """Spawns the given command, returning a ``Popen``-like object.
        
        :param args: Any arguments to be passed to the process (a tuple)
        
        :param kwargs: Any keyword-arguments to be passed to the ``Popen`` constructor
        
        :returns: A ``Popen``-like object
        """
        raise NotImplementedError()
    
    def run(self, args = (), **kwargs):
        """Runs the given command (equivalent to popen() followed by 
        :func:`run_proc <plumbum.commands.run_proc>`). If the exit code of the process does
        not match the expected one, :class:`ProcessExecutionError 
        <plumbum.commands.ProcessExecutionError>` is raised.
        
        :param args: Any arguments to be passed to the process (a tuple)
        
        :param retcode: The expected return code of this process (defaults to 0).
                        In order to disable exit-code validation, pass ``None``. It may also
                        be a tuple (or any iterable) of expected exit codes.
                        
                        .. note:: this argument must be passed as a keyword argument.
        
        :param kwargs: Any keyword-arguments to be passed to the ``Popen`` constructor
        
        :returns: A tuple of (return code, stdout, stderr)
        """
        retcode = kwargs.pop("retcode", 0)
        p = self.popen(args, **kwargs)
        try:
            return run_proc(p, retcode)
        finally:
            for f in [p.stdin, p.stdout, p.stderr]:
                try:
                    f.close()
                except Exception:
                    pass

class BoundCommand(BaseCommand):
    __slots__ = ["cmd", "args"]
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args
    def __repr__(self):
        return "BoundCommand(%r, %r)" % (self.cmd, self.args)
    def _get_encoding(self):
        return self.cmd._get_encoding()
    def formulate(self, level = 0, args = ()):
        return self.cmd.formulate(level + 1, self.args + tuple(args))
    def popen(self, args = (), **kwargs):
        if isinstance(args, str):
            args = (args,)
        return self.cmd.popen(self.args + tuple(args), **kwargs)

class Pipeline(BaseCommand):
    __slots__ = ["srccmd", "dstcmd"]
    def __init__(self, srccmd, dstcmd):
        self.srccmd = srccmd
        self.dstcmd = dstcmd
    def __repr__(self):
        return "Pipeline(%r, %r)" % (self.srccmd, self.dstcmd)
    def _get_encoding(self):
        return self.srccmd._get_encoding() or self.dstcmd._get_encoding()
    def formulate(self, level = 0, args = ()):
        return self.srccmd.formulate(level + 1) + ["|"] + self.dstcmd.formulate(level + 1, args)

    def popen(self, args = (), **kwargs):
        src_kwargs = kwargs.copy()
        src_kwargs["stdout"] = PIPE
        src_kwargs["stderr"] = PIPE
        
        srcproc = self.srccmd.popen(args, **src_kwargs)
        kwargs["stdin"] = srcproc.stdout
        dstproc = self.dstcmd.popen(**kwargs)
        # allow p1 to receive a SIGPIPE if p2 exits
        srcproc.stdout.close()
        srcproc.stderr.close()
        if srcproc.stdin:
            srcproc.stdin.close()
        dstproc.srcproc = srcproc
        return dstproc

class BaseRedirection(BaseCommand):
    __slots__ = ["cmd", "file"]
    SYM = None
    KWARG = None
    MODE = None
    
    def __init__(self, cmd, file):
        self.cmd = cmd
        self.file = file
    def _get_encoding(self):
        return self.cmd._get_encoding()
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.cmd, self.file)
    def formulate(self, level = 0, args = ()):
        return self.cmd.formulate(level + 1, args) + [self.SYM, shquote(getattr(self.file, "name", self.file))]
    def popen(self, args = (), **kwargs):
        from plumbum.local_machine import LocalPath
        from plumbum.remote_machine import RemotePath
        
        if self.KWARG in kwargs and kwargs[self.KWARG] not in (PIPE, None):
            raise RedirectionError("%s is already redirected" % (self.KWARG,))
        if isinstance(self.file, (str, LocalPath)):
            f = kwargs[self.KWARG] = open(str(self.file), self.MODE)
        elif isinstance(self.file, RemotePath):
            raise TypeError("Cannot redirect to/from remote paths")
        else:
            kwargs[self.KWARG] = self.file
            f = None
        try:
            return self.cmd.popen(args, **kwargs)
        finally:
            if f:
                f.close()

class StdinRedirection(BaseRedirection):
    __slots__ = []
    SYM = "<"
    KWARG = "stdin"
    MODE = "r"

class StdoutRedirection(BaseRedirection):
    __slots__ = []
    SYM = ">"
    KWARG = "stdout"
    MODE = "w"

class StderrRedirection(BaseRedirection):
    __slots__ = []
    SYM = "2>"
    KWARG = "stderr"
    MODE = "w"

class ERROUT(int):
    def __repr__(self):
        return "ERROUT"
    def __str__(self):
        return "&1"
ERROUT = ERROUT(subprocess.STDOUT)

class StdinDataRedirection(BaseCommand):
    __slots__ = ["cmd", "data"]
    CHUNK_SIZE = 16000
    
    def __init__(self, cmd, data):
        self.cmd = cmd
        self.data = data
    def _get_encoding(self):
        return self.cmd._get_encoding()
    
    def formulate(self, level = 0, args = ()):
        return ["echo %s" % (shquote(self.data),), "|", self.cmd.formulate(level + 1, args)]
    def popen(self, args = (), **kwargs):
        if "stdin" in kwargs and kwargs["stdin"] != PIPE:
            raise RedirectionError("stdin is already redirected")
        data = self.data
        if not isinstance(data, bytes) and self._get_encoding() is not None:
            data = data.encode(self._get_encoding())
        f = TemporaryFile()
        while data:
            chunk = data[:self.CHUNK_SIZE]
            f.write(chunk)
            data = data[self.CHUNK_SIZE:]
        f.seek(0)
        try:
            return self.cmd.popen(args, stdin = f, **kwargs)
        finally:
            f.close()

class ConcreteCommand(BaseCommand):
    QUOTE_LEVEL = None
    __slots__ = ["executable", "encoding"]
    def __init__(self, executable, encoding):
        self.executable = executable
        self.encoding = encoding
    def __str__(self):
        return str(self.executable)
    def _get_encoding(self):
        return self.encoding

    def formulate(self, level = 0, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                if level >= self.QUOTE_LEVEL:
                    argv.extend(shquote_list(a.formulate(level + 1)))
                else:
                    argv.extend(a.formulate(level + 1))
            else:
                if level >= self.QUOTE_LEVEL:
                    argv.append(shquote(a))
                else:
                    argv.append(str(a))
        #if self.encoding:
        #    argv = [a.encode(self.encoding) for a in argv if isinstance(a, six.string_types)]
        return argv

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
    def __init__(self, proc, expected_retcode):
        self.proc = proc
        self._expected_retcode = expected_retcode
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
        self._returncode, self._stdout, self._stderr = run_proc(self.proc, self._expected_retcode)
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


