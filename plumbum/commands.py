import os
from tempfile import TemporaryFile
from subprocess import PIPE


IS_WIN32 = os.name == "nt"

#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(Exception):
    def __init__(self, cmdline, retcode, stdout, stderr):
        Exception.__init__(self, cmdline, retcode, stdout, stderr)
        self.cmdline = cmdline
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        stdout = "\n         | ".join(self.stdout.splitlines())
        stderr = "\n         | ".join(self.stderr.splitlines())
        lines = ["Command line: %r" % (self.cmdline,), "Exit code: %s" % (self.retcode)]
        if stdout:
            lines.append("Stdout:  | %s" % (stdout,))
        if stderr:
            lines.append("Stderr:  | %s" % (stderr,))
        return "\n".join(lines)

class CommandNotFound(Exception):
    def __init__(self, progname, path):
        Exception.__init__(self, progname, path)
        self.progname = progname
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
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = "".join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'

def run_proc(proc, retcode):
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = ""
    if not stderr:
        stderr = ""
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "cmdline", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

def make_input(data, CHUNK_SIZE = 16000):
    f = TemporaryFile()
    while data:
        chunk = data[:CHUNK_SIZE]
        f.write(chunk)
        data = data[CHUNK_SIZE:]
    f.seek(0)
    return f

#===================================================================================================
# Command objects
#===================================================================================================
class ChainableCommand(object):
    def __or__(self, other):
        return Pipeline(self, other)
    def __gt__(self, stdout_file):
        return Redirection(self, stdout_file = stdout_file)
    def __ge__(self, stderr_file):
        return Redirection(self, stderr_file = stderr_file)
    def __lt__(self, stdin_file):
        return Redirection(self, stdin_file = stdin_file)
    def __lshift__(self, data):
        return Redirection(self, stdin_file = make_input(data))
    def __call__(self, *args, **kwargs):
        return self.run(args, **kwargs)[1]
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)
    
    def popen(self, args = (), **kwargs):
        raise NotImplementedError()

    def run(self, args = (), **kwargs):
        retcode = kwargs.pop("retcode", 0)
        return run_proc(self.popen(args, **kwargs), retcode)

class BoundCommand(ChainableCommand):
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = tuple(args)
    def __str__(self):
        return "%s %s" % (self.cmd, " ".join(repr(a) for a in self.args))
    def __repr__(self):
        return "BoundCommand(%r, %r)" % (self.cmd, self.args)
    
    def popen(self, args = (), **kwargs):
        return self.cmd.popen(self.args + tuple(args), **kwargs)
    def formulate(self, args = ()):
        return self.cmd.formulate(self.args + tuple(args))

class Pipeline(ChainableCommand):
    def __init__(self, srccmd, dstcmd):
        self.srccmd = srccmd
        self.dstcmd = dstcmd
    def __str__(self):
        return "(%s | %s)" % (self.srccmd, self.dstcmd)
    def __repr__(self):
        return "Pipeline(%r, %r)" % (self.srccmd, self.dstcmd)
    
    def popen(self, args = (), **kwargs):
        stdin = kwargs.pop("stdin", PIPE)
        stdout = kwargs.pop("stdout", PIPE)
        stderr = kwargs.pop("stderr", PIPE)
        
        srcproc = self.srccmd.popen(args, stdin = stdin, stderr = PIPE, **kwargs)
        dstproc = self.dstcmd.popen(stdin = srcproc.stdout, stdout = stdout, 
            stderr = stderr, **kwargs)
        srcproc.stdout.close() # allow p1 to receive a SIGPIPE if p2 exits
        srcproc.stderr.close()
        dstproc.srcproc = srcproc
        return dstproc

    def formulate(self, args = ()):
        return [shquote(a) for a in self.srccmd.formulate(args)] + ["|"] + [shquote(a) for a in self.dstcmd.formulate(args)]

class Redirection(ChainableCommand):
    def __init__(self, cmd, stdin_file = None, stdout_file = None, stderr_file = None):
        self.cmd = cmd
        self.stdin_file = stdin_file
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
    
    def __repr__(self):
        args = []
        if self.stdin_file:
            args.append("stdin_file = %r" % (self.stdin_file,))
        if self.stdout_file:
            args.append("stdout_file = %r" % (self.stdout_file,))
        if self.stderr_file:
            args.append("stderr_file = %r" % (self.stderr_file,))
        return "Redirection(%r, %s)" % (self.cmd, ", ".join(args))
    
    def __str__(self):
        parts = [str(self.cmd)]
        if self.stdin_file:
            parts.append("< %s" % (getattr(self.stdin_file, "name", self.stdin_file),))
        if self.stdout_file:
            parts.append("> %s" % (getattr(self.stdout_file, "name", self.stdout_file),))
        if self.stderr_file:
            parts.append("2> %s" % (getattr(self.stderr_file, "name", self.stderr_file),))
        return " ".join(parts)

    def formulate(self, args = ()):
        parts = self.cmd.formulate(args)
        for f, arrow in [(self.stdin_file, "<"), (self.stdout_file, ">"), (self.stderr_file, "2>")]:
            if f:
                parts.append(arrow)
                parts.append(shquote(str(getattr(f, "name", f))))
        return parts
    
    def popen(self, args = (), **kwargs):
        kw_stdin = kwargs.pop("stdin", PIPE)
        kw_stdout = kwargs.pop("stdout", PIPE)
        kw_stderr = kwargs.pop("stderr", PIPE)
        
        if self.stdin_file:
            if kw_stdin != PIPE:
                raise RedirectionError("stdin is already redirected")
            stdin = open(self.stdin_file, "r") if isinstance(self.stdin_file, str) else self.stdin_file
        else:
            stdin = kw_stdin
        
        if self.stdout_file:
            if kw_stdout != PIPE:
                raise RedirectionError("stdout is already redirected")
            stdout = open(self.stdout_file, "w") if isinstance(self.stdout_file, str) else self.stdout_file
        else:
            stdout = kw_stdout
        
        if self.stderr_file:
            if kw_stderr != PIPE:
                raise RedirectionError("stderr is already redirected")
            stderr = open(self.stderr_file, "w") if isinstance(self.stderr_file, str) else self.stderr_file
        else:
            stderr = kw_stderr
        
        return self.cmd.popen(args, stdin = stdin, stdout = stdout, stderr = stderr, **kw_stderr) 


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

