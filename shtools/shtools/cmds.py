from subprocess import PIPE, Popen


class Env(object):
    pass

class Workdir(object):
    pass


env = Env()
cwd = Workdir()


class Command(object):
    retcodes = (0,)
    def __init__(self, executable):
        self.executable = executable
    def __repr__(self):
        return "<Command %s>" % (self.executable,)
    def pipe(self, destproc):
        pass
    def redirect(self, filename):
        pass
    def run(self, *args, **kwargs):
        cmdargs = [str(self.executable)] + list(args)
        for k, v in kwargs.items():
            if len(k) == 1:
                cmdargs.append("-" + k)
            else:
                cmdargs.append("--" + k)
            if v is True:
                pass
            elif v is False or v is None:
                cmdargs.pop(-1)
            else:
                cmdargs.append(str(v))
        proc = Popen(cmdargs, executable = str(self.executable), stdin = PIPE, stdout = PIPE, 
            stderr = PIPE, cwd = str(cwd), env = env.getdict())
        stdout, stderr = proc.communicate()
        if proc.returncode not in self.retcodes:
            raise CommandFailure(cmdargs, proc.returncode, stdout, stderr)
        return stdout, stderr
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)[0]


class _CommandNamespace(object):
    @classmethod
    def which(cls, progname):
        for p in env.path:
            try:
                filelist = {n.basename : n for n in p.list()}
            except OSError:
                continue
            for ext in ["", ".exe", ".bat"]:
                n = progname + ext
                if n in filelist:
                    return filelist[n]
        raise ProgramNotFound(progname, list(env.path))
    def __getattr__(self, name):
        return self[name]
    def __getitem__(self, name):
        name = str(name)
        if "/" in name or "\\" in name:
            return Command(name)
        else:
            return Command(self.which(name))

cmd = _CommandNamespace()


ls = cmd.ls
grep = cmd.grep

#(ls["-l"] | grep["foo"])()








