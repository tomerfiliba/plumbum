import os
import errno
from contextlib import contextmanager
from plumbum.path import Path
from plumbum.commands import CommandNotFound, shquote, ConcreteCommand
from plumbum.session import ShellSession
from plumbum.local_machine import local, BaseEnv, EnvPathList


class RemotePath(Path):
    __slots__ = ["_path", "remote"]
    def __init__(self, remote, *parts):
        self.remote = remote
        normed = []
        parts = (self.remote.cwd,) + parts
        for p in parts:
            plist = str(p).replace("\\", "/").split("/")
            if not plist[0]:
                plist.pop(0)
                del normed[:]
            for item in plist:
                if item == "" or item == ".":
                    continue
                if item == "..":
                    if normed:
                        normed.pop(-1)
                else:
                    normed.append(item)
        self._path = "/" + "/".join(normed)
    
    def __str__(self):
        return self._path
    
    @property
    def basename(self):
        if not "/" in str(self):
            return str(self)
        return str(self).rsplit("/", 1)[1]
    @property
    def dirname(self):
        if not "/" in str(self):
            return str(self)
        return str(self).rsplit("/", 1)[0]
    
    def _get_info(self):
        return (self.remote, self._path)
    def join(self, *parts):
        return RemotePath(self.remote, self, *parts)
    def list(self):
        if not self.isdir():
            return []
        files = self.remote._session.run("ls -a %s" % (self,))[1].splitlines()
        files.remove(".")
        files.remove("..")
        return [self.join(fn) for fn in files]
    
    def isdir(self):
        res = self._stat()
        if not res:
            return False
        return res[0] in ("directory")
    def isfile(self):
        res = self._stat()
        if not res:
            return False
        return res[0] in ("regular file", "regular empty file")
    def exists(self):
        return self._stat() is not None
    
    def _stat(self):
        rc, out, _ = self.remote._session.run(
            "stat -c '%F,%f,%i,%d,%h,%u,%g,%s,%X,%Y,%Z' " + shquote(self), retcode = None)
        if rc != 0:
            return None
        statres = out.strip().split(",")
        mode = statres.pop(0).lower()
        return mode, os.stat_result(statres)
    
    def stat(self):
        res = self._stat()
        if res is None:
            raise OSError(errno.ENOENT)
        return res[1]
    
    def glob(self, pattern):
        matches = self.remote._session.run("for fn in %s/%s; do echo $fn; done" % (self, pattern))[1].splitlines()
        if len(matches) == 1 and not self._stat(matches[0]):
            return [] # pattern expansion failed
        return [RemotePath(self.remote, m) for m in matches]
    
    def delete(self):
        if not self.exists():
            return
        self.remote._session.run("rm -rf %s" % (shquote(self),))
    def move(self, dst):
        if isinstance(dst, RemotePath) and dst.remote is not self.remote:
            raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine)")
        self.remote._session.run("mv %s %s" % (shquote(self), shquote(dst)))
    def copy(self, dst, override = False):
        if isinstance(dst, RemotePath):
            if dst.remote is not self.remote:
                raise TypeError("dst points to a different remote machine")
        elif not isinstance(dst, str):
            raise TypeError("dst must be a string or a RemotePath (to the same remote machine)", repr(dst))
        if override:
            if isinstance(dst, str):
                dst = RemotePath(self.remote, dst)
            dst.remove()
        self.remote._session.run("cp -r %s %s" % (shquote(self), shquote(dst)))
    def mkdir(self):
        self.remote._session.run("mkdir -p %s" % (shquote(self),))

class Workdir(RemotePath):
    def __init__(self, remote):
        self.remote = remote
        self._path = self.remote._session.run("pwd")[1].strip()
    def __hash__(self):
        raise TypeError("unhashable type")
    
    def chdir(self, newdir):
        self.remote._session.run("cd %s" % (shquote(newdir),))
        self._path = self.remote._session.run("pwd")[1].strip()
    def getpath(self):
        return RemotePath(self.remote, self)
    @contextmanager
    def __call__(self, newdir):
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)

class RemoteEnv(BaseEnv):
    __slots__ = ["_orig", "remote"]
    def __init__(self, remote):
        self.remote = remote
        self._curr = dict(line.split("=",1) for line in self.remote._session.run("env")[1].splitlines())
        self._orig = self._curr.copy()
        BaseEnv.__init__(self, self.remote.path)

    def __delitem__(self, name):
        BaseEnv.__delitem__(self, name)
        self.remote._session.run("unset %s" % (name,))
    def __setitem__(self, name, value):
        BaseEnv.__setitem__(self, name, value)
        self.remote._session.run("export %s=%s" % (name, shquote(value)))
    def pop(self, name, *default):
        BaseEnv.pop(self, name, *default)
        self.remote._session.run("unset %s" % (name,))
    def update(self, *args, **kwargs):
        BaseEnv.update(self, *args, **kwargs)
        self.remote._session.run("export " + 
            " ".join("%s=%s" % (k, shquote(v)) for k, v in self.getdict().items()))

    #def clear(self):
    #    BaseEnv.clear(self, *args, **kwargs)
    #    self.remote._session.run("export %s" % " ".join("%s=%s" % (k, v) for k, v in self.getdict()))

    def getdelta(self):
        self._curr["PATH"] = self.path.join()
        delta = {}
        for k, v in self._curr.items():
            if k not in self._orig:
                delta[k] = str(v)
        for k, v in self._orig.items():
            if k not in self._curr:
                delta[k] = ""
        return delta


