import paramiko
from plumbum.remote_machine import BaseRemoteMachine
from plumbum.commands import run_proc


class ParamikoPopen(object):
    def __init__(self, argv, stdin, stdout, stderr):
        self.argv = argv
        self.channel = stdout.channel
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = None
    def poll(self):
        if self.returncode is None:
            if self.channel.exit_status_ready():
                return self.wait()
        return self.returncode
    def wait(self):
        if self.returncode is None:
            self.channel.recv_exit_status()
            self.returncode = self.channel.exit_status
        return self.returncode
    def communicate(self, input = None):
        if input:
            self.stdin.write(input)
        self.wait()
        return self.stdout.read(), self.stderr.read()


class ParamikoSession(object):
    def __init__(self, client, isatty):
        self.client = client
        self.isatty = isatty
    
    def close(self):
        pass
    
    def popen(self, cmd):
        return self.client.popen(cmd)
    
    def run(self, cmd, retcode = 0):
        return run_proc(self.popen(cmd), retcode)


class ParamikoMachine(BaseRemoteMachine):
    def __init__(self, host, user = None, port = None, password = None, keyfile = None, 
            load_system_host_keys = True, encoding = "utf8"):
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
        BaseRemoteMachine.__init__(self, encoding)
    
    def session(self, isatty = False):
        return ParamikoSession(self, isatty)
    
    def popen(self, args):
        cmdline = []
        #envdelta = self.env.getdelta()
        #cmdline.extend(["cd", str(self.cwd), "&&"])
        #if envdelta:
        #    cmdline.append("env")
        #    cmdline.extend("%s=%s" % (k, v) for k, v in envdelta.items())
        if isinstance(args, (tuple, list)):
            cmdline.extend(args)
        else:
            cmdline.append(args)
        si, so, se = self._client.exec_command(" ".join(cmdline))
        return ParamikoPopen(cmdline, si, so, se)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level = 0)
    m = ParamikoMachine("192.168.1.143")
    p = m.popen("ls -l")
    print p.communicate()





