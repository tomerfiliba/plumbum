import sys
import os
import glob
import shutil
import subprocess
import functools
import logging
from subprocess import Popen, PIPE
from plumbum.path import Path
from plumbum.commands import shquote, shquote_list, BaseCommand, CommandNotFound
from contextlib import contextmanager
from types import ModuleType


local_logger = logging.getLogger("plumbum.local")

IS_WIN32 = os.name == "nt"

class LocalPath(Path):
    __slots__ = ["_path"]
    def __init__(self, *parts):
        self._path = os.path.normpath(os.path.join(os.getcwd(), *(str(p) for p in parts)))
    def __new__(cls, *parts):
        if len(parts) == 1 and isinstance(parts[0], cls):
            return parts[0]
        return object.__new__(cls, *parts)
    def __str__(self):
        return self._path
    def _get_info(self):
        return self._path

    @property
    def basename(self):
        return os.path.basename(str(self))
    @property
    def dirname(self):
        return os.path.dirname(str(self))

    def join(self, *parts):
        return LocalPath(self, *parts)
    def list(self):
        return [self.join(fn) for fn in os.listdir(str(self))]
    def isdir(self):
        return os.path.isdir(str(self))
    def isfile(self):
        return os.path.isfile(str(self))
    def exists(self):
        return os.path.exists(str(self))
    def stat(self):
        return os.stat(str(self))
    def glob(self, pattern):
        return [LocalPath(fn) for fn in glob.glob(str(self.join(pattern)))] 

    def delete(self):
        if not self.exists():
            return
        if self.isdir():
            shutil.rmtree(str(self))
        else:
            os.remove(str(self))
    def move(self, dst):
        if not isinstance(dst, (str, LocalPath)):
            raise TypeError("dst must be a string or a LocalPath")
        shutil.move(str(self), str(dst))
        return LocalPath(dst)
    def copy(self, dst, override = False):
        if not isinstance(dst, (str, LocalPath)):
            raise TypeError("dst must be a string or a LocalPath")
        dst = LocalPath(dst)
        if override:
            dst.remove()
        if self.isdir():
            shutil.copytree(str(self), str(dst))
        else:
            shutil.copy2(str(self), str(dst))
        return dst
    def rename(self, newname):
        self.move(LocalPath(self.dirname, newname))
    def mkdir(self):
        if not self.exists():
            os.makedirs(str(self))

class Workdir(LocalPath):
    __slots__ = []
    def __init__(self):
        self._path = os.path.normpath(os.getcwd())
    def __hash__(self):
        raise TypeError("unhashable type")
    
    def chdir(self, newdir):
        os.chdir(str(newdir))
        self._path = os.path.normpath(os.getcwd())
    def getpath(self):
        return LocalPath(self)
    @contextmanager
    def __call__(self, newdir):
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)


class EnvPathList(list):
    __slots__ = []
    def append(self, path):
        list.extend(self, LocalPath(path))
    def extend(self, paths):
        list.extend(self, (LocalPath(p) for p in paths))
    def insert(self, index, path):
        list.extend(self, index, LocalPath(path))
    def index(self, path):
        list.index(self, LocalPath(path))
    def __contains__(self, path):
        return list.__contains__(self, LocalPath(path)) 
    def remove(self, path):
        list.remove(self, LocalPath(path))
    def update(self, text):
        self[:] = [LocalPath(p) for p in text.split(os.path.pathsep)]
    def join(self):
        return os.path.pathsep.join(str(p) for p in self)

def upperify_on_win32(func):
    if IS_WIN32:
        @functools.wraps(func)
        def wrapper(self, name, *args):
            return func(self, name.upper(), *args)
        return wrapper
    else:
        return func

class Env(object):
    __slots__ = ["_curr", "_path"]

    def __init__(self):
        # os.environ already takes care of upper'ing on windows
        self._curr = os.environ.copy()
        self._path = EnvPathList()
        self._update_path()
        if IS_WIN32 and "HOME" not in self and self.home is not None:
            self["HOME"] = self.home
    
    def _update_path(self):
        self._path.update(self.get("PATH", ""))
    
    @contextmanager
    def __call__(self, **kwargs):
        prev = self._curr.copy()
        self.update(**kwargs)
        try:
            yield
        finally:
            self._curr = prev
            self._update_path()
    
    def __iter__(self):
        return iter(self._curr.items())
    def __hash__(self):
        raise TypeError("unhashable type")
    def __len__(self):
        return len(self._curr)
    @upperify_on_win32
    def __contains__(self, name):
        return name in self._curr
    @upperify_on_win32
    def __delitem__(self, name):
        del self._curr[name]
    @upperify_on_win32
    def __getitem__(self, name):
        return self._curr[name]
    @upperify_on_win32
    def __setitem__(self, name, value):
        self._curr[name] = value
        if name == "PATH":
            self._update_path()
    
    def clear(self):
        self._curr.clear()
    def keys(self):
        return self._curr.keys()
    def items(self):
        return self._curr.items()
    def values(self):
        return self._curr.values()
    @upperify_on_win32
    def get(self, name, *default):
        return self._curr.get(name, *default)
    @upperify_on_win32
    def pop(self, name, *default):
        return self._curr.pop(name, *default)

    if IS_WIN32:
        def update(self, *args, **kwargs):
            self._curr.update(*args, **kwargs)
            for k, v in list(self._curr.items()):
                self._curr[k.upper()] = v
            self._update_path()
    else:
        def update(self, *args, **kwargs):
            self._curr.update(*args, **kwargs)
            self._update_path()
    
    def getdict(self):
        self._curr["PATH"] = self.path.join()
        return dict((k, str(v)) for k, v in self._curr.items())
    def expand(self, expr):
        prev = os.environ
        os.environ = self.getdict()
        try:
            output = os.path.expanduser(os.path.expandvars(expr))
        finally:
            os.environ = prev
        return output

    @property
    def path(self):
        return self._path

    def _get_home(self):
        if "HOME" in self:
            return LocalPath(self["HOME"])
        elif "USERPROFILE" in self:
            return LocalPath(self["USERPROFILE"])
        elif "HOMEPATH" in self:
            return LocalPath(self.get("HOMEDRIVE", ""), self["HOMEPATH"])
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


