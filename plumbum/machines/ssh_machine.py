from __future__ import with_statement
from plumbum.lib import _setdoc, IS_WIN32
from plumbum.machines.remote import BaseRemoteMachine
from plumbum.machines.session import ShellSession
from plumbum.machines.local import local
from plumbum.path.local import LocalPath
from plumbum.path.remote import RemotePath
from plumbum.commands import ProcessExecutionError, shquote


class SshTunnel(object):
    """An object representing an SSH tunnel (created by
    :func:`SshMachine.tunnel <plumbum.machines.remote.SshMachine.tunnel>`)"""
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
    An implementation of :class:`remote machine <plumbum.machines.remote.BaseRemoteMachine>`
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

    :param password: the password to use; requires ``sshpass`` be installed. Cannot be used
                     in conjunction with ``ssh_command`` or ``scp_command`` (will be ignored).
                     NOTE: THIS IS A SECURITY RISK!

    :param encoding: the remote machine's encoding (defaults to UTF8)
    """

    def __init__(self, host, user = None, port = None, keyfile = None, ssh_command = None,
            scp_command = None, ssh_opts = (), scp_opts = (), password = None, encoding = "utf8"):

        if ssh_command is None:
            if password is not None:
                ssh_command = local["sshpass"]["-p", password, "ssh"]
            else:
                ssh_command = local["ssh"]
        if scp_command is None:
            if password is not None:
                scp_command = local["sshpass"]["-p", password, "scp"]
            else:
                scp_command = local["scp"]

        scp_args = []
        ssh_args = []
        if user:
            self._fqhost = "%s@%s" % (user, host)
        else:
            self._fqhost = host
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

    def nohup(self, command):
        """
        Runs the given command using ``nohup`` and redirects std handles to ``/dev/null``,
        allowing the command to run "detached" from its controlling TTY or parent.
        Does not return anything.
        """
        args = ["nohup"]
        args.extend(command.formulate())
        args.extend([">/dev/null", "2>/dev/null", "</dev/null"])
        proc = self.popen(args, ssh_opts = ["-f"])
        rc = proc.wait()
        try:
            if rc != 0:
                raise ProcessExecutionError(args, rc, proc.stdout.read(), proc.stderr.read())
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()

    @_setdoc(BaseRemoteMachine)
    def session(self, isatty = False, connect_timeout = 5):
        return ShellSession(self.popen((), ["-tt"] if isatty else ["-T"]),
            self.encoding, isatty, connect_timeout)

    def tunnel(self, lport, dport, lhost = "localhost", dhost = "localhost"):
        r"""Creates an SSH tunnel from the TCP port (``lport``) of the local machine
        (``lhost``, defaults to ``"localhost"``, but it can be any IP you can ``bind()``)
        to the remote TCP port (``dport``) of the destination machine (``dhost``, defaults
        to ``"localhost"``, which means *this remote machine*). The returned
        :class:`SshTunnel <plumbum.machines.remote.SshTunnel>` object can be used as a
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
        ssh_opts = ["-L", "[%s]:%s:[%s]:%s" % (lhost, lport, dhost, dport)]
        proc = self.popen((), ssh_opts = ssh_opts, new_session = True)
        return SshTunnel(ShellSession(proc, self.encoding))

    def _translate_drive_letter(self, path):
        # replace c:\some\path with /c/some/path
        path = str(path)
        if ":" in path:
            path = "/" + path.replace(":", "").replace("\\", "/")
        return path

    @_setdoc(BaseRemoteMachine)
    def download(self, src, dst):
        if isinstance(src, LocalPath):
            raise TypeError("src of download cannot be %r" % (src,))
        if isinstance(src, RemotePath) and src.remote != self:
            raise TypeError("src %r points to a different remote machine" % (src,))
        if isinstance(dst, RemotePath):
            raise TypeError("dst of download cannot be %r" % (dst,))
        if IS_WIN32:
            src = self._translate_drive_letter(src)
            dst = self._translate_drive_letter(dst)
        self._scp_command("%s:%s" % (self._fqhost, shquote(src)), dst)

    @_setdoc(BaseRemoteMachine)
    def upload(self, src, dst):
        if isinstance(src, RemotePath):
            raise TypeError("src of upload cannot be %r" % (src,))
        if isinstance(dst, LocalPath):
            raise TypeError("dst of upload cannot be %r" % (dst,))
        if isinstance(dst, RemotePath) and dst.remote != self:
            raise TypeError("dst %r points to a different remote machine" % (dst,))
        if IS_WIN32:
            src = self._translate_drive_letter(src)
            dst = self._translate_drive_letter(dst)
        self._scp_command(src, "%s:%s" % (self._fqhost, shquote(dst)))


class PuttyMachine(SshMachine):
    """
    PuTTY-flavored SSH connection. The programs ``plink`` and ``pscp`` are expected to
    be in the path (or you may provide your own ``ssh_command`` and ``scp_command``)

    Arguments are the same as for :class:`plumbum.machines.remote.SshMachine`
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
        if port is not None:
            ssh_opts.extend(["-P", str(port)])
            port = None
        SshMachine.__init__(self, host, user, port, keyfile, ssh_command, scp_command,
            ssh_opts, scp_opts)

    def __str__(self):
        return "putty-ssh://%s" % (self._fqhost,)

    def _translate_drive_letter(self, path):
        # pscp takes care of windows paths automatically
        return path

    @_setdoc(BaseRemoteMachine)
    def session(self, isatty = False):
        return ShellSession(self.popen((), ["-t"] if isatty else ["-T"]), self.encoding, isatty)


