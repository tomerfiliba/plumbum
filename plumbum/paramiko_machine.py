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

import logging
import six
import errno
import socket
from plumbum.remote_machine import BaseRemoteMachine
from plumbum.session import ShellSession
from plumbum.lib import _setdoc, bytes
from plumbum.local_machine import LocalPath
from plumbum.remote_path import RemotePath


logger = logging.getLogger("plumbum.paramiko")

class ParamikoPopen(object):
    def __init__(self, argv, stdin, stdout, stderr, encoding, stdin_file = None, 
            stdout_file = None, stderr_file = None):
        self.argv = argv
        self.channel = stdout.channel
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.encoding = encoding
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
            #logger.debug("%s> %r", name, line)
            if not line:
                del sources[i]
            elif outfile:
                outfile.write(line)
                outfile.flush()
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
    """    
    def __init__(self, host, user = None, port = None, password = None, keyfile = None, 
            load_system_host_keys = True, missing_host_policy = None, encoding = "utf8"):
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
        if user is not None:
            kwargs["username"] = user
        if missing_host_policy is not None:
            self._client.set_missing_host_key_policy(missing_host_policy)
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
    def popen(self, args, stdin = None, stdout = None, stderr = None):
        argv = []
        envdelta = self.env.getdelta()
        argv.extend(["cd", str(self.cwd), "&&"])
        if envdelta:
            argv.append("env")
            argv.extend("%s=%s" % (k, v) for k, v in envdelta.items())
        argv.extend(args.formulate())
        cmdline = " ".join(argv)
        logger.debug(cmdline)
        si, so, se = self._client.exec_command(cmdline, 1)
        return ParamikoPopen(argv, si, so, se, self.encoding, stdin_file = stdin, stdout_file = stdout, stderr_file = stderr)

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
        if src.isdir():
            if not dst.exists():
                self.sftp.mkdir(str(dst))
            for fn in src:
                self._download(fn, dst / fn.basename)
        elif dst.isdir():
            self.sftp.get(str(src), str(dst / src.basename))
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
        if src.isdir():
            if not dst.exists():
                self.sftp.mkdir(str(dst))
            for fn in src:
                self._upload(fn, dst / fn.basename)
        elif dst.isdir():
            self.sftp.put(str(src), str(dst / src.basename))
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
        chan = self._client.get_transport().open_channel('direct-tcpip', (dhost, dport), srcaddr)
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
        #if self.encoding and isinstance(data, bytes) and not isinstance(data, str):
        #    data = data.decode(self.encoding)
        return data
    def _path_write(self, fn, data):
        if self.encoding and isinstance(data, str) and not isinstance(data, bytes):
            data = data.encode(self.encoding)
        f = self.sftp.open(str(fn), 'wb')
        f.write(data)
        f.close()



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



