import pytest
import sys
import os
import socket
import time
import logging
import plumbum
from copy import deepcopy
from plumbum import RemotePath, SshMachine, CommandNotFound, ProcessExecutionError, local, ProcessTimedOut, NOHUP
from plumbum import CommandNotFound
from plumbum.lib import six
from plumbum.machines.session import IncorrectLogin, HostPublicKeyUnknown
from plumbum._testtools import skip_without_chown, skip_on_windows

try:
    import paramiko
except ImportError:
    paramiko = None
else:
    from plumbum.machines.paramiko_machine import ParamikoMachine

def strassert(one, two):
    assert str(one) == str(two)

#TEST_HOST = "192.168.1.143"
TEST_HOST = "127.0.0.1"
if TEST_HOST not in ("::1", "127.0.0.1", "localhost"):
    plumbum.local.env.path.append("c:\\Program Files\\Git\\bin")


@pytest.fixture(scope='session')
def sshpass():
    try:
        return plumbum.local['sshpass']
    except CommandNotFound:
        pytest.skip('Test requires sshpass')


@skip_on_windows
def test_connection():
    SshMachine(TEST_HOST)


def test_incorrect_login(sshpass):
    def connect():
        SshMachine(TEST_HOST, password='swordfish',
                   ssh_opts=['-o', 'PubkeyAuthentication=no',
                             '-o', 'PreferredAuthentications=password'])
    pytest.raises(IncorrectLogin, connect)


def test_hostpubkey_unknown(sshpass):
    def connect():
        SshMachine(TEST_HOST, password='swordfish',
                   ssh_opts=['-o', 'UserKnownHostsFile=/dev/null',
                             '-o', 'UpdateHostKeys=no'])
    pytest.raises(HostPublicKeyUnknown, connect)


@skip_on_windows
class TestRemotePath:
    def _connect(self):
        return SshMachine(TEST_HOST)

    def test_name(self):
        name = RemotePath(self._connect(), "/some/long/path/to/file.txt").name
        assert isinstance(name, six.string_types)
        assert "file.txt" == str(name)

    def test_dirname(self):
        name = RemotePath(self._connect(), "/some/long/path/to/file.txt").dirname
        assert isinstance(name, RemotePath)
        assert "/some/long/path/to" == str(name)

    def test_uri(self):
        p1 = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        assert "ftp://" == p1.as_uri('ftp')[:6]
        assert "ssh://" == p1.as_uri('ssh')[:6]
        assert "/some/long/path/to/file.txt" == p1.as_uri()[-27:]

    def test_stem(self):
        p = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        assert p.stem == "file"
        p = RemotePath(self._connect(), "/some/long/path/")
        assert p.stem == "path"

    def test_suffix(self):
        p1 = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        p2 = RemotePath(self._connect(), "file.tar.gz")
        assert p1.suffix == ".txt"
        assert p1.suffixes == [".txt"]
        assert p2.suffix == ".gz"
        assert p2.suffixes == [".tar",".gz"]
        strassert(p1.with_suffix(".tar.gz"), RemotePath(self._connect(), "/some/long/path/to/file.tar.gz"))
        strassert(p2.with_suffix(".other"), RemotePath(self._connect(), "file.tar.other"))
        strassert(p2.with_suffix(".other", 2), RemotePath(self._connect(), "file.other"))
        strassert(p2.with_suffix(".other", 0), RemotePath(self._connect(), "file.tar.gz.other"))
        strassert(p2.with_suffix(".other", None), RemotePath(self._connect(), "file.other"))

    def test_newname(self):
        p1 = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        p2 = RemotePath(self._connect(), "file.tar.gz")
        strassert(p1.with_name("something.tar"), RemotePath(self._connect(), "/some/long/path/to/something.tar"))
        strassert(p2.with_name("something.tar"), RemotePath(self._connect(), "something.tar"))

    @skip_without_chown
    def test_chown(self):
        with self._connect() as rem:
            with rem.tempdir() as dir:
                p = dir / "foo.txt"
                p.write(six.b("hello"))
                # because we're connected to localhost, we expect UID and GID to be the same
                assert p.uid == os.getuid()
                assert p.gid == os.getgid()
                p.chown(p.uid.name)
                assert p.uid == os.getuid()

