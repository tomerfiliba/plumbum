from tempfile import TemporaryFile
from subprocess import PIPE, Popen
import subprocess
import sys
import threading
from contextlib import contextmanager
import random
import time


class ProcessExecutionError(Exception):
    def __init__(self, argv, retcode, stdout, stderr):
        Exception.__init__(self, argv, retcode, stdout, stderr)
        self.argv = argv
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
    def __str__(self):
        stdout = "\n         | ".join(self.stdout.splitlines())
        stderr = "\n         | ".join(self.stderr.splitlines())
        lines = ["Command line: %r" % (self.argv,), "Exit code: %s" % (self.retcode)]
        if stdout:
            lines.append("Stdout:  | %s" % (stdout,))
        if stderr:
            lines.append("Stderr:  | %s" % (stderr,))
        return "\n".join(lines)

class RedirectionError(Exception):
    pass
class ShellSessionError(Exception):
    pass

#===================================================================================================
# Utilities
#===================================================================================================
# modified from the stdlib pipes module for windows
_safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
_funnychars = '"`$\\'
def shquote(text):
    if not text:
        return "''"
    text = str(text)
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = "".join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'

def shquote_list(seq):
    return [shquote(item) for item in seq]

def run_proc(proc, retcode):
    stdout, stderr = proc.communicate()
    if not stdout:
        stdout = ""
    if not stderr:
        stderr = ""
    if retcode is not None and proc.returncode != retcode:
        raise ProcessExecutionError(getattr(proc, "argv", None), 
            proc.returncode, stdout, stderr)
    return proc.returncode, stdout, stderr

#===================================================================================================
# Commands
#===================================================================================================
class BaseCommand(object):
    cwd = None
    env = None
    
    def __str__(self):
        return " ".join(self.formulate())
    def __or__(self, other):
        return Pipeline(self, other)
    def __gt__(self, file):
        return StdoutRedirection(self, file)
    def __ge__(self, file):
        return StderrRedirection(self, file)
    def __lt__(self, file):
        return StdinRedirection(self, file)
    def __lshift__(self, data):
        return StdinDataRedirection(self, data)
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)
        return BoundCommand(self, args)
    def __call__(self, *args, **kwargs):
        return self.run(args, **kwargs)[1]
    
    def formulate(self, args = ()):
        raise NotImplementedError()
    def popen(self, args = (), **kwargs):
        raise NotImplementedError()
    
    def run(self, args = (), **kwargs):
        retcode = kwargs.pop("retcode", 0)
        return run_proc(self.popen(args, **kwargs), retcode)

class BoundCommand(BaseCommand):
    def __init__(self, cmd, args):
        self.cmd = cmd
        self.args = args

    def formulate(self, args = ()):
        with formulation_level():
            return self.cmd.formulate(self.args + tuple(args))
    
    def popen(self, args = (), **kwargs):
        if isinstance(args, str):
            args = (args,)
        return self.cmd.popen(self.args + tuple(args), **kwargs)

class Pipeline(BaseCommand):
    def __init__(self, srccmd, dstcmd):
        self.srccmd = srccmd
        self.dstcmd = dstcmd

    def formulate(self, args = ()):
        with formulation_level():
            return self.srccmd.formulate() + ["|"] + self.dstcmd.formulate(args)

    def popen(self, args = (), **kwargs):
        src_kwargs = kwargs.copy()
        src_kwargs["stdout"] = PIPE
        #src_kwargs["stderr"] = PIPE
        
        srcproc = self.srccmd.popen(args, **src_kwargs)
        kwargs["stdin"] = srcproc.stdout
        dstproc = self.dstcmd.popen(**kwargs)
        srcproc.stdout.close() # allow p1 to receive a SIGPIPE if p2 exits
        srcproc.stderr.close()
        dstproc.srcproc = srcproc
        return dstproc

class BaseRedirection(BaseCommand):
    SYM = None
    KWARG = None
    MODE = None
    
    def __init__(self, cmd, file):
        self.cmd = cmd
        self.file = file
    def formulate(self, args = ()):
        with formulation_level():
            return self.cmd.formulate(args) + [self.SYM, shquote(getattr(self.file, "name", self.file))]
    def popen(self, args = (), **kwargs):
        if self.KWARG in kwargs and kwargs[self.KWARG] != PIPE:
            raise RedirectionError("%s is already redirected" % (self.KWARG,))
        if isinstance(self.file, str):
            kwargs[self.KWARG] = open(self.file, self.MODE)
        else:
            kwargs[self.KWARG] = self.file
        return self.cmd.popen(args, **kwargs)

class StdinRedirection(BaseRedirection):
    SYM = "<"
    KWARG = "stdin"
    MODE = "r"

class StdoutRedirection(BaseRedirection):
    SYM = ">"
    KWARG = "stdout"
    MODE = "w"

class StderrRedirection(BaseRedirection):
    SYM = "2>"
    KWARG = "stderr"
    MODE = "w"

class StdinDataRedirection(BaseCommand):
    CHUNK_SIZE = 16000
    TRUNCATE = 15
    
    def __init__(self, cmd, data):
        self.cmd = cmd
        self.data = data
    
    def __str__(self):
        shortened = self.data[:self.TRUNCATE]
        if len(self.data) > self.TRUNCATE:
            shortened += "..."
        return "%s << %r" % (self.cmd, shortened)
    
    def formulate(self, args = ()):
        raise NotImplementedError()
        #return shquote_list(self.cmd.formulate(args)) + [self.SYM] + \
        #    [shquote(getattr(self.file, "name", self.file))]
    
    def popen(self, args = (), **kwargs):
        if "stdin" in kwargs and kwargs["stdin"] != PIPE:
            raise RedirectionError("stdin is already redirected")
        data = self.data
        f = TemporaryFile()
        while data:
            chunk = data[:self.CHUNK_SIZE]
            f.write(chunk)
            data = data[self.CHUNK_SIZE:]
        f.seek(0)
        return self.cmd.popen(args, stdin = f, **kwargs)


