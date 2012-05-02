import time
import random
import logging
from tempfile import TemporaryFile
from subprocess import PIPE

shell_logger = logging.getLogger("plumbum.shell")


#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(Exception):
    def __init__(self, argv, retcode, stdout, stderr):
        Exception.__init__(self, argv, retcode, stdout, stderr)
        self.argv = argv
        self.retcode = retcode
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
    def __init__(self, program, path):
        Exception.__init__(self, program, path)
        self.program = program
        self.path = path

class RedirectionError(Exception):
    pass

class ShellSessionError(Exception):
    pass

#===================================================================================================
# Utilities
#===================================================================================================
# modified from the stdlib pipes module for windows
_safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
_funnychars = '"`$\\'
def shquote(text):
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
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = ""
    if not stderr:
        stderr = ""
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "argv", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

#===================================================================================================
# Commands
#===================================================================================================
class BaseCommand(object):
    cwd = None
    env = None
    
    def __str__(self):
        return " ".join(self.formulate())
    def __or__(self, other):
        return Pipeline(self, other)
    def __gt__(self, file):
        return StdoutRedirection(self, file)
    def __ge__(self, file):
        return StderrRedirection(self, file)
    def __lt__(self, file):
        return StdinRedirection(self, file)
    def __lshift__(self, data):
        return StdinDataRedirection(self, data)
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)
    def __call__(self, *args, **kwargs):
        return self.run(args, **kwargs)[1]
    
    def formulate(self, level = 0, args = ()):
        raise NotImplementedError()
    def popen(self, args = (), **kwargs):
        raise NotImplementedError()
    
    def run(self, args = (), **kwargs):
        retcode = kwargs.pop("retcode", 0)
        return run_proc(self.popen(args, **kwargs), retcode)

class BoundCommand(BaseCommand):
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args

    def formulate(self, level = 0, args = ()):
        return self.cmd.formulate(level + 1, self.args + tuple(args))
    
    def popen(self, args = (), **kwargs):
        if isinstance(args, str):
            args = (args,)
        return self.cmd.popen(self.args + tuple(args), **kwargs)

class Pipeline(BaseCommand):
    def __init__(self, srccmd, dstcmd):
        self.srccmd = srccmd
        self.dstcmd = dstcmd

    def formulate(self, level = 0, args = ()):
        return self.srccmd.formulate(level + 1) + ["|"] + self.dstcmd.formulate(level + 1, args)

    def popen(self, args = (), **kwargs):
        src_kwargs = kwargs.copy()
        src_kwargs["stdout"] = PIPE
        #src_kwargs["stderr"] = PIPE
        
        srcproc = self.srccmd.popen(args, **src_kwargs)
        kwargs["stdin"] = srcproc.stdout
        dstproc = self.dstcmd.popen(**kwargs)
        srcproc.stdout.close() # allow p1 to receive a SIGPIPE if p2 exits
        srcproc.stderr.close()
        dstproc.srcproc = srcproc
        return dstproc

class BaseRedirection(BaseCommand):
    SYM = None
    KWARG = None
    MODE = None
    
    def __init__(self, cmd, file):
        self.cmd = cmd
        self.file = file
    def formulate(self, level = 0, args = ()):
        return self.cmd.formulate(level + 1, args) + [self.SYM, shquote(getattr(self.file, "name", self.file))]
    def popen(self, args = (), **kwargs):
        if self.KWARG in kwargs and kwargs[self.KWARG] != PIPE:
            raise RedirectionError("%s is already redirected" % (self.KWARG,))
        if isinstance(self.file, str):
            kwargs[self.KWARG] = open(self.file, self.MODE)
        else:
            kwargs[self.KWARG] = self.file
        return self.cmd.popen(args, **kwargs)

class StdinRedirection(BaseRedirection):
    SYM = "<"
    KWARG = "stdin"
    MODE = "r"

class StdoutRedirection(BaseRedirection):
    SYM = ">"
    KWARG = "stdout"
    MODE = "w"

class StderrRedirection(BaseRedirection):
    SYM = "2>"
    KWARG = "stderr"
    MODE = "w"

class StdinDataRedirection(BaseCommand):
    CHUNK_SIZE = 16000
    TRUNCATE = 15
    
    def __init__(self, cmd, data):
        self.cmd = cmd
        self.data = data
    
    def __str__(self):
        shortened = self.data[:self.TRUNCATE]
        if len(self.data) > self.TRUNCATE:
            shortened += "..."
        return "%s << %r" % (self.cmd, shortened)
    
    def formulate(self, level = 0, args = ()):
        return ["echo %s" % (shquote(self.data),), "|", self.cmd.formulate(level + 1, args)]
    
    def popen(self, args = (), **kwargs):
        if "stdin" in kwargs and kwargs["stdin"] != PIPE:
            raise RedirectionError("stdin is already redirected")
        data = self.data
        f = TemporaryFile()
        while data:
            chunk = data[:self.CHUNK_SIZE]
            f.write(chunk)
            data = data[self.CHUNK_SIZE:]
        f.seek(0)
        return self.cmd.popen(args, stdin = f, **kwargs)

