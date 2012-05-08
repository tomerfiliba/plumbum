import sys
import os
import glob
import shutil
import subprocess
import logging
import stat
from subprocess import Popen, PIPE
from contextlib import contextmanager
from plumbum.path import Path
from plumbum.commands import CommandNotFound, ConcreteCommand
from plumbum.session import ShellSession
from types import ModuleType
from tempfile import mkdtemp
from plumbum.lib import setdoc


local_logger = logging.getLogger("plumbum.local")

IS_WIN32 = os.name == "nt"

#===================================================================================================
# Local Paths
#===================================================================================================
class LocalPath(Path):
    """The class implementing local-machine paths"""
    
    __slots__ = ["_path"]
    if IS_WIN32:
        CASE_SENSITIVE = False
    
    def __init__(self, *parts):
        for p in parts:
            if not isinstance(p, (str, LocalPath)):
                raise TypeError("LocalPath can be constructed only from strings or other LocalPaths")
        self._path = os.path.normpath(os.path.join(os.getcwd(), *(str(p) for p in parts)))
        if IS_WIN32:
            self._path = self._path.lower()
    def __new__(cls, *parts):
        if len(parts) == 1 and isinstance(parts[0], cls):
            return parts[0]
        return object.__new__(cls)
    def __str__(self):
        return self._path
    def _get_info(self):
        return self._path

    @property
    @setdoc(Path)
    def basename(self):
        return os.path.basename(str(self))
    
    @property
    @setdoc(Path)
    def dirname(self):
        return os.path.dirname(str(self))

    @setdoc(Path)
    def join(self, *parts):
        return LocalPath(self, *parts)
    
    @setdoc(Path)
    def list(self):
        return [self.join(fn) for fn in os.listdir(str(self))]
    
    @setdoc(Path)
    def isdir(self):
        return os.path.isdir(str(self))
    
    @setdoc(Path)
    def isfile(self):
        return os.path.isfile(str(self))
    
    @setdoc(Path)
    def exists(self):
        return os.path.exists(str(self))
    
    @setdoc(Path)
    def stat(self):
        return os.stat(str(self))
    
    @setdoc(Path)
    def glob(self, pattern):
        return [LocalPath(fn) for fn in glob.glob(str(self.join(pattern)))] 

    @setdoc(Path)
    def delete(self):
        if not self.exists():
            return
        if self.isdir():
            shutil.rmtree(str(self))
        else:
            os.remove(str(self))
    
    @setdoc(Path)
    def move(self, dst):
        if not isinstance(dst, (str, LocalPath)):
            raise TypeError("dst must be a string or a LocalPath")
        shutil.move(str(self), str(dst))
        return LocalPath(dst)
    
    @setdoc(Path)
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
    
    @setdoc(Path)
    def mkdir(self):
        if not self.exists():
            os.makedirs(str(self))
    
    @setdoc(Path)
    def open(self, mode = "r"):
        return open(str(self), mode)
    
    @setdoc(Path)
    def read(self):
        with self.open() as f:
            return f.read()
    
    @setdoc(Path)
    def write(self, data):
        with self.open("w") as f:
            f.write(data)


