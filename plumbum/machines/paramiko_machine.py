import logging
import errno
import stat
import socket
from plumbum.machines.base import PopenAddons
from plumbum.machines.remote import BaseRemoteMachine
from plumbum.machines.session import ShellSession
from plumbum.lib import _setdoc, six
from plumbum.path.local import LocalPath
from plumbum.path.remote import RemotePath, StatRes
from plumbum.commands.processes import iter_lines
try:
    # Sigh... we need to gracefully-import paramiko for Sphinx builds, etc
    import paramiko
except ImportError:
    class paramiko(object):
        def __nonzero__(self):
            return False
        __bool__ = __nonzero__
        def __getattr__(self, name):
            raise ImportError("No module named paramiko")
    paramiko = paramiko()


logger = logging.getLogger("plumbum.paramiko")

class ParamikoPopen(PopenAddons):
    def __init__(self, argv, stdin, stdout, stderr, encoding, stdin_file = None,
            stdout_file = None, stderr_file = None):
        self.argv = argv
        self.channel = stdout.channel
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.custom_encoding = encoding
        self.returncode = None
        self.pid = None
        self.stdin_file = stdin_file
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
    def poll(self):
        if self.returncode is None:
            if self.channel.exit_status_ready():
                return self.wait()
        return self.returncode
    def wait(self):
        if self.returncode is None:
            self.channel.recv_exit_status()
            self.returncode = self.channel.exit_status
            self.close()
        return self.returncode
    def close(self):
        self.channel.shutdown_read()
        self.channel.shutdown_write()
        self.channel.close()
    def kill(self):
        # possible way to obtain pid:
        # "(cmd ; echo $?) & echo ?!"
        # and then client.exec_command("kill -9 %s" % (pid,))
        raise EnvironmentError("Cannot kill remote processes, we don't have their PIDs")
    terminate = kill
    def send_signal(self, sig):
        raise NotImplementedError()
    def communicate(self):
        stdout = []
        stderr = []
        infile = self.stdin_file
        sources = [("1", stdout, self.stdout, self.stdout_file), ("2", stderr, self.stderr, self.stderr_file)]
        i = 0
        while sources:
            if infile:
                try:
                    line = infile.readline()
                except (ValueError, IOError):
                    line = None
                logger.debug("communicate: %r", line)
                if not line:
                    infile.close()
                    infile = None
                    self.stdin.close()
                else:
                    self.stdin.write(line)
                    self.stdin.flush()

            i = (i + 1) % len(sources)
            name, coll, pipe, outfile = sources[i]
            line = pipe.readline()
            # logger.debug("%s> %r", name, line)
            if not line:
                del sources[i]
            elif outfile:
                outfile.write(line)
                outfile.flush()
            else:
                coll.append(line)
        self.wait()
        stdout = six.b("").join(six.b(s) for s in stdout)
        stderr = six.b("").join(six.b(s) for s in stderr)
        return stdout, stderr

    def iter_lines(self, timeout=None, **kwargs):
        if timeout is not None:
            raise NotImplementedError("The 'timeout' parameter is not supported with ParamikoMachine")
        return iter_lines(self, _iter_lines=_iter_lines, **kwargs)

    __iter__ = iter_lines

