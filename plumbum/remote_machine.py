from __future__ import with_statement
from contextlib import contextmanager
from plumbum.remote_path import RemotePath
from plumbum.commands import CommandNotFound, shquote, ConcreteCommand
from plumbum.session import ShellSession
from plumbum.lib import _setdoc
from plumbum.local_machine import local, BaseEnv, LocalPath


class Workdir(RemotePath):
    """Remote working directory manipulator"""

    def __init__(self, remote):
        self.remote = remote
        self._path = self.remote._session.run("pwd")[1].strip()
    def __hash__(self):
        raise TypeError("unhashable type")

    def chdir(self, newdir):
        """Changes the current working directory to the given one"""
        self.remote._session.run("cd %s" % (shquote(newdir),))
        self._path = self.remote._session.run("pwd")[1].strip()

    def getpath(self):
        """Returns the current working directory as a
        `remote path <plumbum.remote_machine.RemotePath>` object"""
        return RemotePath(self.remote, self)

    @contextmanager
    def __call__(self, newdir):
        """A context manager used to ``chdir`` into a directory and then ``chdir`` back to
        the previous location; much like ``pushd``/``popd``.

        :param newdir: The destination director (a string or a
                       :class:`RemotePath <plumbum.remote_machine.RemotePath>`)
        """
        prev = self._path
        self.chdir(newdir)
        try:
            yield
        finally:
            self.chdir(prev)

class RemoteEnv(BaseEnv):
    """The remote machine's environment; exposes a dict-like interface"""

    __slots__ = ["_orig", "remote"]
    def __init__(self, remote):
        self.remote = remote
        self._curr = dict(line.split("=",1) for line in self.remote._session.run("env")[1].splitlines())
        self._orig = self._curr.copy()
        BaseEnv.__init__(self, self.remote.path)

    @_setdoc(BaseEnv)
    def __delitem__(self, name):
        BaseEnv.__delitem__(self, name)
        self.remote._session.run("unset %s" % (name,))
    @_setdoc(BaseEnv)
    def __setitem__(self, name, value):
        BaseEnv.__setitem__(self, name, value)
        self.remote._session.run("export %s=%s" % (name, shquote(value)))
    @_setdoc(BaseEnv)
    def pop(self, name, *default):
        BaseEnv.pop(self, name, *default)
        self.remote._session.run("unset %s" % (name,))
    @_setdoc(BaseEnv)
    def update(self, *args, **kwargs):
        BaseEnv.update(self, *args, **kwargs)
        self.remote._session.run("export " +
            " ".join("%s=%s" % (k, shquote(v)) for k, v in self.getdict().items()))

    def expand(self, expr):
        """Expands any environment variables and home shortcuts found in ``expr``
        (like ``os.path.expanduser`` combined with ``os.path.expandvars``)

        :param expr: An expression containing environment variables (as ``$FOO``) or
                     home shortcuts (as ``~/.bashrc``)

        :returns: The expanded string"""
        return self.remote._session.run("echo %s" % (expr,))

    def expanduser(self, expr):
        """Expand home shortcuts (e.g., ``~/foo/bar`` or ``~john/foo/bar``)

        :param expr: An expression containing home shortcuts

        :returns: The expanded string"""
        if not any(part.startwith("~") for part in expr.split("/")):
            return expr
        # we escape all $ signs to avoid expanding env-vars
        return self.remote._session.run("echo %s" % (expr.replace("$", "\\$"),))

    #def clear(self):
    #    BaseEnv.clear(self, *args, **kwargs)
    #    self.remote._session.run("export %s" % " ".join("%s=%s" % (k, v) for k, v in self.getdict()))

    def getdelta(self):
        """Returns the difference between the this environment and the original environment of
        the remote machine"""
        self._curr["PATH"] = self.path.join()
        delta = {}
        for k, v in self._curr.items():
            if k not in self._orig:
                delta[k] = str(v)
        for k, v in self._orig.items():
            if k not in self._curr:
                delta[k] = ""
        return delta


