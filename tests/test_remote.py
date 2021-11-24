# -*- coding: utf-8 -*-
import logging
import os
import socket
import sys
import time
from copy import deepcopy
from multiprocessing import Queue
from threading import Thread

import env
import pytest

import plumbum
from plumbum import (
    NOHUP,
    CommandNotFound,
    ProcessExecutionError,
    ProcessTimedOut,
    RemotePath,
    SshMachine,
    local,
)
from plumbum._testtools import skip_on_windows, skip_without_chown
from plumbum.lib import six
from plumbum.machines.session import HostPublicKeyUnknown, IncorrectLogin

try:
    import paramiko
except ImportError:
    paramiko = None
else:
    from plumbum.machines.paramiko_machine import ParamikoMachine


pytestmark = pytest.mark.ssh


def strassert(one, two):
    assert str(one) == str(two)


# TEST_HOST = "192.168.1.143"
TEST_HOST = "127.0.0.1"
if TEST_HOST not in ("::1", "127.0.0.1", "localhost"):
    plumbum.local.env.path.append("c:\\Program Files\\Git\\bin")


@pytest.fixture(scope="session")
def sshpass():
    try:
        return plumbum.local["sshpass"]
    except CommandNotFound:
        pytest.skip("Test requires sshpass")


@skip_on_windows
def test_connection():
    SshMachine(TEST_HOST)


@pytest.mark.skip(
    env.LINUX and env.PY[:2] == (3, 5), reason="Doesn't work on 3.5 on Linux on GHA"
)
def test_incorrect_login(sshpass):
    with pytest.raises(IncorrectLogin):
        SshMachine(
            TEST_HOST,
            password="swordfish",
            ssh_opts=[
                "-o",
                "PubkeyAuthentication=no",
                "-o",
                "PreferredAuthentications=password",
            ],
        )