_thread_local_level = threading.local()
@contextmanager
def formulation_level():
    if not hasattr(_thread_local_level, "level"):
        _thread_local_level.level = 0
    curr = _thread_local_level.level
    _thread_local_level.level += 1
    try:
        yield curr
    finally:
        _thread_local_level.level -= 1

class LocalCommand(BaseCommand):
    def __init__(self, executable):
        self.executable = executable

    def __str__(self):
        return str(self.executable)

    def formulate(self, args = ()):
        with formulation_level() as level:
            argv = [str(self.executable)]
            for a in args:
                if not a:
                    continue
                if isinstance(a, BaseCommand):
                    if level >= 2:
                        argv.extend(shquote_list(a.formulate()))
                    else:
                        argv.extend(a.formulate())
                else:
                    if level >= 2:
                        argv.append(shquote(a))
                    else:
                        argv.append(a)
            return argv
    
    def popen(self, args = (), stdin = PIPE, stdout = PIPE, stderr = PIPE, cwd = None, 
            env = None, **kwargs):
        if isinstance(args, str):
            args = (args,)
        if subprocess.mswindows and "startupinfo" not in kwargs and not sys.stdin.isatty():
            kwargs["startupinfo"] = subprocess.STARTUPINFO()
            kwargs["startupinfo"].dwFlags |= subprocess.STARTF_USESHOWWINDOW  #@UndefinedVariable
            kwargs["startupinfo"].wShowWindow = subprocess.SW_HIDE  #@UndefinedVariable
        argv = self.formulate(args)
        print "!!", argv
        proc = Popen(argv, executable = str(self.executable), stdin = stdin, stdout = stdout, 
            stderr = stderr, cwd = cwd, env = env, **kwargs)
        proc.argv = argv
        return proc

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
            try:
                line = pipe.readline()
            except EOFError:
                self.close()
                break
            #print "%s> %r" % (name, line)
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
        self.proc.stdin.write(b"\nexit\n\n\nexit\n\n")
        self.proc.stdin.close()
        time.sleep(0.05)
        self.proc.kill()
        self.proc = None
    
    def popen(self, cmd, retcode = 0):
        if self._current and not self._current._done:
            raise ShellSessionError("Each shell may start only one process at a time")
        
        full_cmd = str(cmd)
        marker = b"--END%s--" % (time.time() * random.random())
        if full_cmd.strip():
            full_cmd += " ; "
        full_cmd += "echo $? ; echo %s" % (marker,)
        if not self.isatty:
            full_cmd += " ; echo %s 1>&2" % (marker,)
        #print "@@", full_cmd
        self.proc.stdin.write(full_cmd + "\n")
        self._current = SessionPopen(full_cmd, self.isatty, self.proc.stdin, 
            MarkedPipe(self.proc.stdout, marker), MarkedPipe(self.proc.stderr, marker))
        return self._current
    
    def run(self, cmd, retcode = 0):
        return run_proc(self.popen(cmd), retcode)



class SshContext(object):
    def __init__(self, host, user = None, port = None, keyfile = None, ssh_command = None, 
            scp_command = None, ssh_opts = (), scp_opts = ()):
        if ssh_command is None:
            ssh_command = LocalCommand("ssh")
        if scp_command is None:
            scp_command = LocalCommand("scp")
        if user:
            self._fqhost = "%s@%s" % (user, host)
        else:
            self._fqhost = host
        scp_args = []
        ssh_args = [self._fqhost]
        if port:
            ssh_args.extend(["-p", port])
            scp_args.extend(["-P", port])
        if keyfile:
            ssh_args.extend(["-i", keyfile])
            scp_args.extend(["-i", keyfile])
        scp_args.append("-r")
        ssh_args.extend(ssh_opts)
        scp_args.extend(scp_opts)
        self.ssh_command = ssh_command[tuple(ssh_args)]
        self.scp_command = scp_command[tuple(scp_args)]
    
    def session(self, isatty = False):
        return ShellSession(self.ssh_command.popen(["-tt" if isatty else ""]), isatty)
    
    def download(self, src, dst):
        pass
    
    def upload(self, src, dst):
        pass
    
    def tunnel(self, local_port, remote_port):
        pass




class SshCommand(BaseCommand):
    def __init__(self, remote, executable):
        self.remote = remote
        self.executable = executable
    
    def formulate(self, args = ()):
        argv = [str(self.executable)]
        for a in args:
            if not a:
                continue
            if isinstance(a, BaseCommand):
                argv.extend(a.formulate())
            else:
                argv.append(a)
        return argv
    
    def popen(self, args = (), **kwargs):
        return self.remote.sshctx.popen(args, **kwargs)


with ShellSession(LocalCommand("sh").popen()) as shl:
    print shl.run("echo hi")
    print shl.run("echo hi")


#
#ls = LocalCommand("ls")
#grep = LocalCommand("grep")
#echo = LocalCommand("echo")
#sudo = LocalCommand("sudo")
#ssh = LocalCommand("ssh")
#pwd = LocalCommand("pwd")
#
#
##print sudo[ls | grep["py"]]
##print sudo[sudo[ls | grep["py"]]]
#
#cmd = ssh["localhost", "cd", "/usr", "&&", ssh["localhost", "cd", "/", "&&", ssh["localhost", "cd", "/bin", "&&", pwd]]]
#print cmd
#print cmd()









