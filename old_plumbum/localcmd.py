import sys
import os
import logging
import functools
import glob
import shutil
from types import ModuleType
from subprocess import Popen, PIPE
from contextlib import contextmanager
from plumbum.path import Path
from plumbum.commands import CommandNotFound, ChainableCommand, IS_WIN32
import subprocess


cmd_logger = logging.getLogger(__name__)

#===================================================================================================
# Workdir and Environment abstractions
#===================================================================================================
class LocalPathLocation(object):
    def __str__(self):
        return ""
    def normpath(self, parts):
        return os.path.normpath(os.path.join(os.getcwd(), *(str(p) for p in parts)))
    def listdir(self, p):
        return os.listdir(p)
    def isdir(self, p):
        return os.path.isdir(p)
    def isfile(self, p):
        return os.path.isfile(p)
    def exists(self, p):
        return os.path.exists(p)
    def stat(self, p):
        return os.stat(p)
    def chdir(self, p):
        os.chdir(p)
    def glob(self, p):
        return glob.glob(p)
    def delete(self, p):
        if not self.exists(p):
            return
        elif self.isdir(p):
            shutil.rmtree(p, ignore_errors = True)
        else:
            os.remove(p)
    def move(self, src, dst):
        shutil.move(src, dst)

LocalPathLocation = LocalPathLocation()

class LocalWorkdir(Path):
    def __init__(self):
        self._location = LocalPathLocation
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

cwd = LocalWorkdir()

class LocalEnvPath(list):
    def append(self, path):
        list.extend(self, local.path(path))
    def extend(self, paths):
        list.extend(self, (local.path(p) for p in paths)) #@UndefinedVariable
    def insert(self, index, path):
        list.extend(self, index, local.path(path))
    def index(self, path):
        list.index(self, local.path(path))
    def __contains__(self, path):
        return list.__contains__(self, local.path(path)) 
    def remove(self, path):
        list.remove(self, local.path(path))
    def update(self):
        self[:] = [local.path(p) for p in env.get("PATH", "").split(os.path.pathsep)] #@UndefinedVariable
    def commit(self):
        local.env._envstack[-1]["PATH"] =  os.path.pathsep.join(str(p) for p in self)

def upperify_on_win32(func):
    if IS_WIN32:
        @functools.wraps(func)
        def wrapper(self, name, *args):
            return func(self, name.upper(), *args)
        return wrapper
    else:
        return func

class LocalEnv(object):
    def __init__(self):
        # os.environ already takes care of upper'ing on windows
        self._envstack = [os.environ.copy()]
        self._path = None
    
    @contextmanager
    def __call__(self, **kwargs):
        self._envstack.append(self._envstack[-1].copy())
        self.update(**kwargs)
        try:
            yield
        finally:
            self._envstack.pop(-1)
            self.path.update()
    
    def __iter__(self):
        return iter(self._envstack[-1].items())
    def __hash__(self):
        raise TypeError("unhashable type")
    def __len__(self):
        return len(self._envstack[-1])
    @upperify_on_win32
    def __contains__(self, name):
        return name in self._envstack[-1]
    @upperify_on_win32
    def __delitem__(self, name):
        del self._envstack[-1][name]
    @upperify_on_win32
    def __getitem__(self, name):
        return self._envstack[-1][name]
    @upperify_on_win32
    def __setitem__(self, name, value):
        self._envstack[-1][name] = value
        if name == "PATH":
            self.path.update()
    
    def clear(self):
        self._envstack[-1].clear()
    def keys(self):
        return self._envstack[-1].keys()
    def items(self):
        return self._envstack[-1].items()
    def values(self):
        return self._envstack[-1].values()
    @upperify_on_win32
    def get(self, name, *default):
        return self._envstack[-1].get(name, *default)
    @upperify_on_win32
    def pop(self, name, *default):
        return self._envstack[-1].pop(name, *default)

    if IS_WIN32:
        def update(self, *args, **kwargs):
            self._envstack[-1].update(*args, **kwargs)
            for k, v in list(self._envstack[-1].items()):
                self._envstack[-1][k.upper()] = v
            self.path.update()
    else:
        def update(self, *args, **kwargs):
            self._envstack[-1].update(*args, **kwargs)
            self.path.update()
    
    def getdict(self):
        self.path.commit()
        return dict((k, str(v)) for k, v in self._envstack[-1].items())
    def expand(self, expr):
        old = os.environ
        os.environ = self.getdict()
        output = os.path.expanduser(os.path.expandvars(expr))
        os.environ = old
        return output

    @property
    def path(self):
        if self._path is None:
            self._path = LocalEnvPath()
            self._path.update()
        return self._path

    def _get_home(self):
        if "HOME" in self:
            return local.path(self["HOME"])
        elif "USERPROFILE" in self:
            return local.path(self["USERPROFILE"])
        elif "HOMEPATH" in self:
            return local.path(self.get("HOMEDRIVE", ""), self["HOMEPATH"])
        return None
    def _set_home(self, p):
        if "HOME" in self:
            self["HOME"] = str(p)
        elif "USERPROFILE" in self:
            self["USERPROFILE"] = str(p)
        elif "HOMEPATH" in self:
            self["HOMEPATH"] = str(p)
        else:
            self["HOME"] = str(p)
    home = property(_get_home, _set_home)
    
    @property
    def user(self):
        if "USER" in self:
            return self["USER"]
        elif "USERNAME" in self:
            return self["USERNAME"]
        return None

env = LocalEnv()

#===================================================================================================
# Command objects
#===================================================================================================
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
        for a in args:
            if not a:
                continue
            elif hasattr(a, "formulate"):
                argv.extend(a.formulate())
            else:
                argv.append(str(a))
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

        if subprocess.mswindows and "startupinfo" not in kwargs:
            kwargs["startupinfo"] = subprocess.STARTUPINFO()
            kwargs["startupinfo"].dwFlags |= subprocess.STARTF_USESHOWWINDOW  #@UndefinedVariable
            kwargs["startupinfo"].wShowWindow = subprocess.SW_HIDE  #@UndefinedVariable
        
        cmdline = self.formulate(args)
        cmd_logger.debug("Running %r, cwd = %s", cmdline, cwd)
        proc = Popen(cmdline, executable = str(self.executable), stdin = stdin, 
            stdout = stdout, stderr = stderr, cwd = cwd, env = env, **kwargs)
        proc.cmdline = cmdline
        return proc


#===================================================================================================
# Local command namespace
#===================================================================================================
class Local(object):
    _EXTENSIONS = [""]
    if IS_WIN32:
        _EXTENSIONS += [".exe", ".bat"]

    @property
    def cwd(self):
        return cwd
    @property
    def env(self):
        return env
    
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
    
    def path(self, p):
        if isinstance(p, Path):
            if p._location is LocalPathLocation:
                return p
            else:
                raise TypeError("Given path is non-local: %r" % (p,))
        else:
            return Path(LocalPathLocation, p)
    
    @classmethod
    def which(cls, progname):
        if IS_WIN32:
            progname = progname.lower()
        for pn in [progname, progname.replace("_", "-")]:
            path = cls._which(pn)
            if path:
                return path
        raise CommandNotFound(progname, list(env.path))

    def __getitem__(self, name):
        if isinstance(name, Path):
            return Command(name)
        elif "/" in name or "\\" in name:
            # assume absolute/relate path
            return Command(local.path(name))
        else:
            # search for command
            return Command(self.which(name))
    
    python = Command(sys.executable)

local = Local()

#===================================================================================================
# Local module (e.g., ``from plumbum.local import grep``)
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





