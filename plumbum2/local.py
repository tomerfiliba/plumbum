import sys
import os
import glob
import shutil
import subprocess
from plumbum2.path import Path
from subprocess import Popen, PIPE
from plumbum2.commands import shquote, shquote_list, BaseCommand
from contextlib import contextmanager
import functools


IS_WIN32 = os.name == "nt"

local = None

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
            shutil.copytree(self.path, str(dst))
        else:
            shutil.copy2(self.path, str(dst))
        return dst
    def rename(self, newname):
        self.move(LocalPath(self.dirname, newname))
    def mkdir(self):
        if not self.exists():
            os.makedirs(self.path)

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


class LocalCommand(BaseCommand):
    #cwd = local.cwd
    env = env
    
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
        argv = self.formulate(args)
        print "!!", argv
        proc = Popen(argv, executable = str(self.executable), stdin = stdin, stdout = stdout, 
            stderr = stderr, cwd = cwd, env = env, **kwargs)
        proc.argv = argv
        return proc




if __name__ == "__main__":
    ssh = LocalCommand("ssh")
    pwd = LocalCommand("pwd")
    
    here = LocalPath(os.getcwd())
    print here // "*.py"
    
    cmd = ssh["localhost", "cd", "/usr", "&&", ssh["localhost", "cd", "/", "&&", 
        ssh["localhost", "cd", "/bin", "&&", pwd]]]
    print cmd.formulate(0)
    








