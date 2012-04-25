import weakref
from plumbum.localcmd import local, ChainableCommand, BoundCommand, CommandNotFound, _run
from plumbum.ssh import SshContext, shquote
from contextlib import contextmanager
from plumbum.path import Path


class SshCommand(ChainableCommand):
    def __init__(self, remote, executable):
        self.remote = remote
        self.executable = executable
    def __repr__(self):
        return "<SshCommand %s %s>" % (self.remote.sshctx, self.executable)
    def __str__(self):
        return "%s:%s" % (self.remote.sshctx, self.executable)
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)
    
    def popen(self, args = (), sshopts = {}, **kwargs):
        cmdline = ["cd", self.remote.cwd, "&&", self.executable] + list(args)
        return self.remote.sshctx.popen(cmdline, sshopts, **kwargs)
    def run(self, args = (), retcode = 0, sshopts = {}, **kwargs):
        return _run(self.popen(args, sshopts, **kwargs), retcode)


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
        return str(self.remote.sshctx)
    def listdir(self, p):
        files = self.remote.session.run("ls -a %s" % (shquote(p),))[1].splitlines()
        if "." in files:
            files.remove(".")
        if ".." in files:
            files.remove("..")
        return files
    def chdir(self, p):
        self.remote.cwd.chdir(p)
    def isdir(self, p):
        pass
    def isfile(self, p):
        #self.stat(p).st_mode
        pass
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
        return "<Workdir %s%s>" % (self.remote.sshctx, self)
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
        return self.remote.path(str(self))
    def chdir(self, dir):
        dir = str(dir)
        self._remote.session.run("cd %s" % (shquote(dir),))
        self._dirstack[-1] = dir


class RemoteEnv(object):
    def __init__(self, remote):
        self._remote = remote


class RemoteCommandNamespace(object):
    def __init__(self, sshctx):
        self.sshctx = sshctx
        self.session = sshctx.shell()
        self._location = RemotePathLocation(weakref.proxy(self))
        self.cwd = RemoteWorkdir(weakref.proxy(self))
        self.env = RemoteEnv(weakref.proxy(self))
    
    def __enter__(self):
        pass
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self.session.close()
    def path(self, *parts):
        return Path(self._location, *parts)
    
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

    with local.env(HOME = local.env.home):
        sshctx = SshContext("hollywood.xiv.ibm.com")
        remote = RemoteCommandNamespace(sshctx)
        r_ls = remote["ls"]
        
        print remote.cwd
        
        for fn in remote.cwd:
            print fn
        
        exit()
        print r_ls("-l")
        with remote.cwd("/"):
            print r_ls("-l")
        print r_ls("-l")