class Workdir(LocalPath):
    """Working directory manipulator"""
    
    __slots__ = []
    def __init__(self):
        self._path = os.path.normpath(os.getcwd())
    def __hash__(self):
        raise TypeError("unhashable type")
    
    def chdir(self, newdir):
        """Changes the current working directory to the given one
        
        :param newdir: The destination director (a string or a ``LocalPath``)
        """
        if not isinstance(newdir, (str, LocalPath)):
            raise TypeError("newdir must be a string or a LocalPath, not %r" % (newdir,))
        local_logger.debug("Chdir to %s", newdir)
        os.chdir(str(newdir))
        self._path = os.path.normpath(os.getcwd())
    def getpath(self):
        """Returns the current working directory as a ``LocalPath`` object"""
        return LocalPath(self)
    @contextmanager
    def __call__(self, newdir):
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.
        
        :param newdir: The destination director (a string or a ``LocalPath``)
        """
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)

#===================================================================================================
# Environment
#===================================================================================================
class EnvPathList(list):
    __slots__ = ["_path_factory"]
    PATHSEP = os.path.pathsep
    def __init__(self, path_factory):
        self._path_factory = path_factory
    def append(self, path):
        list.append(self, self._path_factory(path))
    def extend(self, paths):
        list.extend(self, (self._path_factory(p) for p in paths))
    def insert(self, index, path):
        list.insert(self, index, self._path_factory(path))
    def index(self, path):
        list.index(self, self._path_factory(path))
    def __contains__(self, path):
        return list.__contains__(self, self._path_factory(path)) 
    def remove(self, path):
        list.remove(self, self._path_factory(path))
    def update(self, text):
        self[:] = [self._path_factory(p) for p in text.split(os.path.pathsep)]
    def join(self):
        return self.PATHSEP.join(str(p) for p in self)


class BaseEnv(object):
    """The base class of LocalEnv and RemoteEnv"""
    __slots__ = ["_curr", "_path", "_path_factory"]
    CASE_SENSITIVE = True

    def __init__(self, path_factory):
        self._path_factory = path_factory
        self._path = EnvPathList(path_factory)
        self._update_path()

    def _update_path(self):
        self._path.update(self.get("PATH", ""))

    @contextmanager
    def __call__(self, *args, **kwargs):
        """A context manager that can be used for temporal modifications of the environment. 
        Any time you enter the context, a copy of the old environment is stored, and then restored,
        when the context exits.
        
        :param args: Any positional arguments for ``update()``
        :param kwargs: Any keyword arguments for ``update()``
        """
        prev = self._curr.copy()
        self.update(**kwargs)
        try:
            yield
        finally:
            self._curr = prev
            self._update_path()

    def __iter__(self):
        """Returns an iterator over the items ``(key, value)`` of current environment 
        (like dict.items)"""
        return iter(self._curr.items())
    def __hash__(self):
        raise TypeError("unhashable type")
    def __len__(self):
        """Returns the number of elements of the current environment"""
        return len(self._curr)
    def __contains__(self, name):
        """Tests whether an environment variable exists in the current environment"""
        return (name if self.CASE_SENSITIVE else name.upper()) in self._curr
    def __getitem__(self, name):
        """Returns the value of the given environment variable from current environment,
        raising a ``KeyError`` if it does not exist"""
        return self._curr[name if self.CASE_SENSITIVE else name.upper()]
    def keys(self):
        """Returns the keys of the current environment (like dict.keys)"""
        return self._curr.keys()
    def items(self):
        """Returns the items of the current environment (like dict.items)"""
        return self._curr.items()
    def values(self):
        """Returns the values of the current environment (like dict.values)"""
        return self._curr.values()
    def get(self, name, *default):
        """Returns the keys of the current environment (like dict.keys)"""
        return self._curr.get((name if self.CASE_SENSITIVE else name.upper()), *default)

    def __delitem__(self, name):
        """Deletes an environment variable from the current environment"""
        name = name if self.CASE_SENSITIVE else name.upper()
        del self._curr[name]
        if name == "PATH":
            self._update_path()
    def __setitem__(self, name, value):
        """Sets/replaces an environment variable's value in the current environment"""
        name = name if self.CASE_SENSITIVE else name.upper()
        self._curr[name] = value
        if name == "PATH":
            self._update_path()    
    def pop(self, name, *default):
        """Pops an element from the current environment (like dict.pop)"""
        name = name if self.CASE_SENSITIVE else name.upper()
        res = self._curr.pop(name, *default)
        if name == "PATH":
            self._update_path()
        return res
    def clear(self):
        """Clears the current environment (like dict.clear)"""
        self._curr.clear()
        self._update_path()
    def update(self, *args, **kwargs):
        """Updates the current environment (like dict.update)"""
        self._curr.update(*args, **kwargs)
        if not self.CASE_SENSITIVE:
            for k, v in list(self._curr.items()):
                self._curr[k.upper()] = v
        self._update_path()

    def getdict(self):
        """Returns the environment as a real dictionary"""
        self._curr["PATH"] = self.path.join()
        return dict((k, str(v)) for k, v in self._curr.items())

    @property
    def path(self):
        """The system's ``PATH`` (as an easy-to-manipulate list)"""
        return self._path

    def _get_home(self):
        if "HOME" in self:
            return self._path_factory(self["HOME"])
        elif "USERPROFILE" in self:
            return self._path_factory(self["USERPROFILE"])
        elif "HOMEPATH" in self:
            return self._path_factory(self.get("HOMEDRIVE", ""), self["HOMEPATH"])
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
    """Get or set the home path"""
    
    @property
    def user(self):
        """Return the user name, or ``None`` if it is not set"""
        if "USER" in self:
            return self["USER"]
        elif "USERNAME" in self:
            return self["USERNAME"]
        return None


