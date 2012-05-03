import time
import random
import logging
from plumbum.commands import BaseCommand, run_proc


class ShellSessionError(Exception):
    pass

shell_logger = logging.getLogger("plumbum.shell")


#===================================================================================================
# Shell Session Popen
#===================================================================================================
class MarkedPipe(object):
    __slots__ = ["pipe", "marker"]
    def __init__(self, pipe, marker):
        self.pipe = pipe
        self.marker = marker
    def close(self):
        pass
    def readline(self):
        line = self.pipe.readline()
        if not line:
            raise EOFError()
        if line.strip() == self.marker:
            return ""
        return line

class SessionPopen(object):
    def __init__(self, argv, isatty, stdin, stdout, stderr):
        self.argv = argv
        self.isatty = isatty
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = None
        self._done = False
    def poll(self):
        if self._done:
            return self.returncode
        else:
            return None
    def wait(self):
        self.communicate()
        return self.returncode
    def communicate(self, input = None):
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
        stdout = b"".join(stdout)
        stderr = b"".join(stderr)
        return stdout, stderr


class ShellSession(object):
    def __init__(self, proc, isatty = False):
        self.proc = proc
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
        """returns True if the ``ssh`` process is alive, False otherwise"""
        return self.proc and self.proc.poll() is None
    
    def close(self):
        if not self.alive():
            return
        try:
            self.proc.stdin.write(b"\nexit\n\n\nexit\n\n")
            self.proc.stdin.close()
            time.sleep(0.05)
        except (ValueError, EnvironmentError):
            pass
        try:
            self.proc.kill()
        except EnvironmentError:
            pass
        self.proc = None
    
    def popen(self, cmd, retcode = 0):
        if self._current and not self._current._done:
            raise ShellSessionError("Each shell may start only one process at a time")
        
        if isinstance(cmd, BaseCommand):
            full_cmd = cmd.formulate(1)
        else:
            full_cmd = cmd
        marker = b"--.END%s.--" % (time.time() * random.random())
        if full_cmd.strip():
            full_cmd += " ; "
        else:
            full_cmd = "echo -n ''; "
        full_cmd += "echo $? ; echo %s" % (marker,)
        if not self.isatty:
            full_cmd += " ; echo %s 1>&2" % (marker,)
        shell_logger.debug("Running %r", full_cmd)
        self.proc.stdin.write(full_cmd + "\n")
        self._current = SessionPopen(full_cmd, self.isatty, self.proc.stdin, 
            MarkedPipe(self.proc.stdout, marker), MarkedPipe(self.proc.stderr, marker))
        return self._current
    
    def run(self, cmd, retcode = 0):
        return run_proc(self.popen(cmd), retcode)