class ParamikoMachine(BaseRemoteMachine):
    """
    An implementation of :class:`remote machine <plumbum.machines.remote.BaseRemoteMachine>`
    over Paramiko (a Python implementation of openSSH2 client/server). Invoking a remote command
    translates to invoking it over SSH ::

        with ParamikoMachine("yourhostname") as rem:
            r_ls = rem["ls"]
            # r_ls is the remote `ls`
            # executing r_ls() is equivalent to `ssh yourhostname ls`, only without
            # spawning a new ssh client

    :param host: the host name to connect to (SSH server)

    :param user: the user to connect as (if ``None``, the default will be used)

    :param port: the server's port (if ``None``, the default will be used)

    :param password: the user's password (if a password-based authentication is to be performed)
                     (if ``None``, key-based authentication will be used)

    :param keyfile: the path to the identity file (if ``None``, the default will be used)

    :param load_system_host_keys: whether or not to load the system's host keys (from ``/etc/ssh``
                                  and ``~/.ssh``). The default is ``True``, which means Paramiko
                                  behaves much like the ``ssh`` command-line client

    :param missing_host_policy: the value passed to the underlying ``set_missing_host_key_policy``
                                of the client. The default is ``None``, which means
                                ``set_missing_host_key_policy`` is not invoked and paramiko's
                                default behavior (reject) is employed

    :param encoding: the remote machine's encoding (defaults to UTF8)

    :param look_for_keys: set to False to disable searching for discoverable
                          private key files in ``~/.ssh``

    :param connect_timeout: timeout for TCP connection
    """

    class RemoteCommand(BaseRemoteMachine.RemoteCommand):
        def __or__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")
        def __gt__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")
        def __rshift__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")
        def __ge__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")
        def __lt__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")
        def __lshift__(self, *_):
            raise NotImplementedError("Not supported with ParamikoMachine")

    def __init__(self, host, user = None, port = None, password = None, keyfile = None,
            load_system_host_keys = True, missing_host_policy = None, encoding = "utf8",
            look_for_keys = None, connect_timeout = None, keep_alive = 0):
        self.host = host
        kwargs = {}
        if user:
            self._fqhost = "%s@%s" % (user, host)
            kwargs['username'] = user
        else:
            self._fqhost = host
        self._client = paramiko.SSHClient()
        if load_system_host_keys:
            self._client.load_system_host_keys()
        if port is not None:
            kwargs["port"] = port
        if keyfile is not None:
            kwargs["key_filename"] = keyfile
        if password is not None:
            kwargs["password"] = password
        if missing_host_policy is not None:
            self._client.set_missing_host_key_policy(missing_host_policy)
        if look_for_keys is not None:
            kwargs["look_for_keys"] = look_for_keys
        if connect_timeout is not None:
            kwargs["timeout"] = connect_timeout
        self._client.connect(host, **kwargs)
        self._keep_alive = keep_alive
        self._sftp = None
        BaseRemoteMachine.__init__(self, encoding, connect_timeout)

    def __str__(self):
        return "paramiko://%s" % (self._fqhost,)

    def close(self):
        BaseRemoteMachine.close(self)
        self._client.close()

    @property
    def sftp(self):
        """
        Returns an SFTP client on top of the current SSH connection; it can be used to manipulate
        files directly, much like an interactive FTP/SFTP session
        """
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        return self._sftp

    @_setdoc(BaseRemoteMachine)
    def session(self, isatty = False, term = "vt100", width = 80, height = 24, new_session = False):
        # new_session is ignored for ParamikoMachine
        trans = self._client.get_transport()
        trans.set_keepalive(self._keep_alive)
        chan = trans.open_session()
        if isatty:
            chan.get_pty(term, width, height)
            chan.set_combine_stderr(True)
        chan.invoke_shell()
        stdin = chan.makefile('wb', -1)
        stdout = chan.makefile('rb', -1)
        stderr = chan.makefile_stderr('rb', -1)
        proc = ParamikoPopen(["<shell>"], stdin, stdout, stderr, self.custom_encoding)
        return ShellSession(proc, self.custom_encoding, isatty)

    @_setdoc(BaseRemoteMachine)
    def popen(self, args, stdin = None, stdout = None, stderr = None, new_session = False, cwd = None):
        # new_session is ignored for ParamikoMachine
        argv = []
        envdelta = self.env.getdelta()
        argv.extend(["cd", str(cwd or self.cwd), "&&"])
        if envdelta:
            argv.append("env")
            argv.extend("%s=%s" % (k, v) for k, v in envdelta.items())
        argv.extend(args.formulate())
        cmdline = " ".join(argv)
        logger.debug(cmdline)
        si, so, se = streams = self._client.exec_command(cmdline, 1)
        return ParamikoPopen(argv, si, so, se, self.custom_encoding, stdin_file = stdin,
            stdout_file = stdout, stderr_file = stderr)

    @_setdoc(BaseRemoteMachine)
    def download(self, src, dst):
        if isinstance(src, LocalPath):
            raise TypeError("src of download cannot be %r" % (src,))
        if isinstance(src, RemotePath) and src.remote != self:
            raise TypeError("src %r points to a different remote machine" % (src,))
        if isinstance(dst, RemotePath):
            raise TypeError("dst of download cannot be %r" % (dst,))
        return self._download(src if isinstance(src, RemotePath) else self.path(src),
            dst if isinstance(dst, LocalPath) else LocalPath(dst))

    def _download(self, src, dst):
        if src.is_dir():
            if not dst.exists():
                self.sftp.mkdir(str(dst))
            for fn in src:
                self._download(fn, dst / fn.name)
        elif dst.is_dir():
            self.sftp.get(str(src), str(dst / src.name))
        else:
            self.sftp.get(str(src), str(dst))

    @_setdoc(BaseRemoteMachine)
    def upload(self, src, dst):
        if isinstance(src, RemotePath):
            raise TypeError("src of upload cannot be %r" % (src,))
        if isinstance(dst, LocalPath):
            raise TypeError("dst of upload cannot be %r" % (dst,))
        if isinstance(dst, RemotePath) and dst.remote != self:
            raise TypeError("dst %r points to a different remote machine" % (dst,))
        return self._upload(src if isinstance(src, LocalPath) else LocalPath(src),
            dst if isinstance(dst, RemotePath) else self.path(dst))

    def _upload(self, src, dst):
        if src.is_dir():
            if not dst.exists():
                self.sftp.mkdir(str(dst))
            for fn in src:
                self._upload(fn, dst / fn.name)
        elif dst.is_dir():
            self.sftp.put(str(src), str(dst / src.name))
        else:
            self.sftp.put(str(src), str(dst))

    def connect_sock(self, dport, dhost = "localhost", ipv6 = False):
        """Returns a Paramiko ``Channel``, connected to dhost:dport on the remote machine.
        The ``Channel`` behaves like a regular socket; you can ``send`` and ``recv`` on it
        and the data will pass encrypted over SSH. Usage::

            mach = ParamikoMachine("myhost")
            sock = mach.connect_sock(12345)
            data = sock.recv(100)
            sock.send("foobar")
            sock.close()
        """
        if ipv6 and dhost == "localhost":
            dhost = "::1"
        srcaddr = ("::1", 0, 0, 0) if ipv6 else ("127.0.0.1", 0)
        trans = self._client.get_transport()
        trans.set_keepalive(self._keep_alive)
        chan = trans.open_channel('direct-tcpip', (dhost, dport), srcaddr)
        return SocketCompatibleChannel(chan)

    #
    # Path implementation
    #
    def _path_listdir(self, fn):
        return self.sftp.listdir(str(fn))

    def _path_read(self, fn):
        f = self.sftp.open(str(fn), 'rb')
        data = f.read()
        f.close()
        return data
    def _path_write(self, fn, data):
        if self.custom_encoding and isinstance(data, six.unicode_type):
            data = data.encode(self.custom_encoding)
        f = self.sftp.open(str(fn), 'wb')
        f.write(data)
        f.close()
    def _path_stat(self, fn):
        try:
            st = self.sftp.stat(str(fn))
        except IOError as e:
            if e.errno == errno.ENOENT:
                return None
            raise OSError(e.errno)
        res = StatRes((st.st_mode, 0, 0, 0, st.st_uid, st.st_gid,
                       st.st_size, st.st_atime, st.st_mtime, 0))

        if stat.S_ISDIR(st.st_mode):
            res.text_mode = 'directory'
        if stat.S_ISREG(st.st_mode):
            res.text_mode = 'regular file'
        return res



