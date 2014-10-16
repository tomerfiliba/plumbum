import unittest

from plumbum import local, SshMachine


TEST_HOST = "127.0.0.1"


class TestMulti(unittest.TestCase):

    def setUp(self):
        self.remotes = []

    def connect(self):
        m = SshMachine(TEST_HOST)
        self.remotes.append(m)
        return m

    def tearDown(self):
        for m in self.remotes:
            m.close()

    def test_parallel(self):
        m = local + local
        import time
        t = time.time()
        ret = m["sleep"]("2")
        assert(len(ret) == 2)
        assert(2 <= time.time() - t < 4)

    def test_locals(self):
        m = local + local + local
        # we should get 3 different proc ids
        ret = m["bash"]["-c"]["echo $$"]()
        ret = list(map(int, ret))
        assert(len(set(ret))==3)

    def test_sessions(self):
        m1 = local + self.connect()
        m2 = local + self.connect()
        m = m1 + m2
        # we should get 4 different proc ids
        ret = m.session().run("echo $$")
        ret = [int(pid) for _, pid, _ in ret]
        assert(len(set(ret))==4)

    def test_commands(self):
        cmds = local["echo"]["1"] + local["echo"]["2"]
        ret = cmds()
        a, b = map(int, ret)
        assert((a, b) == (1, 2))
