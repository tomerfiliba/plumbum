import sys
import os
import logging
from types import ModuleType
from tempfile import TemporaryFile
from subprocess import Popen, PIPE
from contextlib import contextmanager
from plumbum.path import Path, LocalPathLocation


cmd_logger = logging.getLogger(__name__)

WIN32 = os.name == "nt"
__all__ = ["local", "BG", "FG", "ProcessExecutionError", "CommandNotFound"]

#===================================================================================================
# Workdir and Environment abstractions
#===================================================================================================
class _Workdir(Path):
    def __init__(self):
        self._dirstack = [os.getcwd()]
    def __str__(self):
        return str(self._path)
    @property
    def _path(self):
        return self._dirstack[-1]
    def __repr__(self):
        return "<Workdir %s>" % (self,)
    def __hash__(self):
        raise TypeError("Workdir can change and is unhashable")
    @contextmanager
    def __call__(self, dir): #@ReservedAssignment
        self._dirstack.append(None)
        self.chdir(dir)
        try:
            yield
        finally:
            self._dirstack.pop(-1)
            self.chdir(self._dirstack[-1])

    def getpath(self):
        return local.path(str(self))
    def chdir(self, dir): #@ReservedAssignment
        os.chdir(str(dir))
        self._dirstack[-1] = local.path(dir)

cwd = _Workdir()

class _Env(object):
    def __init__(self):
        if WIN32:
            self._envstack = [dict((k.upper(), v) for k, v in os.environ.items())]
        else:
            self._envstack = [os.environ.copy()]
        self._update_path()
    def _update_path(self):
        self.path = [Path(LocalPathLocation, p) for p in self["PATH"].split(os.path.pathsep)]
    
    @contextmanager
    def __call__(self, **kwargs):
        self._envstack.append(self._envstack[-1].copy())
        self.update(**kwargs)
        try:
            yield
        finally:
            self._update_path()
            self._envstack.pop(-1)
    def __iter__(self):
        return self._envstack[-1].iteritems()
    def __contains__(self, name):
        if WIN32:
            name = name.upper()
        return name in self._envstack[-1]
    def __delitem__(self, name):
        if WIN32:
            name = name.upper()
        del self._envstack[-1][name]
    def __getitem__(self, name):
        if WIN32:
            name = name.upper()
        return self._envstack[-1][name]
    def __setitem__(self, name, value):
        if WIN32:
            name = name.upper()
        self._envstack[-1][name] = value
        if name == "PATH":
            self._update_path()
    def update(self, *args, **kwargs):
        self._envstack[-1].update(*args, **kwargs)
        if WIN32:
            for k, v in list(self._envstack[-1].items()):
                self._envstack[-1][k.upper()] = v
        self._update_path()
    def get(self, name, default = None):
        if WIN32:
            name = name.upper()
        return self._envstack[-1].get(name, default)
    def getdict(self):
        self._envstack[-1]["PATH"] = os.path.pathsep.join(str(p) for p in self.path)
        return dict((str(k), str(v)) for k, v in self._envstack[-1].items())
    def expand(self, expr):
        old = os.environ
        os.environ = self.getdict()
        output = os.path.expanduser(os.path.expandvars(expr))
        os.environ = old
        return output

    @property
    def home(self):
        if "HOME" in self:
            return local.path(self["HOME"])
        elif "USERPROFILE" in self:
            return local.path(self["USERPROFILE"])
        elif "HOMEPATH" in self:
            return local.path(self.get("HOMEDRIVE", ""), self["HOMEPATH"])
        return None
    @home.setter
    def home(self, p):
        if "HOME" in self:
            self["HOME"] = str(p)
        elif "USERPROFILE" in self:
            self["USERPROFILE"] = str(p)
        elif "HOMEPATH" in self:
            self["HOMEPATH"] = str(p)
        else:
            self["HOME"] = str(p)
    @property
    def user(self):
        if "USER" in self:
            return self["USER"]
        elif "USERNAME" in self:
            return self["USERNAME"]
        return None

env = _Env()

#===================================================================================================
# Utilities
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

def _run(proc, retcode):
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = ""
    if not stderr:
        stderr = ""
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "cmdline", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

def _make_input(data, CHUNK_SIZE = 16000):
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
        return Redirection(self, stdin_file = _make_input(data))
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
        return _run(self.popen(args, **kwargs), retcode)

class Command(ChainableCommand):
    cwd = cwd
    env = env
    
    def __init__(self, executable):
        self.executable = executable
    def __str__(self):
        return str(self.executable)
    def __repr__(self):
        return "<Command %s>" % (self.executable,)

    def formulate(self, args = ()):
        argv = [str(self.executable)]
        argv.extend(a.formulate() if hasattr(a, "formulate") else str(a) 
            for a in args)
        return argv

    def popen(self, args = (), **kwargs):
        stdin = kwargs.pop("stdin", PIPE)
        stdout = kwargs.pop("stdout", PIPE)
        stderr = kwargs.pop("stderr", PIPE)
        if isinstance(args, str):
            args = (args,)
        cwd = str(kwargs.pop("cwd", self.cwd))
        env = kwargs.pop("env", self.env)
        if not isinstance(env, dict):
            env = env.getdict()
        
        cmdline = self.formulate(args)
        cmd_logger.debug("Running %r, cwd = %s" % (cmdline, cwd))
        proc = Popen(cmdline, executable = str(self.executable), stdin = stdin, 
            stdout = stdout, stderr = stderr, cwd = cwd, env = env, **kwargs)
        proc.cmdline = cmdline
        return proc

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
    
