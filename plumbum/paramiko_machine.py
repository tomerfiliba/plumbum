import paramiko
import logging
import six
import select
import threading
import socket
from plumbum.remote_machine import BaseRemoteMachine, SshMachine
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


class SimpleReactor(object):
    __slots__ = ["_active", "_io_handlers"]
    
    def __init__(self):
        self._active = False
        self._io_handlers = []

    def add_handler(self, handler):
        self._io_handlers.append(handler)

    def _mainloop(self):
        while self._active:
            pruned = []
            for handler in self._io_handlers:
                try:
                    handler.fileno()
                except EnvironmentError:
                    pass
                else:
                    pruned.append(handler)
            self._io_handlers = pruned
            rlist, _, _ = select.select(self._io_handlers, (), (), 0.5)
            for handler in rlist:
                handler.handle()

    def start(self):
        if self._active:
            raise ValueError("reactor already running")
        self._active = True
        self._mainloop()
    def stop(self):
        self._active = False

reactor = SimpleReactor()
reactor_thread = threading.Thread(target = reactor.start)
reactor_thread.start()
#def shutdown_reactor_thread():
#    reactor.stop()
#    reactor_thread.join()
#atexit.register(shutdown_reactor_thread)

class ReactorHandler(object):
    __slots__ = ()
    def fileno(self):
        raise NotImplementedError()
    def close(self):
        pass

class Accepter(ReactorHandler):
    __slots__ = ["tunnel", "listener"]
    
    def __init__(self, tunnel, backlog = 5, family = socket.AF_INET, socktype = socket.SOCK_STREAM):
        self.tunnel = tunnel
        self.listener = socket.socket(family, socktype)
        self.listener.bind((tunnel.lhost, tunnel.lport))
        self.listener.listen(backlog)
    def close(self):
        self.listener.close()
    def fileno(self):
        return self.listener.fileno()
    def handle(self):
        sock, _ = self.listener.accept()
        chan = self.tunnel.transport.open_channel('direct-tcpip',
           (self.tunnel.dhost, self.tunnel.dport), sock.getpeername())
        if chan is None:
            raise ValueError("Rejected by server")
        self.tunnel.add_pair(chan, sock)

class Forwarder(ReactorHandler):
    __slots__ = ["srcsock", "dstsock"]
    CHUNK_SIZE = 1024
    
    def __init__(self, srcsock, dstsock):
        self.srcsock = srcsock
        self.dstsock = dstsock
    def fileno(self):
        return self.srcsock.fileno()
    def close(self):
        self.srcsock.shutdown(socket.SHUT_RDWR)
        self.srcsock.close()
        self.dstsock.shutdown(socket.SHUT_RDWR)
        self.dstsock.close()
    def handle(self):
        data = self.srcsock.recv(self.CHUNK_SIZE)
        if not data:
            self.shutdown()
        while data:
            count = self.dstsock.send(data)
            data = data[count:]

class ParamikoTunnel(object):
    def __init__(self, reactor, transport, lhost, lport, dhost, dport):
        self.reactor = reactor
        self.transport = transport
        self.lhost = lhost
        self.lport = lport
        self.dhost = dhost
        self.dport = dport
        self.accepter = Accepter(self)
        self.forwarders = []
        self.reactor.add_handler(self.accepter)

    def __repr__(self):
        return "<ParamikoTunnel %s:%s->%s:%s" % (self.lhost, self.lport, self.dhost, self.dport)

    def is_active(self):
        return bool(self.accepter)

    def close(self):
        if not self.accepter:
            return
        for fwd in self.forwarders:
            fwd.close()
        del self.forwarders[:]
        self.accepter.close()
        self.accepter = None

    def add_pair(self, chan, sock):
        f1 = Forwarder(chan, sock)
        f2 = Forwarder(sock, chan)
        self.forwarders.append(f1)
        self.forwarders.append(f2)
        self.reactor.add_handler(f1)
        self.reactor.add_handler(f2)


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
        proc = ParamikoPopen("<shell>", stdin, stdout, stderr, self.encoding)
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

    @_setdoc(SshMachine)
    def tunnel(self, lport, dport, lhost = "localhost", dhost = "localhost"):
        return ParamikoTunnel(reactor, self._client.get_transport(), lhost, lport, dhost, dport)


if __name__ == "__main__":
    logging.basicConfig(level = 0)

    m = ParamikoMachine("192.168.1.143")
    ls = m["ls"]
    #print repr(ls)
    print ls("-l")













