import unittest
from getpass import getuser

from plumbum import local, SshMachine, Cluster, ProcessExecutionError


TEST_HOST = "127.0.0.1"


class TestParallelSsh(unittest.TestCase):

    RemoteMachine = SshMachine

    def setUp(self):
        self.remotes = []

    def connect(self):
        m = self.RemoteMachine(TEST_HOST)
        self.remotes.append(m)
        return m

    def tearDown(self):
        for m in self.remotes:
            m.close()

    def test_parallel(self):
        m = Cluster(local, local)
        import time
        t = time.time()
        ret = m["sleep"]("2")
        assert(len(ret) == 2)
        assert(2 <= time.time() - t < 4)

    def test_locals(self):
        m = Cluster(local, local, local)
        # we should get 3 different proc ids
        ret = m["bash"]["-c"]["echo $$"]()
        ret = list(map(int, ret))
        assert(len(set(ret))==3)

    def test_sessions(self):
        m = Cluster(local, self.connect(), local, self.connect())
        # we should get 4 different proc ids
        ret, stdout, stderr = m.session().run("echo $$")
        ret = [int(pid) for pid in stdout]
        assert(len(set(ret))==4)

    def test_commands(self):
        cmds = local["echo"]["1"] & local["echo"]["2"]
        ret = cmds()
        a, b = map(int, ret)
        assert((a, b) == (1, 2))

    def test_as_user(self):
        m = Cluster(self.connect(), local, self.connect())
        env = m["env"]

        def get_user_from_env():
            ret, = tuple(set(l.split("=")[-1]
                        for ret in env()
                        for l in ret.splitlines()
                        if l.startswith("USER=")))
            return ret

        assert(get_user_from_env() == getuser())

        with m.as_root():
            assert(get_user_from_env() == "root")


try:
    import paramiko
except ImportError:
    print("Paramiko not avilable")
else:

    from plumbum.machines.paramiko_machine import ParamikoMachine
    from paramiko import AutoAddPolicy
    from functools import partial
    ParamikoMachine = partial(ParamikoMachine, missing_host_policy=AutoAddPolicy())

    class TestParallelParamiko(TestParallelSsh):
        RemoteMachine = ParamikoMachine
