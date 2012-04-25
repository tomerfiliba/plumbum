import weakref
from plumbum.localcmd import local, ChainableCommand, BoundCommand, CommandNotFound, _run
from plumbum.ssh import SshContext, shquote
from contextlib import contextmanager


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


class RemoteCwd(object):
    def __init__(self, remote):
        self._remote = remote
        self._dirstack = [self._remote.session.run("pwd")[1].strip()]

    def __str__(self):
        return str(self._dirstack[-1])
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
    def chdir(self, dir):
        self._remote.session.run("cd %s" % (shquote(dir),))
        self._dirstack[-1] = dir


class RemoteEnv(object):
    def __init__(self, remote):
        self._remote = remote


class RemoteCommandNamespace(object):
    def __init__(self, sshctx):
        self.sshctx = sshctx
        self.session = sshctx.shell()
        self.cwd = RemoteCwd(weakref.proxy(self))
        self.env = RemoteEnv(weakref.proxy(self))
    
    def __enter__(self):
        pass
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self.session.close()
    
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
        
        print r_ls("-l")
        with remote.cwd("/"):
            print r_ls("-l")
        print r_ls("-l")