###################################################################################################
# Make paramiko.Channel adhere to the socket protocol, namely, send and recv should fail
# when the socket has been closed
###################################################################################################
class SocketCompatibleChannel(object):
    def __init__(self, chan):
        self._chan = chan
    def __getattr__(self, name):
        return getattr(self._chan, name)
    def send(self, s):
        if self._chan.closed:
            raise socket.error(errno.EBADF, 'Bad file descriptor')
        return self._chan.send(s)
    def recv(self, count):
        if self._chan.closed:
            raise socket.error(errno.EBADF, 'Bad file descriptor')
        return self._chan.recv(count)


###################################################################################################
# Custom iter_lines for paramiko.Channel
###################################################################################################
def _iter_lines(proc, decode, linesize):

    try:
        from selectors import DefaultSelector, EVENT_READ
    except ImportError:
        # Pre Python 3.4 implementation
        from select import select
        def selector():
            while True:
                rlist, _, _ = select([proc.stdout.channel], [], [])
                for _ in rlist:
                    yield
    else:
        # Python 3.4 implementation
        def selector():
            sel = DefaultSelector()
            sel.register(proc.stdout.channel, EVENT_READ)
            while True:
                for key, mask in sel.select():
                    yield

    for _ in selector():
        if proc.stdout.channel.recv_ready():
            yield 0, decode(six.b(proc.stdout.readline(linesize)))
        if proc.stdout.channel.recv_stderr_ready():
            yield 1, decode(six.b(proc.stderr.readline(linesize)))
        if proc.poll() is not None:
            break

    for line in proc.stdout:
        yield 0, decode(six.b(line))
    for line in proc.stderr:
        yield 1, decode(six.b(line))