class RemoteCommand(ConcreteCommand):
    __slots__ = ["remote", "executable"]
    QUOTE_LEVEL = 1

    def __init__(self, remote, executable, encoding = "auto"):
        self.remote = remote
        ConcreteCommand.__init__(self, executable,
            remote.encoding if encoding == "auto" else encoding)
    def __repr__(self):
        return "RemoteCommand(%r, %r)" % (self.remote, self.executable)
    def popen(self, args = (), **kwargs):
        return self.remote.popen(self[args], **kwargs)

class ClosedRemoteMachine(Exception):
    pass

class ClosedRemote(object):
    __slots__ = ["_obj"]
    def __init__(self, obj):
        self._obj = obj
    def close(self):
        pass
    def __getattr__(self, name):
        raise ClosedRemoteMachine("%r has been closed" % (self._obj,))


class BaseRemoteMachine(object):
    """Represents a *remote machine*; serves as an entry point to everything related to that
    remote machine, such as working directory and environment manipulation, command creation,
    etc.

    Attributes:

    * ``cwd`` - the remote working directory
    * ``env`` - the remote environment
    * ``encoding`` - the remote machine's default encoding (assumed to be UTF8)
    """

    def __init__(self, encoding = "utf8"):
        self.encoding = encoding
        self._session = self.session()
        self.uname = self._get_uname()
        self.cwd = Workdir(self)
        self.env = RemoteEnv(self)
        self._python = None

    def _get_uname(self):
        rc, out, _ = self._session.run("uname", retcode = None)
        if rc == 0:
            return out.strip()
        else:
            rc, out, _ = self._session.run("python -c 'import platform;print(platform.uname()[0])'", retcode = None)
            if rc == 0:
                return out.strip()
            else:
                # all POSIX systems should have uname. make an educated guess it's Windows
                return "Windows"

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self)

    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        """closes the connection to the remote machine; all paths and programs will
        become defunct"""
        self._session.close()
        self._session = ClosedRemote(self)

    def path(self, *parts):
        """A factory for :class:`RemotePaths <plumbum.remote_machine.RemotePath>`.
        Usage: ``p = rem.path("/usr", "lib", "python2.7")``
        """
        parts2 = [str(self.cwd)]
        for p in parts:
            if isinstance(p, LocalPath):
                raise TypeError("Cannot construct RemotePath from %r" % (p,))
            p = str(p)
            if "~" in p:
                p = self.env.expanduser(p)
            parts2.append(p)
        return RemotePath(self, *parts2)

    def which(self, progname):
        """Looks up a program in the ``PATH``. If the program is not found, raises
        :class:`CommandNotFound <plumbum.commands.CommandNotFound>`

        :param progname: The program's name. Note that if underscores (``_``) are present
                         in the name, and the exact name is not found, they will be replaced
                         by hyphens (``-``) and the name will be looked up again

        :returns: A :class:`RemotePath <plumbum.local_machine.RemotePath>`
        """
        alternatives = [progname]
        if "_" in progname:
            alternatives.append(progname.replace("_", "-"))
        for name in alternatives:
            rc, out, _ = self._session.run("which %s" % (shquote(name),), retcode = None)
            if rc == 0:
                return self.path(out.strip())

        raise CommandNotFound(progname, self.env.path)

    def __getitem__(self, cmd):
        """Returns a `Command` object representing the given program. ``cmd`` can be a string or
        a :class:`RemotePath <plumbum.remote_machine.RemotePath>`; if it is a path, a command
        representing this path will be returned; otherwise, the program name will be looked up in
        the system's ``PATH`` (using ``which``). Usage::

            r_ls = rem["ls"]
        """
        if isinstance(cmd, RemotePath):
            if cmd.remote is self:
                return RemoteCommand(self, cmd)
            else:
                raise TypeError("Given path does not belong to this remote machine: %r" % (cmd,))
        elif not isinstance(cmd, LocalPath):
            if "/" in cmd or "\\" in cmd:
                return RemoteCommand(self, self.path(cmd))
            else:
                return RemoteCommand(self, self.which(cmd))
        else:
            raise TypeError("cmd must not be a LocalPath: %r" % (cmd,))

    @property
    def python(self):
        """A command that represents the default remote python interpreter"""
        if not self._python:
            self._python = self["python"]
        return self._python

    def session(self, isatty = False):
        """Creates a new :class:`ShellSession <plumbum.session.ShellSession>` object; this invokes the user's
        shell on the remote machine and executes commands on it over stdin/stdout/stderr"""
        raise NotImplementedError()

    def download(self, src, dst):
        """Downloads a remote file/directory (``src``) to a local destination (``dst``).
        ``src`` must be a string or a :class:`RemotePath <plumbum.remote_machine.RemotePath>`
        pointing to this remote machine, and ``dst`` must be a string or a
        :class:`LocalPath <plumbum.local_machine.LocalPath>`"""
        raise NotImplementedError()

    def upload(self, src, dst):
        """Uploads a local file/directory (``src``) to a remote destination (``dst``).
        ``src`` must be a string or a :class:`LocalPath <plumbum.local_machine.LocalPath>`,
        and ``dst`` must be a string or a :class:`RemotePath <plumbum.remote_machine.RemotePath>`
        pointing to this remote machine"""
        raise NotImplementedError()

    def popen(self, args, **kwargs):
        """Spawns the given command on the remote machine, returning a ``Popen``-like object;
        do not use this method directly, unless you need "low-level" control on the remote
        process"""
        raise NotImplementedError()

    @contextmanager
    def tempdir(self):
        """A context manager that creates a remote temporary directory, which is removed when
        the context exits"""
        _, out, _ = self._session.run("mktemp -d")
        dir = self.path(out.strip()) #@ReservedAssignment
        try:
            yield dir
        finally:
            dir.delete()


