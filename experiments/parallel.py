from plumbum.commands.base import BaseCommand
from plumbum.commands.processes import run_proc, CommandNotFound, ProcessExecutionError

def make_concurrent(self, rhs):
    if not isinstance(rhs, BaseCommand):
        raise TypeError("rhs must be an instance of BaseCommand")
    if isinstance(self, ConcurrentCommand):
        if isinstance(rhs, ConcurrentCommand):
            self.commands.extend(rhs.commands)
        else:
            self.commands.append(rhs)
        return self
    elif isinstance(rhs, ConcurrentCommand):
        rhs.commands.insert(0, self)
        return rhs
    else:
        return ConcurrentCommand(self, rhs)

BaseCommand.__and__ = make_concurrent

class ConcurrentPopen(object):
    def __init__(self, procs):
        self.procs = procs
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.encoding = None
        self.returncode = None
    @property
    def argv(self):
        return [getattr(proc, "argv", []) for proc in self.procs]
    def poll(self):
        if self.returncode is not None:
            return self.returncode
        rcs = [proc.poll() for proc in self.procs]
        if any(rc is None for rc in rcs):
            return None
        self.returncode = 0
        for rc in rcs:
            if rc != 0:
                self.returncode = rc
                break
        return self.returncode

    def wait(self):
        for proc in self.procs:
            proc.wait()
        return self.poll()
    def communicate(self, input=None):
        if input:
            raise ValueError("Cannot pass input to ConcurrentPopen.communicate")
        out_err_tuples = [proc.communicate() for proc in self.procs]
        self.wait()
        return tuple(zip(*out_err_tuples))

class ConcurrentCommand(BaseCommand):
    def __init__(self, *commands):
        self.commands = list(commands)
    def formulate(self, level=0, args=()):
        form = ["("]
        for cmd in self.commands:
            form.extend(cmd.formulate(level, args))
            form.append("&")
        return form + [")"]
    def popen(self, *args, **kwargs):
        return ConcurrentPopen([cmd[args].popen(**kwargs) for cmd in self.commands])
    def __getitem__(self, args):
        """Creates a bound-command with the given arguments"""
        if not isinstance(args, (tuple, list)):
            args = [args, ]
        if not args:
            return self
        else:
            return ConcurrentCommand(*(cmd[args] for cmd in self.commands))


class Cluster(object):
    def __init__(self, *machines):
        self.machines = list(machines)
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def close(self):
        for mach in self.machines:
            mach.close()
        del self.machines[:]

    def add_machine(self, machine):
        self.machines.append(machine)
    def __iter__(self):
        return iter(self.machines)
    def filter(self, pred):
        return self.__class__(filter(pred, self))
    def which(self, progname):
        return [mach.which(progname) for mach in self]
    def list_processes(self):
        return [mach.list_processes() for mach in self]
    def pgrep(self, pattern):
        return [mach.pgrep(pattern) for mach in self]
    def path(self, *parts):
        return [mach.path(*parts) for mach in self]
    def __getitem__(self, progname):
        if not isinstance(progname, str):
            raise TypeError("progname must be a string, not %r" % (type(progname,)))
        return ConcurrentCommand(*(mach[progname] for mach in self))
    def __contains__(self, cmd):
        try:
            self[cmd]
        except CommandNotFound:
            return False
        else:
            return True

    @property
    def python(self):
        return ConcurrentCommand(*(mach.python for mach in self))

    def session(self):
        return ClusterSession(*(mach.session() for mach in self))

class ClusterSession(object):

    def __init__(self, *sessions):
        self.sessions = sessions
    def __iter__(self):
        return iter(self.sessions)
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
        """Returns ``True`` if the underlying shells are all alive, ``False`` otherwise"""
        return all(session.alive for session in self)
    def close(self):
        """Closes (terminates) all underlying shell sessions"""
        for session in self.sessions:
            session.close()
        del self.sessions[:]
    def popen(self, cmd):
        return ConcurrentPopen([session.popen(cmd) for session in self])
    def run(self, cmd, retcode=None):
        return run_proc(self.popen(cmd), retcode)


if __name__ == "__main__":
    from plumbum import local
    from plumbum.cmd import ls, date, sleep
    c = ls & date & sleep[1]
    print(c())

    c = ls & date & sleep[1] & sleep["-z"]
    try:
        c()
    except ProcessExecutionError as ex:
        print(ex)
    else:
        assert False

    clst = Cluster(local, local, local)
    print(clst["ls"]())


    # This works fine
    print(local.session().run("echo $$"))

    # this does not
    ret, stdout, stderr = clst.session().run("echo $$")
    print(ret)
    ret = [int(pid) for pid in stdout]
    assert(len(set(ret))==3)







