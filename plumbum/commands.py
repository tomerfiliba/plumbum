import six
from tempfile import TemporaryFile
from subprocess import PIPE
import subprocess

if six.PY3:
    bytes = str
else:
    ascii = repr

#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(Exception):
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
    def __init__(self, program, path):
        Exception.__init__(self, program, path)
        self.program = program
        self.path = path

class RedirectionError(Exception):
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
        stdout = six.b("")
    if not stderr:
        stderr = six.b("")
    if getattr(proc, "encoding", None):
        stdout = stdout.decode(proc.encoding, "replace")
        stderr = stderr.decode(proc.encoding, "replace")
    
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "argv", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

#===================================================================================================
# Commands
#===================================================================================================
class BaseCommand(object):
    __slots__ = ["cwd", "env", "encoding"]
    
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
        if not isinstance(args, (tuple, list)):
            args = (args,)
        if not args:
            return self
        if isinstance(self, BoundCommand):
            return BoundCommand(self.cmd, self.args + tuple(args))
        else:
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
    __slots__ = ["cmd", "args"]
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args
    
    def __repr__(self):
        return "BoundCommand(%r, %r)" % (self.cmd, self.args)

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
    __slots__ = ["cmd", "file"]
    SYM = None
    KWARG = None
    MODE = None
    
    def __init__(self, cmd, file):
        self.cmd = cmd
        self.file = file
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.cmd, self.file)
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

class ConcreteCommand(BaseCommand):
    QUOTE_LEVEL = None
    __slots__ = ["executable", "encoding"]
    def __init__(self, executable, encoding):
        self.executable = executable
        self.encoding = encoding
    def __str__(self):
        return str(self.executable)

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
        if self.encoding:
            argv = [a.encode(self.encoding) for a in argv]
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
    __slots__ = []
    def __rand__(self, cmd):
        return Future(cmd.popen(), self.retcode)
BG = BG()

class FG(ExecutionModifier):
    __slots__ = []
    def __rand__(self, cmd):
        cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)
FG = FG()



