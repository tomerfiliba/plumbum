from __future__ import with_statement
import sys
import os
import socket
import unittest
import time
import logging
from plumbum import RemotePath, SshMachine, ProcessExecutionError, local, ProcessTimedOut
from plumbum import CommandNotFound
from plumbum.lib import six


#TEST_HOST = "192.168.1.143"
TEST_HOST = "127.0.0.1"
if TEST_HOST not in ("::1", "127.0.0.1", "localhost"):
    import plumbum
    plumbum.local.env.path.append("c:\\Program Files\\Git\\bin")

if not hasattr(unittest, "skipIf"):
    import functools
    def skipIf(cond, msg = None):
        def deco(func):
            if cond:
                return func
            else:
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    logging.warn("skipping test")
                return wrapper
        return deco
    unittest.skipIf = skipIf

class RemotePathTest(unittest.TestCase):
    def _connect(self):
        return SshMachine(TEST_HOST)

    def test_basename(self):
        name = RemotePath(self._connect(), "/some/long/path/to/file.txt").basename
        self.assertTrue(isinstance(name, six.string_types))
        self.assertEqual("file.txt", str(name))

    def test_dirname(self):
        name = RemotePath(self._connect(), "/some/long/path/to/file.txt").dirname
        self.assertTrue(isinstance(name, RemotePath))
        self.assertEqual("/some/long/path/to", str(name))

    @unittest.skipIf(not hasattr(os, "chown"), "os.chown not supported")
    def test_chown(self):
        with self._connect() as rem:
            with rem.tempdir() as dir:
                p = dir / "foo.txt"
                p.write(six.b("hello"))
                # because we're connected to localhost, we expect UID and GID to be the same
                self.assertEqual(p.uid, os.getuid())
                self.assertEqual(p.gid, os.getgid())
                p.chown(p.uid.name)
                self.assertEqual(p.uid, os.getuid())


