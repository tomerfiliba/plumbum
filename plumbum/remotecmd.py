import os
import weakref
from contextlib import contextmanager
from plumbum.base import CommandNotFound, IS_WIN32, shquote, ExecutionModifier
from plumbum.localcmd import ChainableCommand, BoundCommand, run_proc
from plumbum.ssh import SshContext
from plumbum.path import Path


class SshCommand(ChainableCommand):
    def __init__(self, remote, executable):
        self.remote = remote
        self.cwd = self.remote.cwd
        self.executable = executable
    def __repr__(self):
        return "<SshCommand %s %s>" % (self.remote.sshctx, self.executable)
    def __str__(self):
        return "%s:%s" % (self.remote.sshctx, self.executable)
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)

    def formulate(self, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if hasattr(a, "formulate"):
                argv.extend(shquote(b) for b in a.formulate())
            else:
                argv.append(shquote(str(a)))
        return argv
    
    def popen(self, args = (), sshopts = {}, **kwargs):
        return self.remote.sshctx.popen(["cd", shquote(str(self.cwd)), "&&"] + self.formulate(args), 
            sshopts, **kwargs)
    def run(self, args = (), retcode = 0, sshopts = {}, **kwargs):
        return run_proc(self.popen(args, sshopts, **kwargs), retcode)


class RemotePathLocation(object):
    def __init__(self, remote):
        self.remote = remote
    def __eq__(self, other):
        if isinstance(other, RemotePathLocation):
            return self.remote == other.remote
        return False
    def __ne__(self, other):
        return not (self == other)
    def __str__(self):
        return "%s/" % (self.remote.sshctx,)
    def listdir(self, p):
        files = self.remote.session.run("ls -a %s" % (shquote(p),))[1].splitlines()
        if "." in files:
            files.remove(".")
        if ".." in files:
            files.remove("..")
        return files
    def normpath(self, parts):
        joined = os.path.join(str(self.remote.cwd), *(str(p) for p in parts))
        if IS_WIN32 and "/" in joined: # assume remote path is posix and fix all backslashes
            joined = joined.replace("\\", "/")
        return joined 
    
    def chdir(self, p):
        self.remote.cwd.chdir(p)
    def isdir(self, p):
        res = self._stat(p)
        if not res:
            return False
    def isfile(self, p):
        res = self._stat(p)
        if not res:
            return False
        #return stat.S_ISREG(.st_mode)
    def exists(self, p):
        return self._stat(p) is not None
    def _stat(self, p):
        rc, out, _ = self.remote.session.run("stat %s" % (shquote(p),), retcode = None)
        if rc == 0:
            return out.strip()
        else:
            return None
    def stat(self, p):
        res = self._stat(p)
        return res
    def glob(self, p):
        matches = self.remote.session.run("for fn in %s; do echo $fn; done" % (p,))[1].splitlines()
        if len(matches) == 1 and not self._stat(matches[0]):
            return () # pattern expansion failed
        return matches

class RemoteWorkdir(Path):
    def __init__(self, remote):
        self._location = remote._location
        self._remote = remote
        self._dirstack = [self._remote.session.run("pwd")[1].strip()]

    def __str__(self):
        return str(self._path)
    @property
    def _path(self):
        return self._dirstack[-1]
    def __repr__(self):
        return "<Workdir %s%s>" % (self._remote.sshctx, self)
    def __hash__(self):
        raise TypeError("Workdir can change and is unhashable")
    
    @contextmanager
    def __call__(self, dir):
        self._dirstack.append(None)
        self.chdir(dir)
        try:
            yield
        finally:
            self._dirstack.pop(-1)
            self.chdir(self._dirstack[-1])
    
    def getpath(self):
        return self._remote.path(str(self))
    def chdir(self, dir):
        dir = str(dir)
        self._remote.session.run("cd %s" % (shquote(dir),))
        self._dirstack[-1] = dir


class RemoteEnv(object):
    def __init__(self, remote):
        self._remote = remote


class Remote(object):
    def __init__(self, sshctx):
        self.sshctx = sshctx
        self.session = sshctx.shell()
        self._location = RemotePathLocation(weakref.proxy(self))
        self.cwd = RemoteWorkdir(weakref.proxy(self))
        self.env = RemoteEnv(weakref.proxy(self))
    
    @classmethod
    def connect(cls, *args, **kwargs):
        return cls(SshContext(*args, **kwargs))
    
    def __enter__(self):
        pass
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self.session.close()
    def path(self, *parts):
        return Path(self._location, *parts)
    
    def run(self, cmd, *args):
        return self.sshctx.run(cmd.formulate(args))
    
    def run_session(self, cmd, *args):
        return self.session.run(" ".join(cmd.formulate(args)))
    
    def tunnel(self, *args, **kwargs):
        return self.sshctx.tunnel(*args, **kwargs)
    
    def which(self, progname):
        rc, out, err = self.session.run("which %s" % (shquote(progname),), retcode = None)
        if rc == 0:
            return out.strip()
        else:
            raise CommandNotFound(progname, err)
    
    def __getitem__(self, progname):
        progname = str(progname)
        if "/" not in progname and "\\" not in progname:
            progname = self.which(progname)
        return SshCommand(self, progname)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    r = Remote.connect("localhost")
    r_ls = r["ls"]
    r_grep = r["grep"]
    r_sudo = r["sudo"]
    r_ssh = r["ssh"]
    
    print r.run(r_ls | r_grep["h"])



