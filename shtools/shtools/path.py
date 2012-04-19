import os
from subprocess import Popen, PIPE
import tempfile
import shutil
from contextlib import contextmanager


class Path(object):
    __slots__ = ["path", "basename", "dirname"]
    def __init__(self, *paths):
        self.path = os.path.abspath(os.path.normpath(os.path.join(*(env.expand_home(str(p)) for p in paths))))
        self.basename = os.path.basename(self.path)
        self.dirname = os.path.dirname(self.path)
    
    @classmethod
    def cwd(cls):
        return cls(os.getcwd())
    @classmethod
    @contextmanager
    def tempdir(cls):
        temp = cls(tempfile.mkdtemp())
        try:
            yield temp
        finally:
            temp.remove()
    
    def __iter__(self):
        return iter(self.list())
    def __eq__(self, other):
        return self.path == str(other)
    def __ne__(self, other):
        return not (self == other)
    def __str__(self):
        return self.path
    def __div__(self, other):
        return Path(self.path, str(other))
    def up(self):
        return self / ".."

    def list(self):
        return [self / fn for fn in os.listdir(self.path)]
    def walk(self):
        for p in self:
            yield p
            if p.isdir():
                for p2 in p.walk():
                    yield p2

    def isfile(self):
        return os.path.isfile(self.path)
    def isdir(self):
        return os.path.isdir(self.path)
    def exists(self):
        return os.path.exists(self.path)
    def stat(self):
        return os.stat(self.path)
    
    def copy(self, dst, override = False):
        dst = dst if isinstance(dst, Path) else Path(str(dst))
        if override:
            Path(dst).remove()
        if self.isdir():
            shutil.copytree(self.path, str(dst))
        else:
            shutil.copy2(self.path, str(dst))
        return dst
    def move(self, dst):
        shutil.move(self.path, str(dst))
        return dst if isinstance(dst, Path) else Path(str(dst))
    def rename(self, newname):
        """Renames the last element in the path. 
        Example::
        
            >>> p = Path("/foo/bar/spam.txt")
            >>> p2 = p.rename("bacon.txt")
            >>> p2 == "/foo/bar/bacon.txt"
            True
        """
        return self.move(Path(self.dirname, newname))
    def remove(self):
        """removes the given path, if it exists; if this path is a directory, removes recursively"""
        if not self.exists():
            return
        if self.isdir():
            shutil.rmtree(self.path)
        else:
            os.remove(self.path)
    def mkdir(self):
        """make a directory on this path (including all needed intermediate directories), if this
        path doesn't already exist"""
        if not self.exists():
            os.makedirs(self.path)

    def open(self, fn, *args):
        """opens a file at this path"""
        return open(str(self / fn), *args)

class EnvPathList(object):
    def __init__(self, env):
        self._env = env
        self._refresh()
    def _refresh(self):
        self._pathlist = [Path(p) for p in self._env.get("PATH", "").split(os.path.pathsep)]
    def _flush(self):
        self._env._envstack[-1]["PATH"] = os.path.pathsep.join(str(p) for p in self._pathlist)
    
    def append(self, p):
        self._pathlist.append(p)
        self._flush()
    def extend(self, iterable):
        self._pathlist.extend(iterable)
        self._flush()
    def index(self, p):
        self.pathlist.index(p)
    def remove(self, p):
        self.remove(p)
        self._flush()
    def pop(self, index):
        self._pathlist.pop(index)
        self._flush()
    def insert(self, index, p):
        self._pathlist.insert(index, p)
        self._flush()

    def __contains__(self, p):
        return p in self._pathlist
    def __iter__(self):
        return iter(self._pathlist)
    def __len__(self):
        return len(self._pathlist)
    def __getitem__(self, index):
        return self._pathlist[index]
    def __setitem__(self, index, value):
        self._pathlist[index] = value
    def __delitem__(self, index):
        del self._pathlist[index]