@pytest.mark.xfail(env.LINUX, reason="TODO: no idea why this fails on linux")
def test_hostpubkey_unknown(sshpass):
    with pytest.raises(HostPublicKeyUnknown):
        SshMachine(
            TEST_HOST,
            password="swordfish",
            ssh_opts=["-o", "UserKnownHostsFile=/dev/null", "-o", "UpdateHostKeys=no"],
        )


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
        assert "ftp://" == p1.as_uri("ftp")[:6]
        assert "ssh://" == p1.as_uri("ssh")[:6]
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
        assert p2.suffixes == [".tar", ".gz"]
        strassert(
            p1.with_suffix(".tar.gz"),
            RemotePath(self._connect(), "/some/long/path/to/file.tar.gz"),
        )
        strassert(
            p2.with_suffix(".other"), RemotePath(self._connect(), "file.tar.other")
        )
        strassert(
            p2.with_suffix(".other", 2), RemotePath(self._connect(), "file.other")
        )
        strassert(
            p2.with_suffix(".other", 0),
            RemotePath(self._connect(), "file.tar.gz.other"),
        )
        strassert(
            p2.with_suffix(".other", None), RemotePath(self._connect(), "file.other")
        )

    def test_newname(self):
        p1 = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        p2 = RemotePath(self._connect(), "file.tar.gz")
        strassert(
            p1.with_name("something.tar"),
            RemotePath(self._connect(), "/some/long/path/to/something.tar"),
        )
        strassert(
            p2.with_name("something.tar"), RemotePath(self._connect(), "something.tar")
        )

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

    def test_parent(self):
        p1 = RemotePath(self._connect(), "/some/long/path/to/file.txt")
        p2 = p1.parent
        assert str(p2) == "/some/long/path/to"

    def test_mkdir(self):
        # (identical to test_local.TestLocalPath.test_mkdir)
        with self._connect() as rem:
            with rem.tempdir() as tmp:
                (tmp / "a").mkdir(exist_ok=False, parents=False)
                assert (tmp / "a").exists()
                assert (tmp / "a").is_dir()
                (tmp / "a").mkdir(exist_ok=True, parents=False)
                (tmp / "a").mkdir(exist_ok=True, parents=True)
                with pytest.raises(OSError):
                    (tmp / "a").mkdir(exist_ok=False, parents=False)
                with pytest.raises(OSError):
                    (tmp / "a").mkdir(exist_ok=False, parents=True)
                (tmp / "b" / "bb").mkdir(exist_ok=False, parents=True)
                assert (tmp / "b" / "bb").exists()
                assert (tmp / "b" / "bb").is_dir()
            assert not tmp.exists()

    @pytest.mark.xfail(
        reason="mkdir's mode argument is not yet implemented " "for remote paths",
        strict=True,
    )
    def test_mkdir_mode(self):
        # (identical to test_local.TestLocalPath.test_mkdir_mode)
        with self._connect() as rem:
            with rem.tempdir() as tmp:
                # just verify that mode argument works the same way it does for
                # Python's own os.mkdir, which takes into account the umask
                # (different from shell mkdir mode argument!); umask on my
                # system is 022 by default, so 033 is ok for testing this
                try:
                    (tmp / "pb_333").mkdir(exist_ok=False, parents=False, mode=0o333)
                    rem.python(
                        "-c",
                        "import os; os.mkdir({}, 0o333)".format(
                            repr(str(tmp / "py_333"))
                        ),
                    )
                    pb_final_mode = oct((tmp / "pb_333").stat().st_mode)
                    py_final_mode = oct((tmp / "py_333").stat().st_mode)
                    assert pb_final_mode == py_final_mode
                finally:
                    # we have to revert this so the tempdir deletion works
                    if (tmp / "pb_333").exists():
                        (tmp / "pb_333").chmod(0o777)
                    if (tmp / "py_333").exists():
                        (tmp / "py_333").chmod(0o777)
            assert not tmp.exists()

    def test_copy(self):
        """
        tests `RemotePath.copy` for the following scenarios:

            * copying a simple file from `file_a` to `copy_of_a` succeeds

            * copying file `file_a` into a directory `a_dir/copy_of_a` succeeds

            * copying a directory `a_dir` over an existing directory path with
              `override=False` fails

            * copying a directory `a_dir` over an existing directory path with
              `override=True` succeeds
        """

        with self._connect() as rem:
            with rem.tempdir() as tmp:

                # setup a file and make sure it exists...
                (tmp / "file_a").touch()
                assert (tmp / "file_a").exists()
                assert (tmp / "file_a").is_file()

                # setup a directory for copying into...
                (tmp / "a_dir").mkdir(exist_ok=False, parents=False)
                assert (tmp / "a_dir").exists()
                assert (tmp / "a_dir").is_dir()

                # setup a 2nd directory for testing `override=False`
                (tmp / "b_dir").mkdir(exist_ok=False, parents=False)
                assert (tmp / "b_dir").exists()
                assert (tmp / "b_dir").is_dir()

                # copying a simple file
                (tmp / "file_a").copy(tmp / "copy_of_a")
                assert (tmp / "copy_of_a").exists()
                assert (tmp / "copy_of_a").is_file()

                # copying into a directory
                (tmp / "file_a").copy(tmp / "a_dir/copy_of_a")
                assert (tmp / "a_dir/copy_of_a").exists()
                assert (tmp / "a_dir/copy_of_a").is_file()

                # copying a directory on top of an existing directory using
                # `override=False` (should fail with TypeError)
                with pytest.raises(TypeError):
                    (tmp / "a_dir").copy(tmp / "b_dir", override=False)

                # copying a directory on top of an existing directory using
                # `override=True` (should copy transparently)
                (tmp / "a_dir").copy(tmp / "b_dir", override=True)
                assert "copy_of_a" in (tmp / "b_dir")

            assert not tmp.exists()