class BaseRemoteMachineTest(object):
    TUNNEL_PROG = r"""import sys, socket
s = socket.socket()
if sys.version_info[0] < 3:
    b = lambda x: x
else:
    b = lambda x: bytes(x, "utf8")
s.bind(("", 0))
s.listen(1)
sys.stdout.write(b("%s\n" % (s.getsockname()[1],)))
sys.stdout.flush()
s2, _ = s.accept()
data = s2.recv(100)
s2.send(b("hello ") + data)
s2.close()
s.close()
"""

    def test_basic(self):
        with self._connect() as rem:
            r_ssh = rem["ssh"]
            r_ls = rem["ls"]
            r_grep = rem["grep"]

            self.assertTrue(".bashrc" in r_ls("-a").splitlines())
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                cmd = r_ssh["localhost", "cd", rem.cwd, "&&", r_ls, "|", r_grep["\\.py"]]
                self.assertTrue("'|'" in str(cmd))
                self.assertTrue("test_remote.py" in cmd())
                self.assertTrue("test_remote.py" in [f.basename for f in rem.cwd // "*.py"])

    def test_download_upload(self):
        with self._connect() as rem:
            rem.upload("test_remote.py", "/tmp")
            r_ls = rem["ls"]
            r_rm = rem["rm"]
            self.assertTrue("test_remote.py" in r_ls("/tmp").splitlines())
            rem.download("/tmp/test_remote.py", "/tmp/test_download.txt")
            r_rm("/tmp/test_remote.py")
            r_rm("/tmp/test_download.txt")

    def test_session(self):
        with self._connect() as rem:
            sh = rem.session()
            for _ in range(4):
                _, out, _ = sh.run("ls -a")
                self.assertTrue(".bashrc" in out)

    def test_env(self):
        with self._connect() as rem:
            self.assertRaises(ProcessExecutionError, rem.python, "-c",
                "import os;os.environ['FOOBAR72']")
            with rem.env(FOOBAR72 = "lala"):
                with rem.env(FOOBAR72 = "baba"):
                    out = rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
                    self.assertEqual(out.strip(), "baba")
                out = rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
                self.assertEqual(out.strip(), "lala")

            # path manipulation
            self.assertRaises(CommandNotFound, rem.which, "dummy-executable")
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                rem.env.path.insert(0, rem.cwd / "not-in-path")
                p = rem.which("dummy-executable")
                self.assertEqual(p, rem.cwd / "not-in-path" / "dummy-executable")

    def test_read_write(self):
        with self._connect() as rem:
            with rem.tempdir() as dir:
                self.assertTrue(dir.isdir())
                data = six.b("hello world")
                (dir / "foo.txt").write(data)
                self.assertEqual((dir / "foo.txt").read(), data)

            self.assertFalse(dir.exists())

    def test_contains(self):
        with self._connect() as rem:
            self.assertTrue("ls" in rem, "Expected to find `ls`")

    def test_iter_lines_timeout(self):
        with self._connect() as rem:
            try:
                for i, (out, err) in enumerate(rem["ping"]["127.0.0.1", "-i", 0.5].popen().iter_lines(timeout=2)):
                    print("out:", out)
                    print("err:", err)
            except NotImplementedError:
                try:
                    self.skipTest(sys.exc_info()[1])
                except AttributeError:
                    return
            except ProcessTimedOut:
                self.assertTrue(i > 3)
            else:
                self.fail("Expected a timeout")


    def test_iter_lines_error(self):
        with self._connect() as rem:
            try:
                for i, lines in enumerate(rem["ls"]["--bla"].popen()):
                    pass
                self.assertEqual(i, 1)
            except ProcessExecutionError:
                ex = sys.exc_info()[1]
                self.assertTrue(ex.stderr.startswith("/bin/ls: unrecognized option '--bla'"))
            else:
                self.fail("Expected an execution error")


class RemoteMachineTest(unittest.TestCase, BaseRemoteMachineTest):
    def _connect(self):
        return SshMachine(TEST_HOST)

    def test_tunnel(self):
        with self._connect() as rem:
            p = (rem.python["-u"] << self.TUNNEL_PROG).popen()
            try:
                port = int(p.stdout.readline().strip())
            except ValueError:
                print(p.communicate())
                raise

            with rem.tunnel(12222, port) as tun:
                s = socket.socket()
                s.connect(("localhost", 12222))
                s.send(six.b("world"))
                data = s.recv(100)
                s.close()
                self.assertEqual(data, six.b("hello world"))

            p.communicate()

    def test_list_processes(self):
        with self._connect() as rem:
            self.assertTrue(list(rem.list_processes()))

    def test_pgrep(self):
        with self._connect() as rem:
            self.assertTrue(list(rem.pgrep("ssh")))

    def test_nohup(self):
        with self._connect() as rem:
            sleep = rem["sleep"]
            rem.nohup(sleep["5.793817"])
            self.assertTrue(list(rem.pgrep("5.793817")))
            time.sleep(6)
            self.assertFalse(list(rem.pgrep("5.793817")))

    def test_bound_env(self):
        with self._connect() as rem:
            printenv = rem["printenv"]
            with rem.env(FOO = "hello"):
                self.assertEqual(printenv.with_env(BAR = "world")("FOO", "BAR"), "hello\nworld\n")
                self.assertEqual(printenv.with_env(FOO = "sea", BAR = "world")("FOO", "BAR"), "sea\nworld\n")

    def test_sshpass(self):
        with local.as_root():
            local["useradd"]("-m", "-b", "/tmp", "testuser")

        try:
            with local.as_root():
                try:
                    (local["passwd"] << "123456")("--stdin", "testuser")
                except ProcessExecutionError:
                    # some versions of passwd don't support --stdin, nothing to do in this case
                    logging.warn("passwd failed")
                    return

            with SshMachine("localhost", user = "testuser", password = "123456") as rem:
                self.assertEqual(rem["pwd"]().strip(), "/tmp/testuser")
        finally:
            with local.as_root():
                local["userdel"]("-r", "testuser")



try:
    import paramiko
except ImportError:
    print("Paramiko not avilable")
else:
    from plumbum.machines.paramiko_machine import ParamikoMachine

    class TestParamikoMachine(unittest.TestCase, BaseRemoteMachineTest):
        def _connect(self):
            return ParamikoMachine(TEST_HOST, missing_host_policy = paramiko.AutoAddPolicy())
        
        def test_tunnel(self):
            with self._connect() as rem:
                p = rem.python["-c", self.TUNNEL_PROG].popen()
                try:
                    port = int(p.stdout.readline().strip())
                except ValueError:
                    print(p.communicate())
                    raise
                
                s = rem.connect_sock(port)
                s.send(six.b("world"))
                data = s.recv(100)
                s.close()
                self.assertEqual(data, six.b("hello world"))

        def test_piping(self):
            with self._connect() as rem:
                try:
                    cmd = rem["ls"] | rem["cat"]
                except NotImplementedError:
                    pass
                else:
                    assert False, "Should not pipe"


if __name__ == "__main__":
    unittest.main()