class LocalCommand(BaseCommand):
    def __init__(self, executable):
        self.executable = executable

    def __str__(self):
        return str(self.executable)

    def formulate(self, level = 0, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                if level >= 2:
                    argv.extend(shquote_list(a.formulate(level + 1)))
                else:
                    argv.extend(a.formulate(level + 1))
            else:
                if level >= 2:
                    argv.append(shquote(a))
                else:
                    argv.append(a)
        return argv
    
    def popen(self, args = (), stdin = PIPE, stdout = PIPE, stderr = PIPE, cwd = None, 
            env = None, **kwargs):
        if isinstance(args, str):
            args = (args,)
        if subprocess.mswindows and "startupinfo" not in kwargs and not sys.stdin.isatty():
            kwargs["startupinfo"] = subprocess.STARTUPINFO()
            kwargs["startupinfo"].dwFlags |= subprocess.STARTF_USESHOWWINDOW  #@UndefinedVariable
            kwargs["startupinfo"].wShowWindow = subprocess.SW_HIDE  #@UndefinedVariable
        if cwd is None:
            cwd = self.cwd
        if cwd is None:
            cwd = local.cwd

        if env is None:
            env = self.env
        if env is None:
            env = local.env
        if hasattr(env, "getdict"):
            env = env.getdict()
        
        argv = self.formulate(args)
        local_logger.debug("Running %r", argv)
        proc = Popen(argv, executable = str(self.executable), stdin = stdin, stdout = stdout, 
            stderr = stderr, cwd = str(cwd), env = env, **kwargs)
        proc.argv = argv
        return proc


class LocalMachine(object):
    cwd = Workdir()
    env = Env()

    if IS_WIN32:
        _EXTENSIONS = ["", ".exe", ".bat"]
        
        @classmethod
        def _which(cls, progname):
            for p in cls.env.path:
                try:
                    filelist = {n.basename : n for n in p.list()}
                except OSError:
                    continue
                for ext in cls._EXTENSIONS:
                    n = progname + ext
                    if n in filelist:
                        return filelist[n]
            return None
    else:
        @classmethod
        def _which(cls, progname):
            for p in cls.env.path:
                try:
                    filelist = {n.basename : n for n in p.list()}
                except OSError:
                    continue
                if progname in filelist:
                    return filelist[progname]
            return None
    
    @classmethod
    def which(cls, progname):
        if IS_WIN32:
            progname = progname.lower()
        for pn in [progname, progname.replace("_", "-")]:
            path = cls._which(pn)
            if path:
                return path
        raise CommandNotFound(progname, list(cls.env.path))

    def path(self, p):
        if isinstance(p, LocalPath):
            return p
        elif isinstance(p, Path):
            raise TypeError("Given path is non-local: %r" % (p,))
        else:
            return LocalPath(p)

    def __getitem__(self, cmd):
        if isinstance(cmd, LocalPath):
            return LocalCommand(cmd)
        elif isinstance(cmd, Path):
            raise TypeError("Given path is non-local: %r" % (cmd,))
        elif isinstance(cmd, str): 
            if "/" in cmd or "\\" in cmd:
                # assume path
                return LocalCommand(local.path(cmd))
            else:
                # search for command
                return LocalCommand(self.which(cmd))
        else:
            raise TypeError("cmd must be a path or a string: %r" % (cmd,))
    
    python = LocalCommand(sys.executable)


local = LocalMachine()

#===================================================================================================
# Module hack: ``from plumbum.local import ls``
#===================================================================================================
class LocalModule(ModuleType):
    def __init__(self, name):
        ModuleType.__init__(self, name, __doc__)
        self.__file__ = __file__
        self.__package__ = __package__
    def __getattr__(self, name):
        return local[name]
LocalModule = LocalModule("plumbum.local_commands")
sys.modules[LocalModule.__name__] = LocalModule



if __name__ == "__main__":
    ssh = local["ssh"]
    pwd = local["pwd"]
    
    print (ssh, pwd)
    print (local.cwd // "*.py")
    
    cmd = ssh["localhost", "cd", "/usr", "&&", ssh["localhost", "cd", "/", "&&", 
        ssh["localhost", "cd", "/bin", "&&", pwd]]]
    print (cmd.formulate(0))
