import sys
import time
import subprocess
import logging
from plumbum.localcmd import local, ProcessExecutionError, _run


#logging.basicConfig(level=logging.INFO)
ctx_logger = logging.getLogger("SshContext")
sess_logger = logging.getLogger("SshSession")

# modified from the stdlib pipes module for windows
_safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
_funnychars = '"`$\\'
def shquote(text):
    if not text:
        return "''"
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = "".join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'

if subprocess.mswindows:
    def _get_startupinfo():
        sui = subprocess.STARTUPINFO()
        sui.dwFlags |= subprocess.STARTF_USESHOWWINDOW    #@UndefinedVariable
        sui.wShowWindow = subprocess.SW_HIDE              #@UndefinedVariable
        return sui
else:
    def _get_startupinfo():
        return None


class SshSession(object):
    def __init__(self, sshctx, tty, **kwargs):
        self.sshctx = sshctx
        self.tty = tty
        self.proc = sshctx.popen((), sshopts = dict(tt = tty, **kwargs))
        self.run("") # consume MOTD, banners, etc

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()

    def __repr__(self):
        return "<SshSession to %s>" % (self.sshctx,)
    
    def alive(self):
        """returns True if the ``ssh`` process is alive, False otherwise"""
        return self.proc and self.proc.poll() is None
    
    def close(self):
        if not self.alive():
            return
        self.proc.stdin.write(b"\nexit\n\n\nexit\n\n")
        self.proc.stdin.close()
        time.sleep(0.05)
        self.proc.kill()
        self.proc = None
    
    def run(self, cmdline, retcode = 0):
        """
        :param cmdline: the command line string (given as-is to the remote 
                        shell, so be sure to take care of proper escaping)
        :param retcode: the expected return code (defaults to 0 -- success). 
                        An exception is raised if the return code does not 
                        match the expected one, unless it is ``None``, in 
                        which case it will not be tested.
        
        :raises: :class:`ProcessExecutionError` if the expected return code 
                 is not matched
        
        :returns: a tuple of (return code, stdout, stderr)
        
        Example::
            
            shl = ctx.shell()
            rc, out, err = shl.execute("ls -la")
        """
        MARKER = b"-:#:-End~Of~Output-%s-:#:-" % (time.time(),)
        full_cmdline = cmdline
        if full_cmdline.strip():
            full_cmdline += " ; "
        full_cmdline += "echo $? ; echo %s" % (MARKER,)
        if not self.tty:
            full_cmdline += " ; echo %s 1>&2" % (MARKER)
        sess_logger.info("Running: %r" % (full_cmdline,))
        self.proc.stdin.write((full_cmdline + "\n").encode(self.sshctx.encoding))
        stdout = []
        stderr = []
        sources = [("1", stdout, self.proc.stdout)]
        if not self.tty:
            # in tty mode, stdout and stderr are unified
            sources.append(("2", stderr, self.proc.stderr))
        for name, coll, pipe in sources:
            while True:
                line = pipe.readline()
                sess_logger.debug("%s> %r" % (name, line))
                if line.strip() == MARKER:
                    break
                coll.append(line)
        if self.tty:
            stdout.pop(0) # discard first line prompt
        try:
            rc = int(stdout.pop(-1))
        except (IndexError, ValueError):
            rc = None
        stdout = b"".join(stdout)
        stderr = b"".join(stderr)
        if retcode is not None and rc != retcode:
            raise ProcessExecutionError(full_cmdline, rc, stdout.decode(self.sshctx.encoding), 
                stderr.decode(self.sshctx.encoding))
        return rc, stdout, stderr


class SshTunnel(object):
    def __init__(self, session, src, dst):
        self.session = session
        self.src = src
        self.dst = dst
        ctx_logger.info("Tunnel %r has been created" % (self,))

    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()

    def __repr__(self):
        if not self.session.alive():
            return "<SshTunnel (closed)>"
        return "<SshTunnel %s -> %s>" % (self.src, self.dst) 

    def close(self):
        ctx_logger.info("Tunnel %r is shutting down" % (self,))
        self.session.close()


