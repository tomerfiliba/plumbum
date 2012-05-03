import os
import errno
from contextlib import contextmanager
from plumbum.path import Path
from plumbum.commands import BaseCommand, CommandNotFound, run_proc, shquote, shquote_list
from plumbum.session import ShellSession
from plumbum.local import local


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
        return str(self).rsplit("/", 1)[0]
    @property
    def dirname(self):
        raise NotImplementedError()
    
    def _get_info(self):
        return (self.remote, self._path)
    def join(self, *parts):
        return RemotePath(self.remote, self, *parts)
    def list(self):
        if not self.isdir():
            return []
        return [self.join(fn) for fn in self.remote.session.run("ls -a %s" % (self,))[1].splitlines()]
    
    def isdir(self):
        mode, _ = self._stat()
        return mode in ("directory")
    def isfile(self):
        mode, _ = self._stat()
        return mode in ("regular file", "regular empty file")
    def exists(self):
        return self._stat() is not None
    
    def _stat(self):
        rc, out, _ = self.remote.session.run(
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
        matches = self.remote.session.run("for fn in %s/%s; do echo $fn; done" % (self, pattern))[1].splitlines()
        if len(matches) == 1 and not self._stat(matches[0]):
            return [] # pattern expansion failed
        return [RemotePath(self.remote, m) for m in matches]
    
    def delete(self):
        if not self.exists():
            return
        self.remote.session.run("rm -rf %s" % (shquote(self),))
    def move(self, dst):
        self.remote.session.run("mv %s %s" % (shquote(self), shquote(dst)))
    def copy(self, dst, override = False):
        self.remote.session.run("cp -r %s %s" % (shquote(self), shquote(dst)))
    def mkdir(self):
        self.remote.session.run("mkdir -p %s" % (shquote(self),))

class Workdir(RemotePath):
    __slots__ = []
    def __init__(self, remote):
        self.remote = remote
        self._path = self.remote.session.run("pwd")[1].strip()
    def __hash__(self):
        raise TypeError("unhashable type")
    
    def chdir(self, newdir):
        self.remote.session.run("cd %s" % (shquote(newdir),))
        self._path = self.remote.session.run("pwd")[1].strip()
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

class Env(object):
    __slots__ = ["remote", "_curr"]
    def __init__(self, remote):
        self.remote = remote
        self._curr = dict(line.split("=",1) for line in self.remote.session.run("env")[1].splitlines())
    def __contains__(self, name):
        return name in self._curr
    def __getitem__(self, name):
        return self._curr[name]
    @property
    def path(self):
        return self.get("PATH", "").split(os.path.pathsep)


class SshTunnel(object):
    __slots__ = []
    def __init__(self, session):
        self.session = session
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        self.session.close()

class SshContext(object):
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
        ssh_args = [self._fqhost]
        if port:
            ssh_args.extend(["-p", port])
            scp_args.extend(["-P", port])
        if keyfile:
            ssh_args.extend(["-i", keyfile])
            scp_args.extend(["-i", keyfile])
        scp_args.append("-r")
        ssh_args.extend(ssh_opts)
        scp_args.extend(scp_opts)
        self.ssh_command = ssh_command[tuple(ssh_args)]
        self.scp_command = scp_command[tuple(scp_args)]
    
    def __str__(self):
        return "ssh://%s" % (self._fqhost,)
    def __repr__(self):
        return "<SshContext %r>" % (self._fqhost,)
    def __getitem__(self, args):
        return self.ssh_command[args]
    
    def popen(self, args = (), ssh_opts = (), **kwargs):
        if isinstance(args, str):
            args = (args,)
        return self.ssh_command[tuple(ssh_opts) + tuple(args)].popen()
    def run(self, args = (), ssh_opts = (), retcode = 0, **kwargs):
        return run_proc(self.popen(args, ssh_opts, **kwargs), retcode)
    
    def session(self, isatty = False):
        return ShellSession(self.popen("-tt" if isatty else ""), isatty)
    def download(self, src, dst):
        self.scp_command("%s:%s" % (self._fqdn, src), dst)
    def upload(self, src, dst):
        self.scp_command(src, "%s:%s" % (self._fqdn, dst))
    def tunnel(self, lport, rport, lhost = "localhost", rhost = "localhost"):
        return SshTunnel(ShellSession(self.popen(
            "-L", "[%s]:%s:[%s]:%s" % (lhost, lport, rhost, rport))
            ))

class SshCommand(BaseCommand):
    def __init__(self, remote, executable):
        self.remote = remote
        self.executable = executable

    def __repr__(self):
        return "RemoteCommand(%r, %r)" % (self.remote, self.executable)
    
    def formulate(self, level = 0, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                if level >= 1:
                    argv.extend(shquote_list(a.formulate(level + 1)))
                else:
                    argv.extend(a.formulate(level + 1))
            else:
                if level >= 1:
                    argv.append(shquote(a))
                else:
                    argv.append(a)
        return argv
    
    def popen(self, args = (), **kwargs):
        return self.remote.sshctx.ssh_command[self[args]].popen()


class RemoteMachine(object):
    def __init__(self, sshctx):
        self.sshctx = sshctx
        self.session = sshctx.session()
        rc, out, _ = self.session.run("uname", retcode = None)
        if rc == 0:
            self.uname = out.strip()
        else:
            self.uname = ""
        
        self.cwd = Workdir(self)
        self.env = Env(self)
        self._python = None

    @classmethod
    def connect(self, host, **kwargs):
        return RemoteMachine(SshContext(host, **kwargs))

    def __repr__(self):
        return "RemoteMachine(%r)" % (self.sshctx,)
    
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        if self.session:
            self.session.close()
            self.session = None
    
    def path(self, *parts):
        return RemotePath(self, *parts)
    
    def which(self, progname):
        rc, out, _ = self.session.run("which %s" % (shquote(progname),), retcode = None)
        if rc == 0:
            return self.path(out.strip())
        raise CommandNotFound(progname, self.env.path)
    
    def __getitem__(self, cmd):
        if isinstance(cmd, RemotePath):
            if cmd.remote is self:
                return SshCommand(self, cmd)
            else:
                raise 
        elif isinstance(cmd, Path):
            raise
        elif isinstance(cmd, str):
            if "/" in cmd or "\\" in cmd:
                return SshCommand(self, self.path(cmd))
            else:
                return SshCommand(self, self.which(cmd))
    
    @property
    def python(self):
        if not self._python:
            self._python = self["python"]
        return self._python




if __name__ == "__main__":
    #import logging
    #logging.basicConfig(level = logging.DEBUG)
    with RemoteMachine.connect("localhost") as r:
        #r.cwd.chdir(r.cwd / "workspace" / "plumbum")
        #print r.cwd // "*/*.py"
        r_ssh = r["ssh"]
        r_ls = r["ls"]
        r_grep = r["grep"]

        print (r_ssh["localhost", r_ls | r_grep["hs"]])()
        