class BaseRemoteMachineTest(object):
    TUNNEL_PROG = r"""import sys, socket
s = socket.socket()
s.bind(("", 0))
s.listen(1)
sys.stdout.write("{0}\n".format( s.getsockname()[1]))
sys.stdout.flush()
s2, _ = s.accept()
data = s2.recv(100)
s2.send(b"hello " + data)
s2.close()
s.close()
"""

    def test_basic(self):
        with self._connect() as rem:
            r_ssh = rem["ssh"]
            r_ls = rem["ls"]
            r_grep = rem["grep"]

            lines = r_ls("-a").splitlines()
            assert ".bashrc" in lines or ".bash_profile" in lines
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                cmd = r_ssh["localhost", "cd", rem.cwd, "&&", r_ls, "|", r_grep["\\.py"]]
                assert "'|'" in str(cmd)
                assert "test_remote.py" in cmd()
                assert "test_remote.py" in [f.name for f in rem.cwd // "*.py"]

    # Testing for #271
    def test_double_chdir(self):
        with self._connect() as rem:
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                 rem["ls"]()
            with rem.cwd("/tmp"):
                 rem["pwd"]()

    def test_glob(self):
        with self._connect() as rem:
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                filenames = [f.name for f in rem.cwd // ("*.py", "*.bash")]
                assert "test_remote.py" in filenames
                assert "slow_process.bash" in filenames

    @pytest.mark.usefixtures("testdir")
    def test_download_upload(self):
        with self._connect() as rem:
            rem.upload("test_remote.py", "/tmp")
            r_ls = rem["ls"]
            r_rm = rem["rm"]
            assert "test_remote.py" in r_ls("/tmp").splitlines()
            rem.download("/tmp/test_remote.py", "/tmp/test_download.txt")
            r_rm("/tmp/test_remote.py")
            r_rm("/tmp/test_download.txt")

    def test_session(self):
        with self._connect() as rem:
            sh = rem.session()
            for _ in range(4):
                _, out, _ = sh.run("ls -a")
                assert ".bashrc" in out or ".bash_profile" in out

    def test_env(self):
        with self._connect() as rem:
            with pytest.raises(ProcessExecutionError):
              rem.python("-c", "import os;os.environ['FOOBAR72']")
            with rem.env(FOOBAR72 = "lala"):
                with rem.env(FOOBAR72 = "baba"):
                    out = rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
                    assert out.strip() == "baba"
                out = rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
                assert out.strip() == "lala"

            # path manipulation
            with pytest.raises(CommandNotFound):
                rem.which("dummy-executable")
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                rem.env.path.insert(0, rem.cwd / "not-in-path")
                p = rem.which("dummy-executable")
                assert p == rem.cwd / "not-in-path" / "dummy-executable"

    def test_read_write(self):
        with self._connect() as rem:
            with rem.tempdir() as dir:
                assert dir.is_dir()
                data = six.b("hello world")
                (dir / "foo.txt").write(data)
                assert (dir / "foo.txt").read() == data

            assert not dir.exists()

    def test_contains(self):
        with self._connect() as rem:
            assert "ls" in rem

    def test_iter_lines_timeout(self):
        with self._connect() as rem:
            try:
                for i, (out, err) in enumerate(rem["ping"]["-i", 0.5, "127.0.0.1"].popen().iter_lines(timeout=4)):
                    print("out:", out)
                    print("err:", err)
            except NotImplementedError:
                try:
                    pytest.skip(sys.exc_info()[1])
                except AttributeError:
                    return
            except ProcessTimedOut:
                assert i > 3
            else:
                pytest.fail("Expected a timeout")


    def test_iter_lines_error(self):
        with self._connect() as rem:
            with pytest.raises(ProcessExecutionError) as ex:
                for i, lines in enumerate(rem["ls"]["--bla"].popen()):
                    pass
                assert i == 1
            assert ex.value.stderr.startswith("/bin/ls: ")

    def test_touch(self):
        with self._connect() as rem:
            rfile = rem.cwd / 'sillyfile'
            assert not rfile.exists()
            rfile.touch()
            assert rfile.exists()
            rfile.delete()

@skip_on_windows
class TestRemoteMachine(BaseRemoteMachineTest):
    def _connect(self):
        return SshMachine(TEST_HOST)

    def test_tunnel(self):
        with self._connect() as rem:
            p = (rem.python["-u"] << self.TUNNEL_PROG).popen()
            try:
                port = int(p.stdout.readline().decode("ascii").strip())
            except ValueError:
                print(p.communicate())
                raise

            with rem.tunnel(12222, port) as tun:
                s = socket.socket()
                s.connect(("localhost", 12222))
                s.send(six.b("world"))
                data = s.recv(100)
                s.close()

            print(p.communicate())
            assert data == b"hello world"

    def test_get(self):
        with self._connect() as rem:
            assert str(rem['ls']) == str(rem.get('ls'))
            assert str(rem['ls']) == str(rem.get('not_a_valid_process_234','ls'))
            assert 'ls' in rem
            assert 'not_a_valid_process_234' not in rem

    def test_list_processes(self):
        with self._connect() as rem:
            assert list(rem.list_processes())

    def test_pgrep(self):
        with self._connect() as rem:
            assert list(rem.pgrep("ssh"))

    @pytest.mark.xfail(reason="Randomly does not work on Travis, not sure why")
    def test_nohup(self):
        with self._connect() as rem:
            sleep = rem["sleep"]
            sleep["5.793817"] & NOHUP(stdout = None, append=False)
            time.sleep(.5)
            print(rem["ps"]("aux"))
            assert list(rem.pgrep("5.793817"))
            time.sleep(6)
            assert not list(rem.pgrep("5.793817"))

    def test_bound_env(self):
        with self._connect() as rem:
            printenv = rem["printenv"]
            with rem.env(FOO = "hello"):
                assert printenv.with_env(BAR = "world")("FOO") == "hello\n"
                assert printenv.with_env(BAR = "world")("BAR") == "world\n"
                assert printenv.with_env(FOO = "sea", BAR = "world")("FOO") == "sea\n"
                assert printenv.with_env(FOO = "sea", BAR = "world")("BAR") == "world\n"

    @pytest.mark.skipif('useradd' not in local,
            reason = "System does not have useradd (Mac?)")
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
                assert rem["pwd"]().strip() == "/tmp/testuser"
        finally:
            with local.as_root():
                local["userdel"]("-r", "testuser")

@skip_on_windows
class TestParamikoMachine(BaseRemoteMachineTest):
    def _connect(self):
        if paramiko is None:
            pytest.skip("System does not have paramiko installed")
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
            s.send(b"world")
            data = s.recv(100)
            s.close()

        print(p.communicate())
        assert data == b"hello world"

    def test_piping(self):
        with self._connect() as rem:
            try:
                cmd = rem["ls"] | rem["cat"]
            except NotImplementedError:
                pass
            else:
                pytest.fail("Should not pipe")

    def test_encoding(self):
        with self._connect() as rem:
            unicode_half = b"\xc2\xbd".decode("utf8")

            ret = rem['bash']("-c", 'echo -e "\xC2\xBD"')
            assert ret == "%s\n" % unicode_half

            ret = list(rem['bash']["-c", 'echo -e "\xC2\xBD"'].popen())
            assert ret == [["%s\n" % unicode_half, None]]
