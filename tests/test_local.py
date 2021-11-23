# -*- coding: utf-8 -*-
import os
import pickle
import signal
import sys
import time

import pytest

import plumbum
from plumbum import (
    BG,
    ERROUT,
    FG,
    RETCODE,
    TEE,
    TF,
    CommandNotFound,
    LocalPath,
    ProcessExecutionError,
    ProcessLineTimedOut,
    ProcessTimedOut,
    local,
)
from plumbum._testtools import (
    skip_on_windows,
    skip_without_chown,
    skip_without_tty,
    xfail_on_pypy,
)
from plumbum.fs.atomic import AtomicCounterFile, AtomicFile, PidFile
from plumbum.lib import IS_WIN32, six
from plumbum.machines.local import LocalCommand, PlumbumLocalPopen
from plumbum.path import RelativePath

# This is a string since we are testing local paths
SDIR = os.path.dirname(os.path.abspath(__file__))


class TestLocalPopen:
    @pytest.mark.skipif(
        sys.version_info < (3, 2), reason="Context Manager was introduced in Python 3.2"
    )
    def test_contextmanager(self):
        if IS_WIN32:
            command = ["dir"]
        else:
            command = ["ls"]
        with PlumbumLocalPopen(command):
            pass


class TestLocalPath:
    longpath = local.path("/some/long/path/to/file.txt")

    def test_name(self):
        name = self.longpath.name
        assert isinstance(name, six.string_types)
        assert "file.txt" == str(name)

    def test_dirname(self):
        name = self.longpath.dirname
        assert isinstance(name, LocalPath)
        assert "/some/long/path/to" == str(name).replace("\\", "/").lstrip("C:").lstrip(
            "D:"
        )

    def test_uri(self):
        if IS_WIN32:
            pth = self.longpath.as_uri()
            assert pth.startswith("file:///")
            assert pth.endswith(":/some/long/path/to/file.txt")
        else:
            assert "file:///some/long/path/to/file.txt" == self.longpath.as_uri()

    def test_pickle(self):
        path1 = local.path(".")
        path2 = local.path("~")
        assert pickle.loads(pickle.dumps(self.longpath)) == self.longpath
        assert pickle.loads(pickle.dumps(path1)) == path1
        assert pickle.loads(pickle.dumps(path2)) == path2

    def test_empty(self):
        with pytest.raises(TypeError):
            LocalPath()
        assert local.path() == local.path(".")

    @skip_without_chown
    def test_chown(self):
        with local.tempdir() as dir:
            p = dir / "foo.txt"
            p.write(six.b("hello"))
            assert p.uid == os.getuid()
            assert p.gid == os.getgid()
            p.chown(p.uid.name)
            assert p.uid == os.getuid()

    def test_split(self):
        p = local.path("/var/log/messages")
        p.split() == ["var", "log", "messages"]

    @pytest.mark.xfail(
        sys.platform == "win32" and (sys.version_info[0] == 2),
        reason="Caseless comparison (at least in pytest) fails on Windows 2.7",
    )
    def test_suffix(self):
        # This picks up the drive letter differently if not constructed here
        p1 = local.path("/some/long/path/to/file.txt")
        p2 = local.path("file.tar.gz")
        assert p1.suffix == ".txt"
        assert p1.suffixes == [".txt"]
        assert p2.suffix == ".gz"
        assert p2.suffixes == [".tar", ".gz"]
        assert p1.with_suffix(".tar.gz") == local.path("/some/long/path/to/file.tar.gz")
        assert p2.with_suffix(".other") == local.path("file.tar.other")
        assert p2.with_suffix(".other", 2) == local.path("file.other")
        assert p2.with_suffix(".other", 0) == local.path("file.tar.gz.other")
        assert p2.with_suffix(".other", None) == local.path("file.other")

        with pytest.raises(ValueError):
            p1.with_suffix("nodot")

    @pytest.mark.xfail(
        sys.platform == "win32" and (sys.version_info[0] == 2),
        reason="Caseless comparison (at least in pytest) fails on Windows 2.7",
    )
    def test_newname(self):
        # This picks up the drive letter differently if not constructed here
        p1 = local.path("/some/long/path/to/file.txt")
        p2 = local.path("file.tar.gz")
        assert p1.with_name("something.tar") == local.path(
            "/some/long/path/to/something.tar"
        )
        assert p2.with_name("something.tar") == local.path("something.tar")

    def test_relative_to(self):
        p = local.path("/var/log/messages")
        assert p.relative_to("/var/log/messages") == RelativePath([])
        assert p.relative_to("/var/") == RelativePath(["log", "messages"])
        assert p.relative_to("/") == RelativePath(["var", "log", "messages"])
        assert p.relative_to("/var/tmp") == RelativePath(["..", "log", "messages"])
        assert p.relative_to("/opt") == RelativePath(["..", "var", "log", "messages"])
        assert p.relative_to("/opt/lib") == RelativePath(
            ["..", "..", "var", "log", "messages"]
        )
        for src in [
            local.path("/var/log/messages"),
            local.path("/var"),
            local.path("/opt/lib"),
        ]:
            delta = p.relative_to(src)
            assert src + delta == p

    def test_read_write(self):
        with local.tempdir() as dir:
            f = dir / "test.txt"
            text = six.b("hello world\xd7\xa9\xd7\x9c\xd7\x95\xd7\x9d").decode("utf8")
            f.write(text, "utf8")
            text2 = f.read("utf8")
            assert text == text2

    def test_parts(self):
        parts = self.longpath.parts
        if IS_WIN32:
            assert parts[1:] == ("some", "long", "path", "to", "file.txt")
            assert ":" in parts[0]
        else:
            assert parts == ("/", "some", "long", "path", "to", "file.txt")

    @pytest.mark.usefixtures("testdir")
    def test_iterdir(self):
        cwd = local.path(".")
        files = list(cwd.iterdir())
        assert cwd / "test_local.py" in files
        assert cwd / "test_remote.py" in files
        assert cwd["test_local.py"] in files
        assert cwd["test_remote.py"] in files

    def test_stem(self):
        assert self.longpath.stem == "file"
        p = local.path("/some/directory")
        assert p.stem == "directory"

    def test_root_drive(self):
        pathlib = pytest.importorskip("pathlib")
        pl_path = pathlib.Path("/some/long/path/to/file.txt").absolute()
        assert self.longpath.root == pl_path.root
        assert self.longpath.drive == pl_path.drive

        p_path = local.cwd / "somefile.txt"
        pl_path = pathlib.Path("somefile.txt").absolute()
        assert p_path.root == pl_path.root
        assert p_path.drive == pl_path.drive

    def test_compare_pathlib(self):
        pathlib = pytest.importorskip("pathlib")

        def filename_compare(name):
            p = local.path(str(name))
            pl = pathlib.Path(str(name)).absolute()
            assert str(p) == str(pl)
            assert p.parts == pl.parts
            assert p.exists() == pl.exists()
            assert p.is_symlink() == pl.is_symlink()
            assert p.as_uri() == pl.as_uri()
            assert str(p.with_suffix(".this")) == str(pl.with_suffix(".this"))
            assert p.name == pl.name
            assert str(p.parent) == str(pl.parent)
            assert list(map(str, p.parents)) == list(map(str, pl.parents))

        filename_compare("/some/long/path/to/file.txt")
        filename_compare(local.cwd / "somefile.txt")
        filename_compare("/some/long/path/")
        filename_compare("/some/long/path")
        filename_compare(__file__)

    def test_suffix_expected(self):
        assert self.longpath.preferred_suffix(".tar") == self.longpath
        assert (local.cwd / "this").preferred_suffix(".txt") == local.cwd / "this.txt"

    def test_touch(self):
        with local.tempdir() as tmp:
            one = tmp / "one"
            assert not one.is_file()
            one.touch()
            assert one.is_file()
            one.delete()
            assert not one.is_file()

    def test_copy_override(self):
        """Edit this when override behavior is added"""
        with local.tempdir() as tmp:
            one = tmp / "one"
            one.touch()
            two = tmp / "two"
            assert one.is_file()
            assert not two.is_file()
            one.copy(two)
            assert one.is_file()
            assert two.is_file()

    def test_copy_nonexistant_dir(self):
        with local.tempdir() as tmp:
            one = tmp / "one"
            one.write(b"lala")
            two = tmp / "two" / "one"
            three = tmp / "three" / "two" / "one"

            one.copy(two)
            assert one.read() == two.read()
            one.copy(three)
            assert one.read() == three.read()

    def test_unlink(self):
        with local.tempdir() as tmp:
            one = tmp / "one"
            one.touch()
            assert one.exists()
            one.unlink()
            assert not one.exists()

    def test_unhashable(self):
        with pytest.raises(TypeError):
            hash(local.cwd)

    def test_getpath(self):
        assert local.cwd.getpath() == local.path(".")

    def test_path_dir(self):
        assert local.path(__file__).dirname == SDIR

    def test_mkdir(self):
        # (identical to test_remote.TestRemotePath.test_mkdir)
        with local.tempdir() as tmp:
            tmp["a"].mkdir(exist_ok=False, parents=False)
            assert tmp["a"].exists()
            assert tmp["a"].is_dir()
            tmp["a"].mkdir(exist_ok=True, parents=False)
            tmp["a"].mkdir(exist_ok=True, parents=True)
            with pytest.raises(OSError):
                tmp["a"].mkdir(exist_ok=False, parents=False)
            with pytest.raises(OSError):
                tmp["a"].mkdir(exist_ok=False, parents=True)
            tmp["b"]["bb"].mkdir(exist_ok=False, parents=True)
            assert tmp["b"]["bb"].exists()
            assert tmp["b"]["bb"].is_dir()
        assert not tmp.exists()

    def test_mkdir_mode(self):
        # (identical to test_remote.TestRemotePath.test_mkdir_mode)
        with local.tempdir() as tmp:
            # just verify that mode argument works the same way it does for
            # Python's own os.mkdir, which takes into account the umask
            # (different from shell mkdir mode argument!); umask on my
            # system is 022 by default, so 033 is ok for testing this
            try:
                (tmp / "pb_333").mkdir(exist_ok=False, parents=False, mode=0o333)
                local.python(
                    "-c",
                    "import os; os.mkdir({}, 0o333)".format(repr(str(tmp / "py_333"))),
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

    def test_str_getitem(self):
        with local.tempdir() as tmp:
            assert str(tmp) == str(tmp[:])
            assert str(tmp)[0] == str(tmp[0])

    def test_fspath(self):
        with local.tempdir() as tmp:
            assert tmp.__fspath__() == str(tmp)


@pytest.mark.usefixtures("testdir")
class TestLocalMachine:
    def test_getattr(self):
        pb = plumbum
        assert getattr(pb.cmd, "does_not_exist", 1) == 1
        ls_cmd1 = pb.cmd.non_exist1N9 if hasattr(pb.cmd, "non_exist1N9") else pb.cmd.ls
        ls_cmd2 = getattr(pb.cmd, "non_exist1N9", pb.cmd.ls)
        assert str(ls_cmd1) == str(local["ls"])
        assert str(ls_cmd2) == str(local["ls"])

    # TODO: This probably fails because of odd ls behavior
    @skip_on_windows
    def test_imports(self):
        from plumbum.cmd import ls

        assert "test_local.py" in local["ls"]().splitlines()
        assert "test_local.py" in ls().splitlines()

        with pytest.raises(CommandNotFound):
            local["non_exist1N9"]()

        with pytest.raises(ImportError):
            from plumbum.cmd import non_exist1N9  # @UnresolvedImport @UnusedImport

    def test_get(self):
        assert str(local["ls"]) == str(local.get("ls"))
        assert str(local["ls"]) == str(local.get("non_exist1N9", "ls"))

        with pytest.raises(CommandNotFound):
            local.get("non_exist1N9")
        with pytest.raises(CommandNotFound):
            local.get("non_exist1N9", "non_exist1N8")
        with pytest.raises(CommandNotFound):
            local.get("non_exist1N9", "/tmp/non_exist1N8")

    def test_shadowed_by_dir(self):
        real_ls = local["ls"]
        with local.tempdir() as tdir:
            with local.cwd(tdir):
                ls_dir = tdir / "ls"
                ls_dir.mkdir()
                fake_ls = local["ls"]
                assert fake_ls.executable == real_ls.executable

                local.env.path.insert(0, tdir)
                fake_ls = local["ls"]
                del local.env.path[0]
                assert fake_ls.executable == real_ls.executable

    def test_repr_command(self):
        assert "BG" in repr(BG)
        assert "FG" in repr(FG)

    @skip_on_windows
    def test_cwd(self):
        from plumbum.cmd import ls

        assert local.cwd == os.getcwd()
        assert "machines" not in ls().splitlines()

        with local.cwd("../plumbum"):
            assert "machines" in ls().splitlines()
        assert "machines" not in ls().splitlines()

        assert "machines" in ls.with_cwd("../plumbum")().splitlines()
        path = local.cmd.pwd.with_cwd("../plumbum")().strip()
        with local.cwd("/"):
            assert "machines" not in ls().splitlines()
            assert "machines" in ls.with_cwd(path)().splitlines()

        with pytest.raises(OSError):
            local.cwd.chdir("../non_exist1N9")

    @skip_on_windows
    def test_mixing_chdir(self):
        assert local.cwd == os.getcwd()
        os.chdir("../plumbum")
        assert local.cwd == os.getcwd()
        os.chdir("../tests")
        assert local.cwd == os.getcwd()

    def test_contains(self):
        assert "plumbum" in local.cwd / ".."
        assert "non_exist1N91" not in local.cwd / ".."

    @skip_on_windows
    def test_path(self):
        assert not (local.cwd / "../non_exist1N9").exists()
        assert (local.cwd / ".." / "plumbum").is_dir()
        # traversal
        found = False
        for fn in local.cwd / ".." / "plumbum":
            if fn.name == "__init__.py":
                assert fn.is_file()
                found = True
        assert found
        # glob'ing
        found = False
        for fn in local.cwd / ".." // "*/*.rst":
            if fn.name == "index.rst":
                found = True
        assert found
        for fn in local.cwd / ".." // ("*/*.rst", "*./*.html"):
            if fn.name == "index.rst":
                found = True
        assert found

    @skip_on_windows
    def test_glob_spaces(self):
        fileloc = local.cwd / "file with space.txt"
        assert fileloc.exists()

        assert local.cwd // "*space.txt"
        assert local.cwd // "file with*"

    @skip_on_windows
    def test_env(self):
        assert "PATH" in local.env
        assert "FOOBAR72" not in local.env
        with pytest.raises(ProcessExecutionError):
            local.python("-c", "import os;os.environ['FOOBAR72']")
        local.env["FOOBAR72"] = "spAm"
        assert local.python(
            "-c", "import os;print (os.environ['FOOBAR72'])"
        ).splitlines() == ["spAm"]

        with local.env(FOOBAR73=1889):
            assert local.python(
                "-c", "import os;print (os.environ['FOOBAR73'])"
            ).splitlines() == ["1889"]
            with local.env(FOOBAR73=1778):
                assert local.python(
                    "-c", "import os;print (os.environ['FOOBAR73'])"
                ).splitlines() == ["1778"]
            assert local.python(
                "-c", "import os;print (os.environ['FOOBAR73'])"
            ).splitlines() == ["1889"]
        with pytest.raises(ProcessExecutionError):
            local.python("-c", "import os;os.environ['FOOBAR73']")

        # path manipulation
        with pytest.raises(CommandNotFound):
            local.which("dummy-executable")
        with local.env():
            local.env.path.insert(0, local.cwd / "not-in-path")
            p = local.which("dummy-executable")
            assert p == local.cwd / "not-in-path" / "dummy-executable"

    def test_local(self):
        from plumbum.cmd import cat, head

        assert "plumbum" in str(local.cwd)
        assert "PATH" in local.env.getdict()
        assert local.path("foo") == os.path.join(os.getcwd(), "foo")
        local.which("ls")
        local["ls"]
        assert local.python("-c", "print ('hi there')").splitlines() == ["hi there"]

    @skip_on_windows
    def test_piping(self):
        from plumbum.cmd import grep, ls

        chain = ls | grep["\\.py"]
        assert "test_local.py" in chain().splitlines()

        chain = ls["-a"] | grep["test"] | grep["local"]
        assert "test_local.py" in chain().splitlines()

    @skip_on_windows
    def test_redirection(self):
        from plumbum.cmd import cat, grep, ls, rm

        chain = (ls | grep["\\.py"]) > "tmp.txt"
        chain()

        chain2 = (cat < "tmp.txt") | grep["local"]
        assert "test_local.py" in chain2().splitlines()
        rm("tmp.txt")

        chain3 = (
            cat << "this is the\nworld of helloness and\nspam bar and eggs"
        ) | grep["hello"]
        assert "world of helloness and" in chain3().splitlines()

        rc, _, err = (grep["-Zq5"] >= "tmp2.txt").run(["-Zq5"], retcode=None)
        assert rc == 2
        assert not err
        assert "usage" in (cat < "tmp2.txt")().lower()
        rm("tmp2.txt")

        rc, out, _ = (grep["-Zq5"] >= ERROUT).run(["-Zq5"], retcode=None)
        assert rc == 2
        assert "usage" in out.lower()

    @skip_on_windows
    def test_popen(self):
        from plumbum.cmd import ls

        p = ls.popen(["-a"])
        out, _ = p.communicate()
        assert p.returncode == 0
        assert "test_local.py" in out.decode(local.encoding).splitlines()

    def test_run(self):
        from plumbum.cmd import grep, ls

        rc, out, err = (ls | grep["non_exist1N9"]).run(retcode=1)
        assert rc == 1

    def test_timeout(self):
        from plumbum.cmd import sleep

        with pytest.raises(ProcessTimedOut):
            sleep(3, timeout=1)

    @skip_on_windows
    def test_pipe_stderr(self, capfd):
        from plumbum.cmd import cat, head

        cat["/dev/urndom"] & FG(1)
        assert "urndom" in capfd.readouterr()[1]

        assert "" == capfd.readouterr()[1]

        (cat["/dev/urndom"] | head["-c", "10"]) & FG(retcode=1)
        assert "urndom" in capfd.readouterr()[1]

    @skip_on_windows
    def test_fair_error_attribution(self):
        # use LocalCommand directly for predictable argv
        false = LocalCommand("false")
        true = LocalCommand("true")
        with pytest.raises(ProcessExecutionError) as e:
            (false | true) & FG
        assert e.value.argv == ["false"]

    @skip_on_windows
    def test_iter_lines_timeout(self):
        from plumbum.cmd import bash

        cmd = bash["-ce", "for ((i=0;1==1;i++)); do echo $i; sleep .3; done"]
        with pytest.raises(ProcessTimedOut):
            for i, (out, err) in enumerate(cmd.popen().iter_lines(timeout=1)):
                assert not err
                assert out
                print(i, "out:", out)
        assert i in (2, 3)  # Mac is a bit flakey

    @skip_on_windows
    def test_iter_lines_timeout_by_type(self):
        from plumbum.cmd import bash
        from plumbum.commands.processes import BY_TYPE

        cmd = bash[
            "-ce", "for ((i=0;1==1;i++)); do echo $i; sleep .3; echo $i 1>&2; done"
        ]
        types = {1: "out:", 2: "err:"}
        counts = {1: 0, 2: 0}
        with pytest.raises(ProcessTimedOut):
            # Order is important on mac
            for typ, line in cmd.popen().iter_lines(timeout=1, mode=BY_TYPE):
                counts[typ] += 1
                print(types[typ], line)
        assert counts[1] in (3, 4)  # Mac is a bit flakey
        assert counts[2] in (2, 3)  # Mac is a bit flakey

    @skip_on_windows
    def test_iter_lines_error(self):
        from plumbum.cmd import ls

        with pytest.raises(ProcessExecutionError) as err:
            for i, lines in enumerate(ls["--bla"].popen()):
                pass
            assert i == 1
        assert (
            "/bin/ls: unrecognized option '--bla'" in err.value.stderr
            or "bin/ls: illegal option -- -" in err.value.stderr
        )

    @skip_on_windows
    def test_iter_lines_line_timeout(self):
        from plumbum.cmd import bash

        cmd = bash["-ce", "for ((i=0;1==1;i++)); do echo $i; sleep $i; done"]

        with pytest.raises(ProcessLineTimedOut):
            # Order is important on mac
            for i, (out, err) in enumerate(cmd.popen().iter_lines(line_timeout=0.2)):
                print(i, "out:", out)
                print(i, "err:", err)
        assert i == 1

    @skip_on_windows
    def test_modifiers(self):
        from plumbum.cmd import grep, ls

        f = (ls["-a"] | grep["\\.py"]) & BG
        f.wait()
        assert "test_local.py" in f.stdout.splitlines()

        command = ls["-a"] | grep["local"]
        command_false = ls["-a"] | grep["not_a_file_here"]
        command & FG
        assert command & TF
        assert not (command_false & TF)
        assert command & RETCODE == 0
        assert command_false & RETCODE == 1

    @skip_on_windows
    def test_tee_modifier(self, capfd):
        from plumbum.cmd import echo

        result = echo["This is fun"] & TEE
        assert result[1] == "This is fun\n"
        assert "This is fun\n" == capfd.readouterr()[0]

    @skip_on_windows
    def test_tee_race(self, capfd):
        from plumbum.cmd import seq

        EXPECT = "".join("{}\n".format(i) for i in range(1, 5001))
        for _ in range(5):
            result = seq["1", "5000"] & TEE
            assert result[1] == EXPECT
            assert EXPECT == capfd.readouterr()[0]

    @skip_on_windows
    def test_logger_pipe(self):
        from plumbum.cmd import bash
        from plumbum.commands.modifiers import PipeToLoggerMixin

        logs = []

        class Logger(PipeToLoggerMixin):
            def log(self, level, line):
                print(level, line)
                logs.append((level, line))

        logger = Logger()

        ret = bash["-ce", "echo aaa"] & logger
        assert logs[-1] == (PipeToLoggerMixin.INFO, "aaa")
        assert ret == 0

        bash["-ce", "echo bbb 1>&2"] & logger
        assert logs[-1] == (PipeToLoggerMixin.DEBUG, "bbb")

        ret = bash["-ce", "echo ccc 1>&2; false"] & logger.pipe(
            prefix="echo", retcode=1, err_level=0
        )
        assert logs[-1] == (0, "echo: ccc")
        assert ret == 1

    @skip_on_windows
    def test_logger_pipe_line_timeout(self):
        from plumbum.cmd import bash
        from plumbum.commands.modifiers import PipeToLoggerMixin

        cmd = bash["-ce", "for ((i=0;i<10;i++)); do echo .$i; sleep .$i; done"]

        class Logger(PipeToLoggerMixin):
            def log(self, level, line):
                print(level, line)
                assert level == 20
                assert float(line) <= 0.6

        logger = Logger()

        with pytest.raises(ProcessLineTimedOut):
            # Order is important on mac
            cmd & logger.pipe(line_timeout=0.45)

    def test_arg_expansion(self):
        from plumbum.cmd import ls

        args = ["-l", "-F"]
        ls(*args)
        ls[args]

    @skip_on_windows
    def test_session(self):
        sh = local.session()
        for _ in range(4):
            _, out, _ = sh.run("ls -a")
            assert "test_local.py" in out.splitlines()

        sh.run("cd ..")
        sh.run("export FOO=17")
        out = sh.run("echo $FOO")[1]
        assert out.splitlines() == ["17"]

    def test_quoting(self):
        ssh = local["ssh"]
        pwd = local["pwd"]

        cmd = ssh[
            "localhost",
            "cd",
            "/usr",
            "&&",
            ssh[
                "localhost", "cd", "/", "&&", ssh["localhost", "cd", "/bin", "&&", pwd]
            ],
        ]
        assert "\"'&&'\"" in " ".join(cmd.formulate(0))

        ls = local["ls"]
        with pytest.raises(ProcessExecutionError) as execinfo:
            ls("-a", "")  # check that empty strings are rendered correctly
        assert execinfo.value.argv[-2:] == ["-a", ""]

    def test_tempdir(self):
        from plumbum.cmd import cat

        with local.tempdir() as dir:
            assert dir.is_dir()
            data = six.b("hello world")
            with open(str(dir / "test.txt"), "wb") as f:
                f.write(data)
            with open(str(dir / "test.txt"), "rb") as f:
                assert f.read() == data

        assert not dir.exists()

    def test_direct_open_tmpdir(self):
        from plumbum.cmd import cat

        with local.tempdir() as dir:
            assert dir.is_dir()
            data = six.b("hello world")
            with open(dir / "test.txt", "wb") as f:
                f.write(data)
            with open(dir / "test.txt", "rb") as f:
                assert f.read() == data

        assert not dir.exists()

    def test_read_write_str(self):
        with local.tempdir() as tmp:
            data = "hello world"
            (tmp / "foo.txt").write(data)
            assert (tmp / "foo.txt").read() == data

    def test_read_write_unicode(self):
        with local.tempdir() as tmp:
            data = six.u("hello world")
            (tmp / "foo.txt").write(data)
            assert (tmp / "foo.txt").read() == data

    def test_read_write_bin(self):
        with local.tempdir() as tmp:
            data = six.b("hello world")
            (tmp / "foo.txt").write(data)
            assert (tmp / "foo.txt").read(mode="rb") == data

    def test_links(self):
        with local.tempdir() as tmp:
            src = tmp / "foo.txt"
            dst1 = tmp / "bar.txt"
            dst2 = tmp / "spam.txt"
            data = "hello world"
            src.write(data)
            src.link(dst1)
            assert data == dst1.read()
            src.symlink(dst2)
            assert data == dst2.read()

    def test_list_processes(self):
        assert list(local.list_processes())

    def test_pgrep(self):
        assert list(local.pgrep("python"))

    def _generate_sigint(self):
        with pytest.raises(KeyboardInterrupt):
            if sys.platform == "win32":
                from win32api import GenerateConsoleCtrlEvent

                GenerateConsoleCtrlEvent(0, 0)  # send Ctrl+C to current TTY
            else:
                os.kill(0, signal.SIGINT)
            time.sleep(1)

    @skip_without_tty
    @skip_on_windows
    def test_same_sesion(self):
        from plumbum.cmd import sleep

        p = sleep.popen([1000])
        assert p.poll() is None
        self._generate_sigint()
        time.sleep(1)
        assert p.poll() is not None

    @skip_without_tty
    def test_new_session(self):
        from plumbum.cmd import sleep

        p = sleep.popen([1000], new_session=True)
        assert p.poll() is None
        self._generate_sigint()
        time.sleep(1)
        assert p.poll() is None
        p.terminate()

    # Hangs sometimes on Windows
    @skip_on_windows
    @pytest.mark.timeout(20)
    def test_local_daemon(self):
        from plumbum.cmd import sleep

        proc = local.daemonic_popen(sleep[5])
        with pytest.raises(OSError):
            os.waitpid(proc.pid, 0)
        proc.wait()

    @skip_on_windows
    def test_atomic_file(self):
        af1 = AtomicFile("tmp.txt")
        af2 = AtomicFile("tmp.txt")
        af1.write_atomic(six.b("foo"))
        af2.write_atomic(six.b("bar"))
        assert af1.read_atomic() == six.b("bar")
        assert af2.read_atomic() == six.b("bar")
        local.path("tmp.txt").delete()

    @skip_on_windows
    def test_atomic_file2(self):
        af = AtomicFile("tmp.txt")

        code = """from __future__ import with_statement
from plumbum.fs.atomic import AtomicFile
af = AtomicFile("tmp.txt")
try:
    with af.locked(blocking = False):
        raise ValueError("this should have failed")
except (OSError, IOError):
    print("already locked")
"""
        with af.locked():
            output = local.python("-c", code)
            assert output.strip() == "already locked"

        local.path("tmp.txt").delete()

    @skip_on_windows
    def test_pid_file(self):
        code = """from __future__ import with_statement
from plumbum.fs.atomic import PidFile, PidFileTaken
try:
    with PidFile("mypid"):
        raise ValueError("this should have failed")
except PidFileTaken:
    print("already locked")
"""
        with PidFile("mypid"):
            output = local.python("-c", code)
            assert output.strip() == "already locked"

        local.path("mypid").delete()

    @skip_on_windows
    def test_atomic_counter(self):
        local.path("counter").delete()
        num_of_procs = 20
        num_of_increments = 20

        code = """from plumbum.fs.atomic import AtomicCounterFile
import time
time.sleep(0.2)
afc = AtomicCounterFile.open("counter")
for _ in range({}):
    print(afc.next())
    time.sleep(0.1)
""".format(
            num_of_increments,
        )

        procs = []
        for _ in range(num_of_procs):
            procs.append(local.python["-c", code].popen())
        results = []
        for p in procs:
            out, _ = p.communicate()
            assert p.returncode == 0
            results.extend(int(num) for num in out.splitlines())

        assert len(results) == num_of_procs * num_of_increments
        assert len(set(results)) == len(results)
        assert min(results) == 0
        assert max(results) == num_of_procs * num_of_increments - 1
        local.path("counter").delete()

    @skip_on_windows
    def test_atomic_counter2(self):
        local.path("counter").delete()
        afc = AtomicCounterFile.open("counter")
        assert afc.next() == 0
        assert afc.next() == 1
        assert afc.next() == 2

        with pytest.raises(TypeError):
            afc.reset("hello")

        afc.reset(70)
        assert afc.next() == 70
        assert afc.next() == 71
        assert afc.next() == 72

        local.path("counter").delete()

    @skip_on_windows
    @pytest.mark.skipif("printenv" not in local, reason="printenv is missing")
    def test_bound_env(self):
        from plumbum.cmd import printenv

        with local.env(FOO="hello"):
            assert printenv.with_env(BAR="world")("FOO") == "hello\n"
            assert printenv.with_env(BAR="world")("BAR") == "world\n"
            assert printenv.with_env(FOO="sea", BAR="world")("FOO") == "sea\n"
            assert printenv("FOO") == "hello\n"

        assert local.cmd.pwd.with_cwd("/")() == "/\n"
        assert local.cmd.pwd["-L"].with_env(A="X").with_cwd("/")() == "/\n"

    def test_nesting_lists_as_argv(self):
        from plumbum.cmd import ls

        c = ls["-l", ["-a", "*.py"]]
        assert c.formulate()[1:] == ["-l", "-a", "*.py"]

    def test_contains(self):
        assert "ls" in local

    def test_issue_139(self):
        LocalPath(local.cwd)

    def test_pipeline_failure(self):
        from plumbum.cmd import head, ls

        with pytest.raises(ProcessExecutionError):
            (ls["--no-such-option"] | head)()

    def test_cmd(self):
        local.cmd.ls("/tmp")

    def test_pipeline_retcode(self):
        "From PR #288"
        from plumbum.cmd import echo, grep

        print((echo["one two three four"] | grep["two"] | grep["three"])(retcode=None))
        print((echo["one two three four"] | grep["five"] | grep["three"])(retcode=None))
        print((echo["one two three four"] | grep["two"] | grep["five"])(retcode=None))
        print((echo["one two three four"] | grep["six"] | grep["five"])(retcode=None))

    def test_pipeline_stdin(self):
        from subprocess import PIPE

        from plumbum.cmd import cat

        with (cat | cat).bgrun(stdin=PIPE) as future:
            future.stdin.write(b"foobar")
            future.stdin.close()

    def test_run_bg(self):
        from plumbum.cmd import ls

        f = ls["-a"].run_bg()
        f.wait()
        assert "test_local.py" in f.stdout

    def test_run_fg(self, capfd):
        from plumbum.cmd import ls

        ls["-l"].run_fg()
        stdout = capfd.readouterr()[0]
        assert "test_local.py" in stdout

    @skip_on_windows
    def test_run_tee(self, capfd):
        from plumbum.cmd import echo

        result = echo["This is fun"].run_tee()
        assert result[1] == "This is fun\n"
        assert "This is fun\n" == capfd.readouterr()[0]

    def test_run_tf(self):
        from plumbum.cmd import ls

        f = ls["-l"].run_tf()
        assert f == True

    def test_run_retcode(self):
        from plumbum.cmd import ls

        f = ls["-l"].run_retcode()
        assert f == 0

    def test_run_nohup(self):
        from plumbum.cmd import ls

        f = ls["-l"].run_nohup()
        f.wait()
        assert os.path.exists("nohup.out")
        os.unlink("nohup.out")


class TestLocalEncoding:
    try:
        richstr = unichr(40960)
    except NameError:
        richstr = chr(40960)

    @pytest.mark.xfail(
        IS_WIN32,
        reason="Unicode output on Windows does not work (Python 3.6+ was supposed to work)",
    )
    def test_inout_rich(self):
        from plumbum.cmd import echo

        out = echo(self.richstr)
        assert self.richstr in out

    @pytest.mark.xfail(
        IS_WIN32 and sys.version_info < (3, 6),
        reason="Unicode output on Windows requires Python 3.6+",
    )
    @pytest.mark.usefixtures("cleandir")
    def test_out_rich(self):
        import io

        from plumbum.cmd import cat

        with io.open("temp.txt", "w", encoding="utf8") as f:
            f.write(self.richstr)
        out = cat("temp.txt")
        assert self.richstr in out

    @pytest.mark.xfail(IS_WIN32, reason="Unicode path not supported on Windows for now")
    @pytest.mark.skipif(not six.PY3, reason="Unicode paths only supported on Python 3")
    @pytest.mark.usefixtures("cleandir")
    def test_runfile_rich(self):
        import os
        import stat

        name = self.richstr + six.str("_program")
        with open(name, "w") as f:
            f.write("#!{}\nprint('yes')".format(sys.executable))

        st = os.stat(name)
        os.chmod(name, st.st_mode | stat.S_IEXEC)

        assert "yes" in local[local.cwd / name]()


@pytest.mark.skipif(
    IS_WIN32, reason="Windows does not support these weird paths, so unambiguous there"
)
def test_local_glob_path(tmpdir):
    p = tmpdir.mkdir("a*b?c")
    p2 = tmpdir.mkdir("aanythingbxc")
    p2.join("something.txt").write("content")
    p.join("hello.txt").write("content")
    p.join("other.txt").write("content")

    pp = LocalPath(str(p))
    assert len(pp // "*.txt") == 2