class BaseRemoteMachineTest(object):
    TUNNEL_PROG_AF_INET = r"""import sys, socket
s = socket.socket()
s.bind(("", 0))
s.listen(1)
sys.stdout.write("{0}\n".format(s.getsockname()[1]))
sys.stdout.flush()
s2, _ = s.accept()
data = s2.recv(100)
s2.send(b"hello " + data)
s2.close()
s.close()
"""

    TUNNEL_PROG_AF_UNIX = r"""import sys, socket, tempfile
s = socket.socket(family=socket.AF_UNIX)
socket_location = tempfile.NamedTemporaryFile()
socket_location.close()
s.bind(socket_location.name)
s.listen(1)
sys.stdout.write("{0}\n".format(s.getsockname()))
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
                cmd = r_ssh[
                    "localhost", "cd", rem.cwd, "&&", r_ls, "|", r_grep["\\.py"]
                ]
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

    def test_glob_spaces(self):
        with self._connect() as rem:
            with rem.cwd(os.path.dirname(os.path.abspath(__file__))):
                filenames = [f.name for f in rem.cwd // ("*space.txt")]
                assert "file with space.txt" in filenames

                filenames = [f.name for f in rem.cwd // ("*with space.txt")]
                assert "file with space.txt" in filenames

    def test_cmd(self):
        with self._connect() as rem:
            rem.cmd.ls("/tmp")

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
            with rem.env(FOOBAR72="lala"):
                with rem.env(FOOBAR72="baba"):
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

    @pytest.mark.xfail(env.PYPY, reason="PyPy sometimes fails here", strict=False)
    @pytest.mark.parametrize(
        "env",
        [
            "lala",
            "-Wl,-O2 -Wl,--sort-common",
            "{{}}",
            "''",
            "!@%_-+=:",
            "'",
            "`",
            "$",
            "\\",
        ],
    )
    def test_env_special_characters(self, env):
        with self._connect() as rem:
            with pytest.raises(ProcessExecutionError):
                rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
            rem.env["FOOBAR72"] = env
            out = rem.python("-c", "import os;print(os.environ['FOOBAR72'])")
            assert out.strip() == env

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
                for i, (out, err) in enumerate(
                    rem["ping"]["-i", 0.5, "127.0.0.1"].popen().iter_lines(timeout=4)
                ):
                    print("out:", out)
                    print("err:", err)
            except NotImplementedError:
                try:
                    pytest.skip(str(sys.exc_info()[1]))
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
            assert "/bin/ls: " in ex.value.stderr

    def test_touch(self):
        with self._connect() as rem:
            rfile = rem.cwd / "sillyfile"
            assert not rfile.exists()
            rfile.touch()
            assert rfile.exists()
            rfile.delete()


def serve_reverse_tunnel(queue):
    s = socket.socket()
    s.bind(("", 12223))
    s.listen(1)
    s2, _ = s.accept()
    data = s2.recv(100).decode("ascii").strip()
    queue.put(data)
    s2.close()
    s.close()


@skip_on_windows
class TestRemoteMachine(BaseRemoteMachineTest):
    def _connect(self):
        return SshMachine(TEST_HOST)

    def test_tunnel(self):

        for tunnel_prog in (self.TUNNEL_PROG_AF_INET, self.TUNNEL_PROG_AF_UNIX):
            with self._connect() as rem:
                p = (rem.python["-u"] << tunnel_prog).popen()
                port_or_socket = p.stdout.readline().decode("ascii").strip()
                try:
                    port_or_socket = int(port_or_socket)
                    dhost = "localhost"
                except ValueError:
                    dhost = None

                with rem.tunnel(12222, port_or_socket, dhost=dhost) as tun:
                    s = socket.socket()
                    s.connect(("localhost", 12222))
                    s.send(six.b("world"))
                    data = s.recv(100)
                    s.close()

                print(p.communicate())
                assert data == b"hello world"

    def test_reverse_tunnel(self):

        with self._connect() as rem:
            get_unbound_socket_remote = """import sys, socket
s = socket.socket()
s.bind(("", 0))
s.listen(1)
sys.stdout.write(str(s.getsockname()[1]))
sys.stdout.flush()
s.close()
"""
            p = (rem.python["-u"] << get_unbound_socket_remote).popen()
            remote_socket = p.stdout.readline().decode("ascii").strip()
            queue = Queue()
            tunnel_server = Thread(target=serve_reverse_tunnel, args=(queue,))
            tunnel_server.start()
            message = str(time.time())
            with rem.tunnel(12223, remote_socket, dhost="localhost", reverse=True):
                remote_send_af_inet = """import socket