class SshTunnel(object):
    """An object representing an SSH tunnel (created by
    :func:`SshMachine.tunnel <plumbum.remote_machine.SshMachine.tunnel>`)"""
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
        """Closes(terminates) the tunnel"""
        self._session.close()


class SshMachine(BaseRemoteMachine):
    """
    An implementation of :class:`remote machine <plumbum.remote_machine.BaseRemoteMachine>`
    over SSH. Invoking a remote command translates to invoking it over SSH ::

        with SshMachine("yourhostname") as rem:
            r_ls = rem["ls"]
            # r_ls is the remote `ls`
            # executing r_ls() translates to `ssh yourhostname ls`

    :param host: the host name to connect to (SSH server)

    :param user: the user to connect as (if ``None``, the default will be used)

    :param port: the server's port (if ``None``, the default will be used)

    :param keyfile: the path to the identity file (if ``None``, the default will be used)

    :param ssh_command: the ``ssh`` command to use; this has to be a ``Command`` object;
                        if ``None``, the default ssh client will be used.

    :param scp_command: the ``scp`` command to use; this has to be a ``Command`` object;
                        if ``None``, the default scp program will be used.

    :param ssh_opts: any additional options for ``ssh`` (a list of strings)

    :param scp_opts: any additional options for ``scp`` (a list of strings)

    :param encoding: the remote machine's encoding (defaults to UTF8)
    """

    def __init__(self, host, user = None, port = None, keyfile = None, ssh_command = None,
            scp_command = None, ssh_opts = (), scp_opts = (), encoding = "utf8"):
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
            ssh_args.extend(["-p", str(port)])
            scp_args.extend(["-P", str(port)])
        if keyfile:
            ssh_args.extend(["-i", str(keyfile)])
            scp_args.extend(["-i", str(keyfile)])
        scp_args.append("-r")
        ssh_args.extend(ssh_opts)
        scp_args.extend(scp_opts)
        self._ssh_command = ssh_command[tuple(ssh_args)]
        self._scp_command = scp_command[tuple(scp_args)]
        BaseRemoteMachine.__init__(self, encoding)

    def __str__(self):
        return "ssh://%s" % (self._fqhost,)

    @_setdoc(BaseRemoteMachine)
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

    @_setdoc(BaseRemoteMachine)
    def session(self, isatty = False):
        return ShellSession(self.popen((), ["-tt"] if isatty else ["-T"]), self.encoding, isatty)

    def tunnel(self, lport, dport, lhost = "localhost", dhost = "localhost"):
        r"""Creates an SSH tunnel from the TCP port (``lport``) of the local machine
        (``lhost``, defaults to ``"localhost"``, but it can be any IP you can ``bind()``)
        to the remote TCP port (``dport``) of the destination machine (``dhost``, defaults
        to ``"localhost"``, which means *this remote machine*). The returned
        :class:`SshTunnel <plumbum.remote_machine.SshTunnel>` object can be used as a
        *context-manager*.

        The more conventional use case is the following::

            +---------+          +---------+
            | Your    |          | Remote  |
            | Machine |          | Machine |
            +----o----+          +---- ----+
                 |                    ^
                 |                    |
               lport                dport
                 |                    |
                 \______SSH TUNNEL____/
                        (secure)

        Here, you wish to communicate safely between port ``lport`` of your machine and
        port ``dport`` of the remote machine. Communication is tunneled over SSH, so the
        connection is authenticated and encrypted.

        The more general case is shown below (where ``dport != "localhost"``)::

            +---------+          +-------------+      +-------------+
            | Your    |          | Remote      |      | Destination |
            | Machine |          | Machine     |      | Machine     |
            +----o----+          +---- ----o---+      +---- --------+
                 |                    ^    |               ^
                 |                    |    |               |
            lhost:lport               |    |          dhost:dport
                 |                    |    |               |
                 \_____SSH TUNNEL_____/    \_____SOCKET____/
                        (secure)              (not secure)

        Usage::

            rem = SshMachine("megazord")

            with rem.tunnel(1234, 5678):
                sock = socket.socket()
                sock.connect(("localhost", 1234))
                # sock is now tunneled to megazord:5678
        """
        opts = ["-L", "[%s]:%s:[%s]:%s" % (lhost, lport, dhost, dport)]
        return SshTunnel(ShellSession(self.popen((), opts), self.encoding))

    @_setdoc(BaseRemoteMachine)
    def download(self, src, dst):
        if isinstance(src, LocalPath):
            raise TypeError("src of download cannot be %r" % (src,))
        if isinstance(src, RemotePath) and src.remote != self:
            raise TypeError("src %r points to a different remote machine" % (src,))
        if isinstance(dst, RemotePath):
            raise TypeError("dst of download cannot be %r" % (dst,))
        self._scp_command("%s:%s" % (self._fqhost, shquote(src)), dst)

    @_setdoc(BaseRemoteMachine)
    def upload(self, src, dst):
        if isinstance(src, RemotePath):
            raise TypeError("src of upload cannot be %r" % (src,))
        if isinstance(dst, LocalPath):
            raise TypeError("dst of upload cannot be %r" % (dst,))
        if isinstance(dst, RemotePath) and dst.remote != self:
            raise TypeError("dst %r points to a different remote machine" % (dst,))
        self._scp_command(src, "%s:%s" % (self._fqhost, shquote(dst)))


class PuttyMachine(SshMachine):
    """
    PuTTY-flavored SSH connection. The programs ``plink`` and ``pscp`` are expected to
    be in the path (or you may supply
    """
    def __init__(self, host, user = None, port = None, keyfile = None, ssh_command = None,
            scp_command = None, ssh_opts = (), scp_opts = (), encoding = "utf8"):
        if ssh_command is None:
            ssh_command = local["plink"]
        if scp_command is None:
            scp_command = local["pscp"]
        if not ssh_opts:
            ssh_opts = ["-ssh"]
        if user is None:
            user = local.env.user
        SshMachine.__init__(self, host, user, port, keyfile, ssh_command, scp_command,
            ssh_opts, scp_opts)

    def __str__(self):
        return "ssh(putty)://%s" % (self._fqhost,)

    @_setdoc(BaseRemoteMachine)
    def session(self, isatty = False):
        return ShellSession(self.popen((), ["-t"] if isatty else ["-T"]), self.encoding, isatty)



