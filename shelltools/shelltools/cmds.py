import os
from subprocess import PIPE, Popen
from contextlib import contextmanager
import sys


WIN32 = sys.platform == "win32"
__all__ = ["cmd", "env", "cwd", "Command", "ProcessExecutionError", "CommandNotFound"]

class Path(object):
    def __init__(self, *parts):
        self._path = os.path.abspath(os.path.join(*(str(p) for p in parts)))
        if WIN32:
            self._path = self._path.lower()
    def __str__(self):
        return self._path
    def __repr__(self):
        return "<Path %s>" % (self,)
    def __div__(self, other):
        return Path(self, other)
    def __iter__(self):
        return iter(self.list())
    def __eq__(self, other):
        return str(self) == str(other)
    def __ne__(self, other):
        return str(self) != str(other)
    def __hash__(self):
        return hash(str(self))

    def list(self): #@ReservedAssignment
        return [self / fn for fn in os.listdir(str(self))]
    def walk(self, filter = lambda p: True): #@ReservedAssignment
        for p in self:
            if filter(p):
                yield p
            if p.isdir() and filter(p):
                for p2 in p.walk():
                    yield p2
    
    @property
    def basename(self):
        return os.path.basename(str(self))
    @property
    def dirname(self):
        return os.path.dirname(str(self))
    def up(self):
        return Path(self.dirname)
    def isdir(self):
        return os.path.isdir(str(self))
    def isfile(self):
        return os.path.isfile(str(self))
    def exists(self):
        return os.path.exists(str(self))
    def stat(self):
        return os.stat(str(self))

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
    @contextmanager
    def __call__(self, dir):
        self._dirstack.append(Path(dir))
        try:
            yield
        finally:
            self._dirstack.pop(-1)
    def __hash__(self):
        raise TypeError("Workdir can change and is unhashable")

    def getpath(self):
        return Path(str(self))
    def chdir(self, dir):
        self._dirstack[-1] = Path(dir)

g_cwd = cwd = _Workdir()


class _Env(object):
    def __init__(self):
        self._envstack = [os.environ.copy()]
        self._update_path()
    def _update_path(self):
        self.path = [Path(p) for p in self["PATH"].split(os.path.pathsep)]
    
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
        return name in self._envstack[-1]
    def __delitem__(self, name):
        del self._envstack[-1][name]
    def __getitem__(self, name):
        return self._envstack[-1][name]
    def __setitem__(self, name, value):
        self._envstack[-1][name] = value
        if name == "PATH":
            self._update_path()
    def update(self, *args, **kwargs):
        self._envstack[-1].update(*args, **kwargs)
        self._update_path()
    def get(self, name, default = None):
        return self._envstack[-1].get(name, default)
    def getdict(self):
        self._envstack[-1]["PATH"] = os.path.pathsep.join(str(p) for p in self.path)
        return self._envstack[-1].copy()
    def expand(self, expr):
        old = os.environ
        os.environ = self.getdict()
        output = os.path.expanduser(os.path.expandvars(expr))
        os.environ = old
        return output

    @property
    def home(self):
        if "HOME" in self:
            return Path(self["HOME"])
        elif "USERPROFILE" in self:
            return Path(self["USERPROFILE"])
        elif "HOMEPATH" in self:
            return Path(self.get("HOMEDRIVE", ""), self["HOMEPATH"])
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

g_env = env = _Env()

def _popen(args, executable = None, cwd = None, env = None, **kwargs):
    if cwd is None:
        cwd = str(g_cwd)
    if env is None:
        env = g_env.getdict()
    return Popen(args, executable = executable, cwd = cwd, env = env, **kwargs)

class ProcessExecutionError(Exception):
    def __init__(self, cmdline, retcode, stdout, stderr):
        Exception.__init__(self, cmdline, retcode, stdout, stderr)
        self.cmdline = cmdline
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        stdout = "\n  |      ".join(self.stdout.splitlines())
        stderr = "\n  |      ".join(self.stderr.splitlines())
        return "Command line: %r\nExit code: %s\nStdout:  %s\nStderr:  %s" % (
            self.cmdline, self.retcode, stdout, stderr)

