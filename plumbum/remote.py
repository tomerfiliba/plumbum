from plumbum.path import Path
from plumbum.commands import ShellSession, BaseCommand
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
        return RemotePath(self, *parts)
    def list(self):
        return [self / fn for fn in self.remote.session.run("ls", "-a").splitlines()]
    def isdir(self):
        raise NotImplementedError()
    def isfile(self):
        raise NotImplementedError()
    def exists(self):
        raise NotImplementedError()
    def stat(self):
        raise NotImplementedError()
    def glob(self, pattern):
        raise NotImplementedError()
    def delete(self):
        raise NotImplementedError()
    def move(self, dst):
        raise NotImplementedError()
    def copy(self, copy, override = False):
        raise NotImplementedError()
    def mkdir(self):
        raise NotImplementedError()


class RemoteMachine(object):
    def __init__(self):
        self.cwd = "/foo/bar"

r = RemoteMachine()
p = RemotePath(r, "/") #"lala", "baba", "..", "../zaza", "/spam")
print p

exit()



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
    
    def session(self, isatty = False):
        return ShellSession(self.ssh_command.popen(["-tt"] if isatty else []), isatty)
    
    def download(self, src, dst):
        pass
    
    def upload(self, src, dst):
        pass
    
    def tunnel(self, local_port, remote_port):
        pass


class SshCommand(BaseCommand):
    def __init__(self, remote, executable):
        self.remote = remote
        self.executable = executable
    
    def formulate(self, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                argv.extend(a.formulate())
            else:
                argv.append(a)
        return argv
    
    def popen(self, args = (), **kwargs):
        return self.remote.sshctx.popen(args, **kwargs)