class SshCommand(ConcreteCommand):
    __slots__ = ["remote", "executable"]
    QUOTE_LEVEL = 1
    
    def __init__(self, remote, executable, encoding = "auto"):
        self.remote = remote
        ConcreteCommand.__init__(self, executable, 
            remote.encoding if encoding == "auto" else encoding)

    def __repr__(self):
        return "RemoteCommand(%r, %r)" % (self.remote, self.executable)
    
    def popen(self, args = (), **kwargs):
        #cmdline = ["%s = %s" % (k, v) for k, v in self.remote.env.getdelta().items()]
        #cmdline.extend(("cd", str(self.remote.cwd), "&&", self[args]))
        return self.remote.popen(self[args], **kwargs)


class BaseRemoteMachine(object):
    def __init__(self, encoding = "utf8"):
        self.encoding = encoding
        self._session = self.session()
        rc, out, _ = self._session.run("uname", retcode = None)
        if rc == 0:
            self.uname = out.strip()
        else:
            self.uname = None
        
        self.cwd = Workdir(self)
        self.env = RemoteEnv(self)
        self._python = None

    def __repr__(self):
        return "<RemoteMachine %s>" % (self,)

    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self._session.close()
    
    def path(self, *parts):
        return RemotePath(self, *parts)
    
    def which(self, progname):
        rc, out, _ = self._session.run("which %s" % (shquote(progname),), retcode = None)
        if rc == 0:
            return self.path(out.strip())
        raise CommandNotFound(progname, self.env.path)
    
    def __getitem__(self, cmd):
        if isinstance(cmd, RemotePath):
            if cmd.remote is self:
                return SshCommand(self, cmd)
            else:
                raise TypeError("Given path does not belong to this remote machine: %r" % (cmd,))
        elif isinstance(cmd, str):
            if "/" in cmd or "\\" in cmd:
                return SshCommand(self, self.path(cmd))
            else:
                return SshCommand(self, self.which(cmd))
        else:
            raise TypeError("cmd must be a path or a string: %r" % (cmd,))

    @property
    def python(self):
        if not self._python:
            self._python = self["python"]
        return self._python

    def session(self, isatty = False):
        raise NotImplementedError()
    def download(self, src, dst):
        raise NotImplementedError()
    def upload(self, src, dst):
        raise NotImplementedError()
    def popen(self, args = (), **kwargs):
        raise NotImplementedError

    @contextmanager
    def tempdir(self):
        _, out, _ = self._session.run("mktemp -d")
        dir = self.path(out.strip())
        try:
            yield dir
        finally:
            dir.delete()


class SshTunnel(object):
    __slots__ = ["_session"]
    def __init__(self, session):
        self._session = session
    def __repr__(self):
        if self._session.alive():
            return "<SshTunnel %s>" % (self._session.proc,)
        else:
            return "<SshTunnel (defunct)>"
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self._session.close()

class SshMachine(BaseRemoteMachine):
    def __init__(self, host, user = None, port = None, keyfile = None, ssh_command = None, 
            scp_command = None, ssh_opts = (), scp_opts = ()):
        if ssh_command is None:
            ssh_command = local["ssh"]
        if scp_command is None:
            scp_command = local["scp"]
        if user:
            self._fqhost = "%s@%s" % (user, host)
        else:
            self._fqhost = host
        scp_args = []
        ssh_args = []
        if port:
            ssh_args.extend(["-p", port])
            scp_args.extend(["-P", port])
        if keyfile:
            ssh_args.extend(["-i", keyfile])
            scp_args.extend(["-i", keyfile])
        scp_args.append("-r")
        ssh_args.extend(ssh_opts)
        scp_args.extend(scp_opts)
        self._ssh_command = ssh_command[tuple(ssh_args)]
        self._scp_command = scp_command[tuple(scp_args)]
        BaseRemoteMachine.__init__(self)

    def __str__(self):
        return "ssh://%s" % (self._fqhost,)

    def popen(self, args, ssh_opts = (), **kwargs):
        cmdline = []
        cmdline.extend(ssh_opts)
        cmdline.append(self._fqhost)
        if args:
            envdelta = self.env.getdelta()
            cmdline.extend(["cd", str(self.cwd), "&&"])
            if envdelta:
                cmdline.append("env")
                cmdline.extend("%s=%s" % (k, v) for k, v in envdelta.items())
            if isinstance(args, (tuple, list)):
                cmdline.extend(args)
            else:
                cmdline.append(args)
        return self._ssh_command[tuple(cmdline)].popen(**kwargs)
    
    def session(self, isatty = False):
        return ShellSession(self.popen((), ["-tt"] if isatty else []), self.encoding, isatty)
    def tunnel(self, lport, rport, lhost = "localhost", rhost = "localhost"):
        opts = ["-L", "[%s]:%s:[%s]:%s" % (lhost, lport, rhost, rport)]
        return SshTunnel(ShellSession(self.popen((), opts), self.encoding))        
    
    def download(self, src, dst):
        self._scp_command("%s:%s" % (self._fqhost, src), dst)
    def upload(self, src, dst):
        self._scp_command(src, "%s:%s" % (self._fqhost, dst))