#===================================================================================================
# Shell Session Popen
#===================================================================================================
class MarkedPipe(object):
    __slots__ = ["pipe", "marker"]
    def __init__(self, pipe, marker):
        self.pipe = pipe
        self.marker = marker
    def close(self):
        pass
    def readline(self):
        line = self.pipe.readline()
        if not line:
            raise EOFError()
        if line.strip() == self.marker:
            return ""
        return line

class SessionPopen(object):
    def __init__(self, argv, isatty, stdin, stdout, stderr):
        self.argv = argv
        self.isatty = isatty
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = None
        self._done = False
    def poll(self):
        if self._done:
            return self.returncode
        else:
            return None
    def wait(self):
        self.communicate()
        return self.returncode
    def communicate(self, input = None):
        stdout = []
        stderr = []
        sources = [("1", stdout, self.stdout)]
        if not self.isatty:
            # in tty mode, stdout and stderr are unified
            sources.append(("2", stderr, self.stderr))
        i = 0
        while sources:
            if input:
                chunk = input[:1000]
                self.stdin.write(chunk)
                input = input[1000:]
            i = (i + 1) % len(sources)
            name, coll, pipe = sources[i]
            line = pipe.readline()
            shell_logger.debug("%s> %r", name, line)
            if not line:
                del sources[i]
            else:
                coll.append(line)
        if self.isatty:
            stdout.pop(0) # discard first line of prompt
        try:
            self.returncode = int(stdout.pop(-1))
        except (IndexError, ValueError):
            self.returncode = "Unknown"
        self._done = True
        stdout = b"".join(stdout)
        stderr = b"".join(stderr)
        return stdout, stderr


class ShellSession(object):
    def __init__(self, proc, isatty = False):
        self.proc = proc
        self.isatty = isatty
        self._current = None
        self.run("")
    
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
    
    def alive(self):
        """returns True if the ``ssh`` process is alive, False otherwise"""
        return self.proc and self.proc.poll() is None
    
    def close(self):
        if not self.alive():
            return
        try:
            self.proc.stdin.write(b"\nexit\n\n\nexit\n\n")
            self.proc.stdin.close()
            time.sleep(0.05)
        except EnvironmentError:
            pass
        self.proc.kill()
        self.proc = None
    
    def popen(self, cmd, retcode = 0):
        if self._current and not self._current._done:
            raise ShellSessionError("Each shell may start only one process at a time")
        
        if isinstance(cmd, BaseCommand):
            full_cmd = cmd.formulate(1)
        else:
            full_cmd = cmd
        marker = b"--.END%s.--" % (time.time() * random.random())
        if full_cmd.strip():
            full_cmd += " ; "
        full_cmd += "echo $? ; echo %s" % (marker,)
        if not self.isatty:
            full_cmd += " ; echo %s 1>&2" % (marker,)
        shell_logger.debug("Running %r", full_cmd)
        self.proc.stdin.write(full_cmd + "\n")
        self._current = SessionPopen(full_cmd, self.isatty, self.proc.stdin, 
            MarkedPipe(self.proc.stdout, marker), MarkedPipe(self.proc.stderr, marker))
        return self._current
    
    def run(self, cmd, retcode = 0):
        return run_proc(self.popen(cmd), retcode)


#===================================================================================================
# execution modifiers (background, foreground)
#===================================================================================================
class ExecutionModifier(object):
    def __init__(self, retcode = 0):
        self.retcode = retcode
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.retcode)
    @classmethod
    def __call__(cls, retcode):
        return cls(retcode)

class Future(object):
    def __init__(self, proc, expected_retcode):
        self.proc = proc
        self._expected_retcode = expected_retcode
        self._returncode = None
        self._stdout = None
        self._stderr = None
    def __repr__(self):
        return "<Future %r (%s)>" % (self.proc.cmdline, self._returncode if self.ready() else "running",)
    def poll(self):
        if self.proc.poll() is not None:
            self.wait()
        return self._returncode is not None
    ready = poll
    def wait(self):
        if self._returncode is not None:
            return
        self._returncode, self._stdout, self._stderr = run_proc(self.proc, self._expected_retcode)
    @property
    def stdout(self):
        self.wait()
        return self._stdout
    @property
    def stderr(self):
        self.wait()
        return self._stderr
    @property
    def returncode(self):
        self.wait()
        return self._returncode

class BG(ExecutionModifier):
    def __rand__(self, cmd):
        return Future(cmd.popen(), self.retcode)
BG = BG()

class FG(ExecutionModifier):
    def __rand__(self, cmd):
        cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)
FG = FG()