class SshContext(object):
    """
    An *SSH context* encapsulates all the details required to establish an SSH 
    connection to other host. It includes the host name, user name, TCP port, 
    identity file, etc.
    
    Once constructed, it can serve as a factory for SSH operations, such as 
    executing a remote program and getting its stdout, or uploading/downloading
    files using ``scp``. It also serves for creating SSH tunnels. 
    
    Example::
    
        >>> sshctx = SshContext("mymachine", user="borg", keyfile="/home/foo/.ssh/mymachine-id")
        >>> sshctx.execute("ls")
        (0, "file1\\nfile2\\nfile3\\n", "")
    """
    def __init__(self, host, user = None, port = None, keyfile = None,
            ssh_command = None, scp_command = None, encoding = sys.getdefaultencoding()):
        self.host = host
        self.user = user
        self.port = port
        self.encoding = encoding
        self.keyfile = keyfile
        if not ssh_command:
            ssh_command = local["ssh"]
        self.ssh_command = ssh_command
        if not scp_command:
            scp_command = local["scp"]
        self.scp_command = scp_command

    def __str__(self):
        uri = "ssh://"
        if self.user:
            uri += "%s@%s" % (self.user, self.host)
        else:
            uri += self.host
        if self.port:
            uri += ":%d" % (self.port)
        return uri

    def _convert_kwargs_to_args(self, kwargs):
        args = []
        for k, v in kwargs.items():
            if v is True:
                args.append("-%s" % (k,))
            elif v is False or v is None:
                pass
            else:
                args.append("-%s" % (k,))
                args.append(str(v))
        return args

    def _process_scp_cmdline(self, kwargs):
        args = []
        if "r" not in kwargs:
            kwargs["r"] = True
        if self.keyfile and "i" not in kwargs:
            kwargs["i"] = self.keyfile
        if self.port and "P" not in kwargs:
            kwargs["P"] = self.port
        args.extend(self._convert_kwargs_to_args(kwargs))
        if self.user:
            host = "%s@%s" % (self.user, self.host)
        else:
            host = self.host
        return args, host

    def _process_ssh_cmdline(self, kwargs):
        args = []
        if self.keyfile and "i" not in kwargs:
            kwargs["i"] = self.keyfile
        if self.port and "p" not in kwargs:
            kwargs["p"] = self.port
        args.extend(self._convert_kwargs_to_args(kwargs))
        if self.user:
            args.append("%s@%s" % (self.user, self.host))
        else:
            args.append(self.host)
        return args

    def popen(self, args, sshopts = {}, **kwargs):
        cmdline = self._process_ssh_cmdline(sshopts)
        cmdline.extend(shquote(str(a)) for a in args)
        return self.ssh_command.popen(cmdline, startupinfo = _get_startupinfo(), **kwargs)

    def run(self, args, retcode = 0, sshopts = {}, **kwargs):
        return _run(self.popen(args, sshopts, **kwargs), retcode)

    '''
    def upload(self, src, dst, **kwargs):
        """
        Uploads *src* from the local machine to *dst* on the other side. By default, 
        ``-r`` (recursive copy) is given to ``scp``, so *src* can be either a file or 
        a directory. To override this behavior, pass ``r = False`` as a keyword argument. 
        
        :param src: the source path (on the local side)
        :param dst: the destination path (on the remote side)
        :param kwargs: any additional keyword arguments, passed to ``scp``.
        """
        cmdline, host = self._process_scp_cmdline(kwargs)
        cmdline.append(src)
        cmdline.append("%s:%s" % (host, dst))
        ctx_logger.debug("Upload: %r" % (cmdline,))
        proc = subprocess.Popen(cmdline, stdin = subprocess.PIPE, stdout = subprocess.PIPE, 
            stderr = subprocess.PIPE, shell = False, cwd = self.scp_cwd, env = self.scp_env, 
            startupinfo = _get_startupinfo())
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise ValueError("upload failed", stdout, stderr)

    def download(self, src, dst, **kwargs):
        """
        Downloads *src* from the other side to *dst* on the local side. By default, 
        ``-r`` (recursive copy) is given to ``scp``, so *src* can be either a file or 
        a directory. To override this behavior, pass ``r = False`` as a keyword argument.
        
        :param src: the source path (on the other side)
        :param dst: the destination path (on the local side)
        :param kwargs: any additional keyword arguments, passed to ``scp``.
        """
        cmdline, host = self._process_scp_cmdline(kwargs)
        cmdline.append("%s:%s" % (host, src))
        cmdline.append(dst)
        ctx_logger.debug("Download: %r" % (cmdline,))
        proc = subprocess.Popen(cmdline, stdin = subprocess.PIPE, stdout = subprocess.PIPE, 
            stderr = subprocess.PIPE, shell = False, cwd = self.scp_cwd, env = self.scp_env, 
            startupinfo = _get_startupinfo())
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise ValueError("upload failed", stdout, stderr)
    '''

    def shell(self, tty = False):
        """
        Creates an SSH shell session on the host; this session can be used 
        to execute a stateful series of commands, without needing to create a new
        connection each time 
        
        :param tty: whether to force TTY allocation (ssh -tt); needed for some 
                    interactive programs
        
        :returns: an :class:`SshSession` instance
        """
        return SshSession(self, tty)

    def tunnel(self, loc_port, rem_port, loc_host = "localhost", rem_host = "localhost"):
        """
        Creates an SSH tunnel from the local port to the remote one. This translates 
        to ``ssh -L loc_host:loc_port:rem_host:rem_port``.
        
        :param loc_port: the local TCP port to forward
        :param rem_port: the remote (server) TCP port, to which the local port 
                         will be forwarded
        
        :returns: an :class:`SshTunnel` instance
        """
        session = SshSession(self, tty = False, 
            L = "[%s]:%s:[%s]:%s" % (loc_host, loc_port, rem_host, rem_port))
        return SshTunnel(session, "%s:%s" %(loc_host, loc_port), 
            "(%s)%s:%s" % (self.host, rem_host, rem_port))
    
    def rtunnel(self, rem_port, loc_port, rem_host = "localhost", loc_host = "localhost"):
        """
        Creates a reverse SSH tunnel from the remote port to the local one. This translates 
        to ``ssh -R rem_host:rem_port:loc_host:loc_port``.
        
        :param rem_port: the remote TCP port to forward
        :param rem_port: the local (client) TCP port, to which the remote port 
                         will be forwarded
        
        :returns: an :class:`SshTunnel` instance
        """
        session = SshSession(self, tty = False, 
            R = "[%s]:%s:[%s]:%s" % (rem_host, rem_port, loc_host, loc_port))
        return SshTunnel(session, "(%s)%s:%s" % (self.host, rem_host, rem_port), 
            "%s:%s" % (loc_host, loc_port))


if __name__ == "__main__":
    with local.env(HOME = local.env.home):
        sshctx = SshContext("hollywood.xiv.ibm.com")
        print sshctx.run(["ls"])
    


