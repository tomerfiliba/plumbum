import paramiko
import logging
import six
import errno
import socket
import functools
from plumbum.remote_machine import BaseRemoteMachine
from plumbum.session import ShellSession
from plumbum.lib import _setdoc
from plumbum.local_machine import LocalPath
from plumbum.remote_path import RemotePath


logger = logging.getLogger("plumbum.paramiko")

class ParamikoPopen(object):
    def __init__(self, argv, stdin, stdout, stderr, encoding):
        self.argv = argv
        self.channel = stdout.channel
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.encoding = encoding
        self.returncode = None
        self.pid = None
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
    def communicate(self, input = None):
        stdout = []
        stderr = []
        sources = [("1", stdout, self.stdout), ("2", stderr, self.stderr)]
        i = 0
        while sources:
            if input:
                chunk = input[:1000]
                self.stdin.write(chunk)
                self.stdin.flush()
                input = input[1000:]
            i = (i + 1) % len(sources)
            name, coll, pipe = sources[i]
            line = pipe.readline()
            #logger.debug("%s> %r", name, line)
            if not line:
                del sources[i]
            else:
                coll.append(line)
        self.wait()
        stdout = six.b("").join(stdout)
        stderr = six.b("").join(stderr)
        return stdout, stderr


class ParamikoMachine(BaseRemoteMachine):
    """
    An implementation of :class:`remote machine <plumbum.remote_machine.BaseRemoteMachine>`
    over Paramiko (a Python implementation of openSSH2 client/server). Invoking a remote command 
    translates to invoking it over SSH ::

        with ParamikoMachine("yourhostname") as rem:
            r_ls = rem["ls"]
            # r_ls is the remote `ls`
            # executing r_ls() translates to `ssh yourhostname ls`

    :param host: the host name to connect to (SSH server)

    :param user: the user to connect as (if ``None``, the default will be used)

    :param port: the server's port (if ``None``, the default will be used)

    :param password: the user's password (if a password-based authentication is to be performed)
                     (if ``None``, key-based authentication will be used)

    :param keyfile: the path to the identity file (if ``None``, the default will be used)
    
    :param load_system_host_keys: whether or not to load the system's host keys (from ``/etc/ssh`` 
                                  and ``~/.ssh``). The default is ``True``, which means Paramiko
                                  behaves much like the ``ssh`` command-line client

    :param encoding: the remote machine's encoding (defaults to UTF8)
    """    
    def __init__(self, host, user = None, port = None, password = None, keyfile = None, 
            load_system_host_keys = True, encoding = "utf8"):
        self.host = host
        if user:
            self._fqhost = "%s@%s" % (user, host)
        else:
            self._fqhost = host
        self._client = paramiko.SSHClient()
        if load_system_host_keys:
            self._client.load_system_host_keys()
        kwargs = {}
        if port is not None:
            kwargs["port"] = port
        if keyfile is not None:
            kwargs["key_filename"] = keyfile
        if password is not None:
            kwargs["password"] = password
        self._client.connect(host, **kwargs)
        self._sftp = None
        BaseRemoteMachine.__init__(self, encoding)

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
    def session(self, isatty = False, term = "vt100", width = 80, height = 24):
        chan = self._client.get_transport().open_session()
        if isatty:
            chan.get_pty(term, width, height)
            chan.set_combine_stderr()
        chan.invoke_shell()
        stdin = chan.makefile('wb', -1)
        stdout = chan.makefile('rb', -1)
        stderr = chan.makefile_stderr('rb', -1)
        proc = ParamikoPopen(["<shell>"], stdin, stdout, stderr, self.encoding)
        return ShellSession(proc, self.encoding, isatty)

    @_setdoc(BaseRemoteMachine)
    def popen(self, args):
        argv = []
        envdelta = self.env.getdelta()
        argv.extend(["cd", str(self.cwd), "&&"])
        if envdelta:
            argv.append("env")
            argv.extend("%s=%s" % (k, v) for k, v in envdelta.items())
        argv.extend(args.formulate())
        cmdline = " ".join(argv)
        logger.debug(cmdline)
        si, so, se = self._client.exec_command(cmdline)
        return ParamikoPopen(argv, si, so, se, self.encoding)

    @_setdoc(BaseRemoteMachine)
    def download(self, src, dst):
        if isinstance(src, LocalPath):
            raise TypeError("src of download cannot be %r" % (src,))
        if isinstance(src, RemotePath) and src.remote != self:
            raise TypeError("src %r points to a different remote machine" % (src,))
        if isinstance(dst, RemotePath):
            raise TypeError("dst of download cannot be %r" % (dst,))
        self.sftp.get(str(src), str(dst))

    @_setdoc(BaseRemoteMachine)
    def upload(self, src, dst):
        if isinstance(src, RemotePath):
            raise TypeError("src of upload cannot be %r" % (src,))
        if isinstance(dst, LocalPath):
            raise TypeError("dst of upload cannot be %r" % (dst,))
        if isinstance(dst, RemotePath) and dst.remote != self:
            raise TypeError("dst %r points to a different remote machine" % (dst,))
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
        chan = self._client.get_transport().open_channel('direct-tcpip', (dhost, dport), srcaddr)
        return chan


###############################################################################
# monkey-patch paramiko.Channel, so that send and recv will fail after the 
# transport has been closed. see https://github.com/paramiko/paramiko/pull/99
################################################################################
_orig_send = paramiko.Channel.send
@functools.wraps(paramiko.Channel.send)
def send2(self, s):
    if self.closed:
        raise socket.error(errno.EBADF, 'Bad file descriptor')
    return _orig_send(self, s)
paramiko.Channel.send = send2

_orig_recv = paramiko.Channel.recv
@functools.wraps(paramiko.Channel.recv)
def recv2(self, count):
    if self.closed:
        raise socket.error(errno.EBADF, 'Bad file descriptor')
    return _orig_recv(self, count)
paramiko.Channel.recv = recv2