class LocalEnv(BaseEnv):
    """The local machine's environment; exposes a dict-like interface"""
    __slots__ = []
    CASE_SENSITIVE = not IS_WIN32
    
    def __init__(self):
        # os.environ already takes care of upper'ing on windows
        self._curr = os.environ.copy()
        BaseEnv.__init__(self, LocalPath)
        if IS_WIN32 and "HOME" not in self and self.home is not None:
            self["HOME"] = self.home
    
    def expand(self, expr):
        """Expands any environment variables and home shortcuts found in ``expr``
        (like ``os.path.expanduser`` combined with ``os.path.expandvars``)
        
        :param expr: An expression containing environment variables (as ``$FOO``) or
                     home shortcuts (as ``~/.bashrc``)
                     
        :returns: The expanded string"""
        prev = os.environ
        os.environ = self.getdict()
        try:
            output = os.path.expanduser(os.path.expandvars(expr))
        finally:
            os.environ = prev
        return output


#===================================================================================================
# Local Commands
#===================================================================================================
class LocalCommand(ConcreteCommand):
    __slots__ = []
    QUOTE_LEVEL = 2
    
    def __init__(self, executable, encoding = "auto"):
        ConcreteCommand.__init__(self, executable, 
            local.encoding if encoding == "auto" else encoding)

    def __repr__(self):
        return "LocalCommand(%r)" % (self.executable,)
    
    def popen(self, args = (), stdin = PIPE, stdout = PIPE, stderr = PIPE, cwd = None, 
            env = None, **kwargs):
        if isinstance(args, str):
            args = (args,)
        if subprocess.mswindows and "startupinfo" not in kwargs and stdin not in (sys.stdin, None):
            kwargs["startupinfo"] = subprocess.STARTUPINFO()
            kwargs["startupinfo"].dwFlags |= subprocess.STARTF_USESHOWWINDOW  #@UndefinedVariable
            kwargs["startupinfo"].wShowWindow = subprocess.SW_HIDE  #@UndefinedVariable
        if cwd is None:
            cwd = getattr(self, "cwd", None)
        if cwd is None:
            cwd = local.cwd

        if env is None:
            env = getattr(self, "env", None)
        if env is None:
            env = local.env
        if hasattr(env, "getdict"):
            env = env.getdict()
        
        argv = self.formulate(0, args)
        local_logger.debug("Running %r", argv)
        proc = Popen(argv, executable = str(self.executable), stdin = stdin, stdout = stdout, 
            stderr = stderr, cwd = str(cwd), env = env, **kwargs) #bufsize = 4096
        proc.encoding = self.encoding
        proc.argv = argv
        return proc

