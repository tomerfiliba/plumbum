import time
import random
import logging
import six
from plumbum.commands import BaseCommand, run_proc


class ShellSessionError(Exception):
    """Raises when something goes wrong when calling 
    :func:`ShellSession.popen <plumbum.session.ShellSession.popen>`"""
    pass

shell_logger = logging.getLogger("plumbum.shell")


#===================================================================================================
# Shell Session Popen
#===================================================================================================
class MarkedPipe(object):
    """A pipe-like object from which you can read lines; the pipe will return report EOF (the 
    empty string) when a special marker is detected"""
    __slots__ = ["pipe", "marker"]
    def __init__(self, pipe, marker):
        self.pipe = pipe
        self.marker = marker
        if six.PY3:
            self.marker = bytes(self.marker, "ascii")
    def close(self):
        """'Closes' the marked pipe; following calls to ``readline`` will return """""
        # consume everything
        while self.readline():
            pass 
        self.pipe = None
    def readline(self):
        """Reads the next line from the pipe; returns "" when the special marker is reached.
        Raises ``EOFError`` if the underlying pipe has closed"""
        if self.pipe is None:
            return six.b("")
        line = self.pipe.readline()
        if not line:
            raise EOFError()
        if line.strip() == self.marker:
            self.pipe = None
            line = six.b("")
        return line


class SessionPopen(object):
    """A shell-session-based ``Popen``-like object (has the following attributes: ``stdin``,
    ``stdout``, ``stderr``, ``returncode``)"""
    def __init__(self, argv, isatty, stdin, stdout, stderr, encoding):
        self.argv = argv
        self.isatty = isatty
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.encoding = encoding
        self.returncode = None
        self._done = False
    def poll(self):
        """Returns the process' exit code or ``None`` if it's still running"""
        if self._done:
            return self.returncode
        else:
            return None
    def wait(self):
        """Waits for the process to terminate and returns its exit code"""
        self.communicate()
        return self.returncode
    def communicate(self, input = None):
        """Consumes the process' stdout and stderr until the it terminates. 
        
        :param input: An optional bytes/buffer object to send to the process over stdin
        :returns: A tuple of (stdout, stderr)
        """
        stdout = []
        stderr = []
        sources = [("1", stdout, self.stdout)]
        if not self.isatty:
            # in tty mode, stdout and stderr are unified
            sources.append(("2", stderr, self.stderr))
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
            shell_logger.debug("%s> %r", name, line)
            if not line:
                del sources[i]
            else:
                coll.append(line)
        if self.isatty:
            stdout.pop(0) # discard first line of prompt
        try:
            self.returncode = int(stdout.pop(-1))
        except (IndexError, ValueError):
            self.returncode = "Unknown"
        self._done = True
        stdout = six.b("").join(stdout)
        stderr = six.b("").join(stderr)
        return stdout, stderr


class ShellSession(object):
    """An abstraction layer over *shell sessions*. A shell session is the execution of an
    interactive shell (``/bin/sh`` or something compatible), over which you may run commands
    (sent over stdin). The output of is then read from stdout and stderr. Shell sessions are
    less "robust" than executing a process on its own, and they are susseptible to all sorts
    of malformatted-strings attacks, and there is little benefit from using them locally. 
    However, they can greatly speed up remote connections, and are required for the implementation
    of :class:`SshMachine <plumbum.remote_machine.SshMachine>`, as they allow us to send multiple
    commands over a single SSH connection (setting up separate SSH connections incurs a high
    overhead). Try to avoid using shell sessions, unless you know what you're doing. 
    
    Instances of this class may be used as *context-managers*.
    
    :param proc: The underlying shell process (with open stdin, stdout and stderr)
    :param encoding: The encoding to use for the shell session. If ``"auto"``, the underlying
                     process' encoding is used.
    :param isatty: If true, assume the shell has a TTY and that stdout and stderr are unified 
    """
    def __init__(self, proc, encoding = "auto", isatty = False):
        self.proc = proc
        self.encoding = proc.encoding if encoding == "auto" else encoding  
        self.isatty = isatty
        self._current = None
        self.run("")
    
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
    
    def alive(self):
        """Returns ``True`` if the underlying shell process is alive, ``False`` otherwise"""
        return self.proc and self.proc.poll() is None
    
    def close(self):
        """Closes (terminates) the shell session"""
        if not self.alive():
            return
        try:
            self.proc.stdin.write(six.b("\nexit\n\n\nexit\n\n"))
            self.proc.stdin.flush()
            time.sleep(0.05)
        except (ValueError, EnvironmentError):
            pass
        for p in [self.proc.stdin, self.proc.stdout, self.proc.stderr]:
            try:
                p.close()
            except Exception:
                pass
        try:
            self.proc.kill()
        except EnvironmentError:
            pass
        self.proc = None
    
    def popen(self, cmd):
        """Runs the given command in the shell, adding some decoration around it. Only a single
        command can be executed at any given time.
        
        :param cmd: The command (string or :class:`Command <plumbum.commands.BaseCommand>` object)
                    to run
        :returns: An :class:`SessionPopen <plumbum.session.SessionPopen>` instance
        """
        if self.proc is None:
            raise ShellSessionError("Shell session has already been closed")
        if self._current and not self._current._done:
            raise ShellSessionError("Each shell may start only one process at a time")
        
        if isinstance(cmd, BaseCommand):
            full_cmd = cmd.formulate(1)
        else:
            full_cmd = cmd
        marker = "--.END%s.--" % (time.time() * random.random(),)
        if full_cmd.strip():
            full_cmd += " ; "
        else:
            full_cmd = "true ; "
        full_cmd += "echo $? ; echo '%s'" % (marker,)
        if not self.isatty:
            full_cmd += " ; echo '%s' 1>&2" % (marker,)
        if self.encoding:
            full_cmd = full_cmd.encode(self.encoding)
        shell_logger.debug("Running %r", full_cmd)
        self.proc.stdin.write(full_cmd + six.b("\n"))
        self.proc.stdin.flush()
        self._current = SessionPopen(full_cmd, self.isatty, self.proc.stdin, 
            MarkedPipe(self.proc.stdout, marker), MarkedPipe(self.proc.stderr, marker),
            self.encoding)
        return self._current
    
    def run(self, cmd, retcode = 0):
        """Runs the given command 
        
        :param cmd: The command (string or :class:`Command <plumbum.commands.BaseCommand>` object)
                    to run
        :param retcode: The expected return code (0 by default). Set to ``None`` in order to 
                        ignore erroneous return codes
        :returns: A tuple of (return code, stdout, stderr)
        """
        return run_proc(self.popen(cmd), retcode)

