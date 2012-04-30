import os
from tempfile import TemporaryFile


IS_WIN32 = os.name == "nt"

#===================================================================================================
# Exceptions
#===================================================================================================
class ProcessExecutionError(Exception):
    def __init__(self, cmdline, retcode, stdout, stderr):
        Exception.__init__(self, cmdline, retcode, stdout, stderr)
        self.cmdline = cmdline
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        stdout = "\n         | ".join(self.stdout.splitlines())
        stderr = "\n         | ".join(self.stderr.splitlines())
        lines = ["Command line: %r" % (self.cmdline,), "Exit code: %s" % (self.retcode)]
        if stdout:
            lines.append("Stdout:  | %s" % (stdout,))
        if stderr:
            lines.append("Stderr:  | %s" % (stderr,))
        return "\n".join(lines)

class CommandNotFound(Exception):
    def __init__(self, progname, path):
        Exception.__init__(self, progname, path)
        self.progname = progname
        self.path = path

#===================================================================================================
# Utilities
#===================================================================================================
def run_proc(proc, retcode):
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = ""
    if not stderr:
        stderr = ""
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "cmdline", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

def make_input(data, CHUNK_SIZE = 16000):
    f = TemporaryFile()
    while data:
        chunk = data[:CHUNK_SIZE]
        f.write(chunk)
        data = data[CHUNK_SIZE:]
    f.seek(0)
    return f

#===================================================================================================
# execution modifiers (background, foreground)
#===================================================================================================
class ExecutionModifier(object):
    def __init__(self, retcode = 0):
        self.retcode = retcode
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.retcode)
    @classmethod
    def __call__(cls, retcode):
        return cls(retcode)

class Future(object):
    def __init__(self, proc, expected_retcode):
        self.proc = proc
        self._expected_retcode = expected_retcode
        self._returncode = None
        self._stdout = None
        self._stderr = None
    def __repr__(self):
        return "<Future %r (%s)>" % (self.proc.cmdline, self._returncode if self.ready() else "running",)
    def poll(self):
        if self.proc.poll() is not None:
            self.wait()
        return self._returncode is not None
    ready = poll
    def wait(self):
        if self._returncode is not None:
            return
        self._returncode, self._stdout, self._stderr = run_proc(self.proc, self._expected_retcode)
    @property
    def stdout(self):
        self.wait()
        return self._stdout
    @property
    def stderr(self):
        self.wait()
        return self._stderr
    @property
    def returncode(self):
        self.wait()
        return self._returncode

class BG(ExecutionModifier):
    def __rand__(self, cmd):
        return Future(cmd.popen(), self.retcode)
BG = BG()

class FG(ExecutionModifier):
    def __rand__(self, cmd):
        cmd(retcode = self.retcode, stdin = None, stdout = None, stderr = None)
FG = FG()