#===================================================================================================
# Local Machine
#===================================================================================================
class LocalMachine(object):
    """The *local machine* (a singleton object). It serves as an entry point to everything
    related to the local machine, such as working directory and environment manipulation,
    command creation, etc.
    
    Attributes:
    
    * ``cwd`` - the local working directory
    * ``env`` - the local environment
    * ``encoding`` - the local machine's default encoding (``sys.getfilesystemencoding()``) 
    """
    cwd = Workdir()
    env = LocalEnv()
    encoding = sys.getfilesystemencoding()

    if IS_WIN32:
        _EXTENSIONS = [""] + env.get("PATHEXT", ":.exe:.bat").lower().split(os.path.pathsep)
        
        @classmethod
        def _which(cls, progname):
            progname = progname.lower()
            for p in cls.env.path:
                try:
                    filelist = dict((n.basename, n) for n in p.list())
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
                    filelist = dict((n.basename, n) for n in p.list())
                except OSError:
                    continue
                if progname in filelist:
                    f = filelist[progname]
                    if not IS_WIN32 and not (f.stat().st_mode & stat.S_IXUSR):
                        continue
                    return f
            return None
    
    @classmethod
    def which(cls, progname):
        """Looks up a program in the ``PATH``. If the program is not found, raises
        :class:`CommandNotFound <plumbum.commands.CommandNotFound>`
        
        :param progname: The program's name. Note that if underscores (``_``) are present
                         in the name, and the exact name is not found, they will be replaced 
                         by hyphens (``-``) and the name will be looked up again
        
        :returns: A :class:`LocalPath <plumbum.local_machine.LocalPath>`
        """
        alternatives = [progname]
        if "_" in progname:
            alternatives.append(progname.replace("_", "-"))
        for pn in alternatives:
            path = cls._which(pn)
            if path:
                return path
        raise CommandNotFound(progname, list(cls.env.path))

    def path(self, *parts):
        """A factory for :class:`LocalPaths <plumbum.local_machine.LocalPath>`. Usage
        
        ::
        
            p = local.path("/usr", "lib", "python2.7")
        """
        return LocalPath(*parts)

    def __getitem__(self, cmd):
        """Returns a `Command` object representing the given program. ``cmd`` can be a string or
        a :class:`LocalPath <plumbum.local_machine.LocalPath>`; if it is a path, a command 
        representing this path will be returned; otherwise, the program name will be looked up 
        in the system's ``PATH`` (using ``which``). Usage::
        
            ls = local["ls"]
        """
        if isinstance(cmd, LocalPath):
            return LocalCommand(cmd)
        elif isinstance(cmd, str): 
            if "/" in cmd or "\\" in cmd:
                # assume path
                return LocalCommand(local.path(cmd))
            else:
                # search for command
                return LocalCommand(self.which(cmd))
        else:
            raise TypeError("cmd must be a LocalPath or a string: %r" % (cmd,))

    def session(self):
        """Creates a new :class:`ShellSession <plumbum.session.ShellSession>` object; this 
        invokes ``/bin/sh`` and executes commands on it over stdin/stdout/stderr"""
        return ShellSession(self["sh"].popen())
    
    @contextmanager
    def tempdir(self):
        """A context manager that creates a temporary directory, which is removed when the context
        exits"""
        dir = self.path(mkdtemp())
        try:
            yield dir
        finally:
            dir.delete()
    
    python = LocalCommand(sys.executable, encoding)
    """A command that represents the current python interpreter (``sys.executable``)"""


local = LocalMachine()
"""The *local machine* (a singleton object). It serves as an entry point to everything
related to the local machine, such as working directory and environment manipulation,
command creation, etc.

Attributes:

* ``cwd`` - the local working directory
* ``env`` - the local environment
* ``encoding`` - the local machine's default encoding (``sys.getfilesystemencoding()``) 
"""

#===================================================================================================
# Module hack: ``from plumbum.cmd import ls``
#===================================================================================================
class LocalModule(ModuleType):
    """The module-hack that allows us to use ``from plumbum.cmd import some_program``"""
    def __init__(self, name):
        ModuleType.__init__(self, name, __doc__)
        self.__file__ = None
        self.__package__ = ".".join(name.split(".")[:-1])
    def __getattr__(self, name):
        return local[name]

LocalModule = LocalModule("plumbum.cmd")
sys.modules[LocalModule.__name__] = LocalModule