class _EnvStack(object):
    def __init__(self):
        self._envstack = [os.environ.copy()]
        self._path = None
    @property
    def path(self):
        if self._path is None:
            self._path = EnvPathList(self)
        return self._path
    def __getitem__(self, name):
        return self._envstack[-1][name]
    def __setitem__(self, name, value):
        self._envstack[-1][name] = value
        if name.upper() == "PATH":
            self.path._refresh()
    def __delitem__(self, name):
        del self._envstack[-1][name]
        if name.upper() == "PATH":
            self.path._refresh()
    def __iter__(self):
        return iter(self._envstack[-1].items())
    def __len__(self):
        return len(self._envstack[-1])
    def __contains__(self, name):
        return name in self._envstack[-1]
    def get(self, key, *default):
        return self._envstack[-1].get(key, *default)
    def pop(self, key, *default):
        return self._envstack[-1].pop(key, *default)
    def update(self, *args, **kwargs):
        oldpath = self._envstack[-1].get("PATH")
        self._envstack[-1].update(*args, **kwargs)
        newpath = self._envstack[-1].get("PATH")
        if oldpath != newpath:
            self.path._refresh()
    def getdict(self):
        return self._envstack[-1]
    
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
    
    @contextmanager
    def push(self, *args, **kwargs):
        self._envstack.append(self._envstack[-1].copy())
        self.update(*args, **kwargs)
        try:
            yield self
        finally:
            self._envstack.pop(-1)
    
    def expand_vars(self, text):
        old = os.environ
        os.environ = self.getdict()
        output = os.path.expandvars(text)
        os.environ = old
        return output
    
    def expand_home(self, text):
        orig_home = os.environ["HOME"]
        try:
            os.environ["HOME"] = self.home
            return os.path.expanduser(str(text))
        finally:
            os.environ["HOME"] = orig_home


env = _EnvStack()

class _Workdir(object):
    def cd(self, newdir):
        os.chdir(str(newdir))
    def get(self):
        return Path.cwd()
    def __str__(self):
        return str(self.get())

    chdir = cd
    getcwd = get
    
    @contextmanager
    def push(self, newdir):
        curr = self.get()
        self.cd(newdir)
        try:
            yield (newdir if isinstance(newdir, Path) else Path(newdir))
        finally:
            self.cd(curr)

cwd = _Workdir()


class ShellError(Exception):
    pass
class ProgramNotFound(ShellError):
    pass
class CommandFailure(ShellError):
    def __init__(self, cmdargs, retcode, stdout, stderr):
        self.cmdargs = cmdargs
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        out = "\n          | ".join(self.stdout.splitlines())
        err = "\n          | ".join(self.stderr.splitlines())
        return ("Command failed with exit code %s\n"
            "    Arguments: %r\n"
            "    Stdout: %s\n\n"
            "    Stderr: %s") % (self.retcode, self.cmdargs, out, err)

class Command(object):
    retcodes = (0,)
    def __init__(self, executable):
        self.executable = executable
    def __repr__(self):
        return "<Command %s>" % (self.executable,)
    def pipe(self, destproc):
        pass
    def redirect(self, filename):
        pass
    def run(self, *args, **kwargs):
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
        proc = Popen(cmdargs, executable = str(self.executable), stdin = PIPE, stdout = PIPE, 
            stderr = PIPE, cwd = str(cwd), env = env.getdict())
        stdout, stderr = proc.communicate()
        if proc.returncode not in self.retcodes:
            raise CommandFailure(cmdargs, proc.returncode, stdout, stderr)
        return stdout, stderr
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)[0]




class _CommandNamespace(object):
    @classmethod
    def which(cls, progname):
        for p in env.path:
            try:
                filelist = {n.basename : n for n in p.list()}
            except OSError:
                continue
            for ext in ["", ".exe", ".bat"]:
                n = progname + ext
                if n in filelist:
                    return filelist[n]
        raise ProgramNotFound()
    def __getattr__(self, name):
        return self[name]
    def __getitem__(self, name):
        if isinstance(name, Path) or "/" in name or "\\" in name:
            return Command(name)
        else:
            return Command(self.which(name))

cmd = _CommandNamespace()


#with cwd.push("c:\\progra~1\\git\\bin"):
print cmd.ls()