s = socket.socket()
s.connect(("localhost", {}))
s.send("{}".encode("ascii"))
s.close()
""".format(
                    remote_socket, message
                )
                (rem.python["-u"] << remote_send_af_inet).popen()
                tunnel_server.join(timeout=1)
                assert queue.get() == message

    def test_get(self):
        with self._connect() as rem:
            assert str(rem["ls"]) == str(rem.get("ls"))
            assert str(rem["ls"]) == str(rem.get("not_a_valid_process_234", "ls"))
            assert "ls" in rem
            assert "not_a_valid_process_234" not in rem

    def test_list_processes(self):
        with self._connect() as rem:
            assert list(rem.list_processes())

    def test_pgrep(self):
        with self._connect() as rem:
            assert list(rem.pgrep("ssh"))

    def test_nohup(self):
        with self._connect() as rem:
            sleep = rem["sleep"]
            sleep["5.793817"] & NOHUP(stdout=None, append=False)
            time.sleep(0.5)
            print(rem["ps"]("aux"))
            assert list(rem.pgrep("5.793817"))
            time.sleep(6)
            assert not list(rem.pgrep("5.793817"))

    def test_bound_env(self):
        with self._connect() as rem:
            printenv = rem["printenv"]
            with rem.env(FOO="hello"):
                assert printenv.with_env(BAR="world")("FOO") == "hello\n"
                assert printenv.with_env(BAR="world")("BAR") == "world\n"
                assert printenv.with_env(FOO="sea", BAR="world")("FOO") == "sea\n"
                assert printenv.with_env(FOO="sea", BAR="world")("BAR") == "world\n"

            assert rem.cmd.pwd.with_cwd("/")() == "/\n"
            assert rem.cmd.pwd["-L"].with_env(A="X").with_cwd("/")() == "/\n"

    @pytest.mark.skipif(
        "useradd" not in local, reason="System does not have useradd (Mac?)"
    )
    def test_sshpass(self):
        with local.as_root():
            local["useradd"]("-m", "-b", "/tmp", "testuser")

        try:
            with local.as_root():
                try:
                    (local["passwd"] << "123456")("--stdin", "testuser")
                except ProcessExecutionError:
                    # some versions of passwd don't support --stdin, nothing to do in this case
                    logging.warning("passwd failed")
                    return

            with SshMachine("localhost", user="testuser", password="123456") as rem:
                assert rem["pwd"]().strip() == "/tmp/testuser"
        finally:
            with local.as_root():
                local["userdel"]("-r", "testuser")


@skip_on_windows
class TestParamikoMachine(BaseRemoteMachineTest):
    def _connect(self):
        if paramiko is None:
            pytest.skip("System does not have paramiko installed")
        return ParamikoMachine(TEST_HOST, missing_host_policy=paramiko.AutoAddPolicy())

    def test_tunnel(self):
        with self._connect() as rem:
            p = rem.python["-c", self.TUNNEL_PROG_AF_INET].popen()
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

    @pytest.mark.xfail(message="Not working yet")
    def test_encoding(self):
        with self._connect() as rem:
            unicode_half = b"\xc2\xbd".decode("utf8")

            ret = rem["bash"]("-c", 'echo -e "\xC2\xBD"')
            assert ret == "%s\n" % unicode_half

            ret = list(rem["bash"]["-c", 'echo -e "\xC2\xBD"'].popen())
            assert ret == [["%s\n" % unicode_half, None]]

    def test_path_open_remote_write_local_read(self):
        with self._connect() as rem:
            # TODO: once Python 2.6 support is dropped, the nested
            # with-statements below can be combined using "with x as a, y as b"
            with rem.tempdir() as remote_tmpdir:
                with local.tempdir() as tmpdir:
                    assert remote_tmpdir.is_dir()
                    assert tmpdir.is_dir()
                    data = six.b("hello world")
                    with (remote_tmpdir / "bar.txt").open("wb") as f:
                        f.write(data)
                    rem.download((remote_tmpdir / "bar.txt"), (tmpdir / "bar.txt"))
                    assert (tmpdir / "bar.txt").open("rb").read() == data

            assert not remote_tmpdir.exists()
            assert not tmpdir.exists()

    def test_path_open_local_write_remote_read(self):
        with self._connect() as rem:
            # TODO: cf. note on Python 2.6 support above
            with rem.tempdir() as remote_tmpdir:
                with local.tempdir() as tmpdir:
                    assert remote_tmpdir.is_dir()
                    assert tmpdir.is_dir()
                    data = six.b("hello world")
                    with (tmpdir / "bar.txt").open("wb") as f:
                        f.write(data)
                    rem.upload((tmpdir / "bar.txt"), (remote_tmpdir / "bar.txt"))
                    assert (remote_tmpdir / "bar.txt").open("rb").read() == data

            assert not remote_tmpdir.exists()
            assert not tmpdir.exists()