class CommandNotFound(Exception):
    def __init__(self, progname, path):
        Exception.__init__(self, progname, path)
        self.progname = progname
        self.path = path

class Command(object):
    def __init__(self, executable):
        self.executable = executable
    def __repr__(self):
        return "<Command %s>" % (self.executable,)
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)[1]
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)

    def _build_cmdargs(self, *args, **kwargs):
        cmdargs = [str(self.executable)] + list(args)
        for k, v in kwargs.items():
            if len(k) == 1:
                cmdargs.append("-" + k)
            else:
                cmdargs.append("--" + k)
            if v is True:
                pass
            elif v is False or v is None:
                cmdargs.pop(-1)
            else:
                cmdargs.append(str(v))
        return cmdargs

    def popen(self, *args, **kwargs):
        stdin = kwargs.pop("stdin", PIPE)
        stdout = kwargs.pop("stdout", PIPE)
        stderr = kwargs.pop("stderr", PIPE)
        return _popen([str(self.executable)] + list(args), str(self.executable), 
            stdin = stdin, stdout = stdout, stderr = stderr)

    def run(self, *args, **kwargs):
        retcode = kwargs.pop("_retcode", 0)
        input = kwargs.pop("_input", None)
        stdin = kwargs.pop("stdin", PIPE)
        stdout = kwargs.pop("stdout", PIPE)
        stderr = kwargs.pop("stderr", PIPE)
        cmdargs = [str(self.executable)] + list(args)
        print cmdargs
        proc = _popen(cmdargs, str(self.executable), stdin = stdin, 
            stdout = stdout, stderr = stderr)
        stdout, stderr = proc.communicate(input)
        if retcode is not None and proc.returncode != retcode:
            raise ProcessExecutionError(cmdargs, proc.returncode, stdout, stderr)
        return proc.returncode, stdout, stderr

class BoundCommand(object):
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args
        print repr(cmd), repr(args)
    def __str__(self):
        return "%s%s" % (self.cmd, self.args)
    def __or__(self, intocmd):
        return Pipeline(self, intocmd)
    def popen(self, **kwargs):
        return self.cmd.popen(*self.args, **kwargs)
    def run(self, **kwargs):
        return self.cmd.run(*self.args, **kwargs)
    def __call__(self, **kwargs):
        return self.run(**kwargs)[1]

class Pipeline(object):
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
    def __str__(self):
        return "(%s | %s)" % (self.src, self.dst)
    def __or__(self, intocmd):
        if not isinstance(intocmd, (BoundCommand, Pipeline)):
            intocmd = BoundCommand(intocmd, ())
        return Pipeline(self, intocmd)
    def __call__(self, **kwargs):
        return self.run(**kwargs)[1]
    def popen(self, **kwargs):
        srcproc = self.src.popen(**kwargs)
        dstproc = self.dst.popen(stdin = srcproc.stdout)
        return dstproc
    def run(self, **kwargs):
        dstproc = self.popen(**kwargs)
        stdout, stderr = dstproc.communicate()
        return dstproc.returncode, stdout, stderr


class _CommandNamespace(object):
    _EXTENSIONS = [""]
    if WIN32:
        _EXTENSIONS += [".exe", ".bat"]
    
    @classmethod
    def which(cls, progname):
        if WIN32:
            progname = progname.lower()
        for p in env.path:
            try:
                filelist = {n.basename : n for n in p.list()}
            except OSError:
                continue
            for ext in cls._EXTENSIONS:
                n = progname + ext
                if n in filelist:
                    return filelist[n]
        raise CommandNotFound(progname, list(env.path))
    
    def __getattr__(self, name):
        return self[name]
    def __getitem__(self, name):
        name = str(name)
        if "/" in name or "\\" in name:
            return Command(Path(name))
        else:
            return Command(self.which(name))
    
    python = Command(sys.executable)

cmd = _CommandNamespace()


if __name__ == "__main__":
    ls = cmd.ls
    grep = cmd.grep
    
    print (ls["-l"] | grep["path"] | grep["2.py"])()
    
    
    