class Redirection(ChainableCommand):
    def __init__(self, cmd, stdin_file = PIPE, stdout_file = PIPE, stderr_file = PIPE):
        self.cmd = cmd
        self.stdin_file = open(stdin_file, "r") if isinstance(stdin_file, str) else stdin_file
        self.stdout_file = open(stdout_file, "w") if isinstance(stdout_file, str) else stdout_file
        self.stderr_file = open(stderr_file, "w") if isinstance(stderr_file, str) else stderr_file
    
    def __repr__(self):
        args = []
        if self.stdin_file != PIPE:
            args.append("stdin_file = %r" % (self.stdin_file,))
        if self.stdout_file != PIPE:
            args.append("stdout_file = %r" % (self.stdout_file,))
        if self.stderr_file != PIPE:
            args.append("stderr_file = %r" % (self.stderr_file,))
        return "Redirection(%r, %s)" % (self.cmd, ", ".join(args))
    
    def __str__(self):
        parts = [str(self.cmd)]
        if self.stdin_file != PIPE:
            parts.append("< %s" % (getattr(self.stdin_file, "name", self.stdin_file),))
        if self.stdout_file != PIPE:
            parts.append("> %s" % (getattr(self.stdout_file, "name", self.stdout_file),))
        if self.stderr_file != PIPE:
            parts.append("2> %s" % (getattr(self.stderr_file, "name", self.stderr_file),))
        return " ".join(parts)
    
    def popen(self, args, **kwargs):
        stdin = kwargs.pop("stdin", PIPE)
        stdout = kwargs.pop("stdout", PIPE)
        stderr = kwargs.pop("stderr", PIPE)
        
        return self.cmd.popen(args,
            stdin = self.stdin_file if self.stdin_file != PIPE else stdin,
            stdout = self.stdout_file if self.stdout_file != PIPE else stdout,
            stderr = self.stderr_file if self.stderr_file != PIPE else stderr, 
            **kwargs)

#===================================================================================================
# Local command namespace
#===================================================================================================
class CommandNotFound(Exception):
    def __init__(self, progname, path):
        Exception.__init__(self, progname, path)
        self.progname = progname
        self.path = path

class LocalCommandNamespace(object):
    _EXTENSIONS = [""]
    if WIN32:
        _EXTENSIONS += [".exe", ".bat"]

    cwd = cwd
    env = env
    
    @classmethod
    def _which(cls, progname):
        for p in env.path:
            try:
                filelist = {n.basename : n for n in p.list()}
            except OSError:
                continue
            for ext in cls._EXTENSIONS:
                n = progname + ext
                if n in filelist:
                    return filelist[n]
        return None
    
    def path(self, *parts):
        return Path(LocalPathLocation, *parts)
    
    @classmethod
    def which(cls, progname):
        if WIN32:
            progname = progname.lower()
        for pn in [progname, progname.replace("_", "-")]:
            path = cls._which(pn)
            if path:
                return path
        raise CommandNotFound(progname, list(env.path))

    def __getitem__(self, name):
        name = str(name)
        if "/" in name or "\\" in name:
            return Command(local.path(name))
        else:
            return Command(self.which(name))
    
    python = Command(sys.executable)

local = LocalCommandNamespace()

#===================================================================================================
# execution modifiers (background, foreground)
#===================================================================================================
class Executer(object):
    def __init__(self, retcode = 0):
        self.retcode = retcode
    @classmethod
    def __call__(cls, retcode):
        return cls(retcode)

class RUN(Executer):
    def __rand__(self, cmd):
        return cmd(retcode = self.retcode)
RUN = RUN()

class Future(object):
    def __init__(self, proc, expected_retcode):
        self.proc = proc
        self._expected_retcode = expected_retcode
        self._returncode = None
        self._stdout = None
        self._stderr = None
    def __repr__(self):
        return "<Future %r (%s)>" % (self.proc.cmdline, self._returncode if self.ready() else "running",)
    def ready(self):
        return self._returncode is not None
    def wait(self):
        if self.ready():
            return
        self._returncode, self._stdout, self._stderr = _run(self.proc, self._expected_retcode)
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

class BG(Executer):
    def __rand__(self, cmd):
        return Future(cmd.popen(), self.retcode)
BG = BG()

class FG(Executer):
    def __rand__(self, cmd):
        return cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)
FG = FG()

#===================================================================================================
# Local module (e.g., from plumbum.local import grep)
#===================================================================================================
class LocalModule(ModuleType):
    def __init__(self):
        ModuleType.__init__(self, "plumbum.local", __doc__)
        self.__file__ = __file__
        self.__package__ = __package__
    def __getattr__(self, name):
        return local[name]
LocalModule = LocalModule()

sys.modules[LocalModule.__name__] = LocalModule



