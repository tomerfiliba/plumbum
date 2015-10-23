import os
import unittest
import sys
import signal
import time
from plumbum import (local, LocalPath, FG, BG, TF, RETCODE, ERROUT,
                    CommandNotFound, ProcessExecutionError, ProcessTimedOut)
from plumbum.lib import six, IS_WIN32
from plumbum.fs.atomic import AtomicFile, AtomicCounterFile, PidFile
from plumbum.path import RelativePath
import plumbum
from plumbum._testtools import (skipIf, skip_on_windows,
                       skip_without_tty, skip_without_chown)

try:
    import pathlib
except ImportError:
    pathlib = None

class LocalPathTest(unittest.TestCase):
    def setUp(self):
        self.longpath = LocalPath("/some/long/path/to/file.txt")
    
    def test_name(self):
        name = self.longpath.name
        self.assertTrue(isinstance(name, six.string_types))
        self.assertEqual("file.txt", str(name))

    def test_dirname(self):
        name = self.longpath.dirname
        self.assertTrue(isinstance(name, LocalPath))
        self.assertEqual("/some/long/path/to", str(name).replace("\\", "/"))

    def test_uri(self):
        self.assertEqual("file:///some/long/path/to/file.txt", self.longpath.as_uri())


    @skip_without_chown
    def test_chown(self):
        with local.tempdir() as dir:
            p = dir / "foo.txt"
            p.write(six.b("hello"))
            self.assertEqual(p.uid, os.getuid())
            self.assertEqual(p.gid, os.getgid())
            p.chown(p.uid.name)
            self.assertEqual(p.uid, os.getuid())

    def test_split(self):
        p = local.path("/var/log/messages")
        self.assertEqual(p.split(), ["var", "log", "messages"])

    def test_suffix(self):
        p1 = self.longpath
        p2 = local.path("file.tar.gz")
        self.assertEqual(p1.suffix, ".txt")
        self.assertEqual(p1.suffixes, [".txt"])
        self.assertEqual(p2.suffix, ".gz")
        self.assertEqual(p2.suffixes, [".tar",".gz"])
        self.assertEqual(p1.with_suffix(".tar.gz"), local.path("/some/long/path/to/file.tar.gz"))
        self.assertEqual(p2.with_suffix(".other"), local.path("file.tar.other"))
        self.assertEqual(p2.with_suffix(".other", 2), local.path("file.other"))
        self.assertEqual(p2.with_suffix(".other", 0), local.path("file.tar.gz.other"))
        self.assertEqual(p2.with_suffix(".other", None), local.path("file.other"))

    def test_newname(self):
        p1 = self.longpath
        p2 = local.path("file.tar.gz")
        self.assertEqual(p1.with_name("something.tar"), local.path("/some/long/path/to/something.tar"))
        self.assertEqual(p2.with_name("something.tar"), local.path("something.tar"))

    def test_relative_to(self):
        p = local.path("/var/log/messages")
        self.assertEqual(p.relative_to("/var/log/messages"), RelativePath([]))
        self.assertEqual(p.relative_to("/var/"), RelativePath(["log", "messages"]))
        self.assertEqual(p.relative_to("/"), RelativePath(["var", "log", "messages"]))
        self.assertEqual(p.relative_to("/var/tmp"), RelativePath(["..", "log", "messages"]))
        self.assertEqual(p.relative_to("/opt"), RelativePath(["..", "var", "log", "messages"]))
        self.assertEqual(p.relative_to("/opt/lib"), RelativePath(["..", "..", "var", "log", "messages"]))
        for src in [local.path("/var/log/messages"), local.path("/var"), local.path("/opt/lib")]:
            delta = p.relative_to(src)
            self.assertEqual(src + delta, p)

    def test_read_write(self):
        with local.tempdir() as dir:
            f = dir / "test.txt"
            text = six.b('hello world\xd7\xa9\xd7\x9c\xd7\x95\xd7\x9d').decode("utf8")
            f.write(text, "utf8")
            text2 = f.read("utf8")
            self.assertEqual(text, text2)

    def test_parts(self):
        parts = self.longpath.parts
        self.assertEqual(parts, ('/', 'some', 'long', 'path', 'to', 'file.txt'))
        
    def test_stem(self):
        self.assertEqual(self.longpath.stem, "file")
        p = local.path("/some/directory")
        self.assertEqual(p.stem, "directory")
        
    @skipIf(pathlib is None, "This test requires pathlib")
    def test_root_drive(self):
        pl_path = pathlib.Path("/some/long/path/to/file.txt").absolute()
        self.assertEqual(self.longpath.root, pl_path.root)
        self.assertEqual(self.longpath.drive, pl_path.drive)
        
        p_path = local.cwd / "somefile.txt"
        pl_path = pathlib.Path("somefile.txt").absolute()
        self.assertEqual(p_path.root, pl_path.root)
        self.assertEqual(p_path.drive, pl_path.drive)
        
    @skipIf(pathlib is None, "This test requires pathlib")
    def test_compare_pathlib(self):
        def filename_compare(name):
            p = local.path(str(name))
            pl = pathlib.Path(str(name)).absolute()
            self.assertEqual(str(p), str(pl))
            self.assertEqual(p.parts, pl.parts)
            self.assertEqual(p.exists(), pl.exists())
            self.assertEqual(p.as_uri(), pl.as_uri())
            self.assertEqual(str(p.with_suffix('.this')), str(pl.with_suffix('.this')))
            self.assertEqual(p.name, pl.name)

        filename_compare("/some/long/path/to/file.txt")
        filename_compare(local.cwd / "somefile.txt")
        filename_compare("/some/long/path/")
        filename_compare("/some/long/path")
        filename_compare(__file__)

    def test_suffix_expected(self):
        self.assertEqual(self.longpath.preferred_suffix('.tar'), self.longpath)
        self.assertEqual((local.cwd / 'this').preferred_suffix('.txt'), local.cwd / 'this.txt')

class LocalMachineTest(unittest.TestCase):
    def test_getattr(self):
        pb = plumbum
        self.assertEqual(getattr(pb.cmd, 'does_not_exist', 1), 1)
        ls_cmd1 = pb.cmd.non_exist1N9 if hasattr(pb.cmd, 'non_exist1N9') else pb.cmd.ls
        ls_cmd2 = getattr(pb.cmd, 'non_exist1N9', pb.cmd.ls)
        self.assertEqual(str(ls_cmd1), str(local['ls']))
        self.assertEqual(str(ls_cmd2), str(local['ls']))

    # TODO: This probably fails because of odd ls behavior
    @skip_on_windows
    def test_imports(self):
        from plumbum.cmd import ls
        self.assertTrue("test_local.py" in local["ls"]().splitlines())
        self.assertTrue("test_local.py" in ls().splitlines())

        self.assertRaises(CommandNotFound, lambda: local["non_exist1N9"])

        try:
            from plumbum.cmd import non_exist1N9 #@UnresolvedImport @UnusedImport
        except (ImportError, CommandNotFound):
            pass
        else:
            self.fail("from plumbum.cmd import non_exist1N9")

    def test_get(self):
        self.assertEqual(str(local['ls']),str(local.get('ls')))
        self.assertEqual(str(local['ls']),str(local.get('non_exist1N9', 'ls')))
        self.assertRaises(CommandNotFound, lambda: local.get("non_exist1N9"))
        self.assertRaises(CommandNotFound, lambda: local.get("non_exist1N9", "non_exist1N8"))
        self.assertRaises(CommandNotFound, lambda: local.get("non_exist1N9", "/tmp/non_exist1N8"))

    def test_shadowed_by_dir(self):
        real_ls = local['ls']
        with local.tempdir() as tdir:
            with local.cwd(tdir):
                ls_dir = tdir / 'ls'
                ls_dir.mkdir()
                fake_ls = local['ls']
                assert fake_ls.executable == real_ls.executable

                local.env.path.insert(0, tdir)
                fake_ls = local['ls']
                del local.env.path[0]
                assert fake_ls.executable == real_ls.executable
            


        

    @skip_on_windows
    def test_cwd(self):
        from plumbum.cmd import ls
        self.assertEqual(local.cwd, os.getcwd())
        self.assertTrue("__init__.py" not in ls().splitlines())
        with local.cwd("../plumbum"):
            self.assertTrue("__init__.py" in ls().splitlines())
        self.assertTrue("__init__.py" not in ls().splitlines())
        self.assertRaises(OSError, local.cwd.chdir, "../non_exist1N9")

    @skip_on_windows
    def test_mixing_chdir(self):
        self.assertEqual(local.cwd, os.getcwd())
        os.chdir('../plumbum')
        self.assertEqual(local.cwd, os.getcwd())
        os.chdir('../tests')
        self.assertEqual(local.cwd, os.getcwd())

    @skip_on_windows
    def test_path(self):
        self.assertFalse((local.cwd / "../non_exist1N9").exists())
        self.assertTrue((local.cwd / ".." / "plumbum").is_dir())
        # traversal
        found = False
        for fn in local.cwd / ".." / "plumbum":
            if fn.name == "__init__.py":
                self.assertTrue(fn.is_file())
                found = True
        self.assertTrue(found)
        # glob'ing
        found = False
        for fn in local.cwd / ".." // "*/*.rst":
            if fn.name == "index.rst":
                found = True
        self.assertTrue(found)
        for fn in local.cwd / ".." // ("*/*.rst", "*./*.html"):
            if fn.name == "index.rst":
                found = True
        self.assertTrue(found)

    @skip_on_windows
    def test_env(self):
        self.assertTrue("PATH" in local.env)
        self.assertFalse("FOOBAR72" in local.env)
        self.assertRaises(ProcessExecutionError, local.python, "-c", "import os;os.environ['FOOBAR72']")
        local.env["FOOBAR72"] = "spAm"
        self.assertEqual(local.python("-c", "import os;print (os.environ['FOOBAR72'])").splitlines(), ["spAm"])

        with local.env(FOOBAR73 = 1889):
            self.assertEqual(local.python("-c", "import os;print (os.environ['FOOBAR73'])").splitlines(), ["1889"])
            with local.env(FOOBAR73 = 1778):
                self.assertEqual(local.python("-c", "import os;print (os.environ['FOOBAR73'])").splitlines(), ["1778"])
            self.assertEqual(local.python("-c", "import os;print (os.environ['FOOBAR73'])").splitlines(), ["1889"])
        self.assertRaises(ProcessExecutionError, local.python, "-c", "import os;os.environ['FOOBAR73']")

        # path manipulation
        self.assertRaises(CommandNotFound, local.which, "dummy-executable")
        with local.env():
            local.env.path.insert(0, local.cwd / "not-in-path")
            p = local.which("dummy-executable")
            self.assertEqual(p, local.cwd / "not-in-path" / "dummy-executable")

    def test_local(self):
        self.assertTrue("plumbum" in str(local.cwd))
        self.assertTrue("PATH" in local.env.getdict())
        self.assertEqual(local.path("foo"), os.path.join(os.getcwd(), "foo"))
        local.which("ls")
        local["ls"]
        self.assertEqual(local.python("-c", "print ('hi there')").splitlines(), ["hi there"])

    @skip_on_windows
    def test_piping(self):
        from plumbum.cmd import ls, grep
        chain = ls | grep["\\.py"]
        self.assertTrue("test_local.py" in chain().splitlines())

        chain = (ls["-a"] | grep["test"] | grep["local"])
        self.assertTrue("test_local.py" in chain().splitlines())

    @skip_on_windows
    def test_redirection(self):
        from plumbum.cmd import cat, ls, grep, rm

        chain = (ls | grep["\\.py"]) > "tmp.txt"
        chain()

        chain2 = (cat < "tmp.txt") | grep["local"]
        self.assertTrue("test_local.py" in chain2().splitlines())
        rm("tmp.txt")

        chain3 = (cat << "this is the\nworld of helloness and\nspam bar and eggs") | grep["hello"]
        self.assertTrue("world of helloness and" in chain3().splitlines())

        rc, _, err = (grep["-Zq5"] >= "tmp2.txt").run(["-Zq5"], retcode = None)
        self.assertEqual(rc, 2)
        self.assertFalse(err)
        self.assertTrue("usage" in (cat < "tmp2.txt")().lower())
        rm("tmp2.txt")

        rc, out, _ = (grep["-Zq5"] >= ERROUT).run(["-Zq5"], retcode = None)
        self.assertEqual(rc, 2)
        self.assertTrue("usage" in out.lower())

    @skip_on_windows
    def test_popen(self):
        from plumbum.cmd import ls

        p = ls.popen(["-a"])
        out, _ = p.communicate()
        self.assertEqual(p.returncode, 0)
        self.assertTrue("test_local.py" in out.decode(local.encoding).splitlines())

    def test_run(self):
        from plumbum.cmd import ls, grep

        rc, out, err = (ls | grep["non_exist1N9"]).run(retcode = 1)
        self.assertEqual(rc, 1)

    def test_timeout(self):
        from plumbum.cmd import sleep
        self.assertRaises(ProcessTimedOut, sleep, 10, timeout = 5)

    @skip_on_windows
    def test_iter_lines_timeout(self):
        from plumbum.cmd import ping

        try:
            # Order is important on mac
            for i, (out, err) in enumerate(ping["-i", 0.5, "127.0.0.1"].popen().iter_lines(timeout=2)):
                print("out:", out)
                print("err:", err)
        except ProcessTimedOut:
            self.assertTrue(i > 3)
        else:
            self.fail("Expected a timeout")


    @skip_on_windows
    def test_iter_lines_error(self):
        from plumbum.cmd import ls
        try:
            for i, lines in enumerate(ls["--bla"].popen()):
                pass
            self.assertEqual(i, 1)
        except ProcessExecutionError:
            ex = sys.exc_info()[1]
            self.assertTrue(ex.stderr.startswith("/bin/ls: unrecognized option '--bla'")
                            or ex.stderr.startswith("/bin/ls: illegal option -- -"))
        else:
            self.fail("Expected an execution error")

    @skip_on_windows
    def test_modifiers(self):
        from plumbum.cmd import ls, grep
        f = (ls["-a"] | grep["\\.py"]) & BG
        f.wait()
        self.assertTrue("test_local.py" in f.stdout.splitlines())

        command = (ls["-a"] | grep["local"])
        command_false = (ls["-a"] | grep["not_a_file_here"])
        command & FG
        self.assertTrue(command & TF)
        self.assertFalse(command_false & TF)
        self.assertEqual(command & RETCODE, 0)
        self.assertEqual(command_false & RETCODE, 1)



    def test_arg_expansion(self):
        from plumbum.cmd import ls
        args = [ '-l', '-F' ]
        ls(*args)
        ls[args]

    @skip_on_windows
    def test_session(self):
        sh = local.session()
        for _ in range(4):
            _, out, _ = sh.run("ls -a")
            self.assertTrue("test_local.py" in out.splitlines())

        sh.run("cd ..")
        sh.run("export FOO=17")
        out = sh.run("echo $FOO")[1]
        self.assertEqual(out.splitlines(), ["17"])

    def test_quoting(self):
        ssh = local["ssh"]
        pwd = local["pwd"]

        cmd = ssh["localhost", "cd", "/usr", "&&", ssh["localhost", "cd", "/", "&&",
            ssh["localhost", "cd", "/bin", "&&", pwd]]]
        self.assertTrue("\"'&&'\"" in " ".join(cmd.formulate(0)))

        ls = local['ls']
        try:
            ls('-a', '') # check that empty strings are rendered correctly
        except ProcessExecutionError:
            ex = sys.exc_info()[1]
            self.assertEqual(ex.argv[-2:], ['-a', ''])
        else:
            self.fail("Expected `ls` to fail")

    def test_tempdir(self):
        from plumbum.cmd import cat
        with local.tempdir() as dir:
            self.assertTrue(dir.is_dir())
            data = six.b("hello world")
            with open(str(dir / "test.txt"), "wb") as f:
                f.write(data)
            with open(str(dir / "test.txt"), "rb") as f:
                self.assertEqual(f.read(), data)

        self.assertFalse(dir.exists())

    def test_direct_open_tmpdir(self):
        from plumbum.cmd import cat
        with local.tempdir() as dir:
            self.assertTrue(dir.is_dir())
            data = six.b("hello world")
            with open(dir / "test.txt", "wb") as f:
                f.write(data)
            with open(dir / "test.txt", "rb") as f:
                self.assertEqual(f.read(), data)

        self.assertFalse(dir.exists())


    def test_read_write(self):
        with local.tempdir() as tmp:
            data = six.b("hello world")
            (tmp / "foo.txt").write(data)
            self.assertEqual((tmp / "foo.txt").read(), data)

    def test_links(self):
        with local.tempdir() as tmp:
            src = tmp / "foo.txt"
            dst1 = tmp / "bar.txt"
            dst2 = tmp / "spam.txt"
            data = six.b("hello world")
            src.write(data)
            src.link(dst1)
            self.assertEqual(data, dst1.read())
            src.symlink(dst2)
            self.assertEqual(data, dst2.read())

    @skip_on_windows
    def test_as_user(self):
        with local.as_root():
            local["date"]()

    def test_list_processes(self):
        self.assertTrue(list(local.list_processes()))

    def test_pgrep(self):
        self.assertTrue(list(local.pgrep("python")))

    def _generate_sigint(self):
        try:
            if sys.platform == "win32":
                from win32api import GenerateConsoleCtrlEvent
                GenerateConsoleCtrlEvent(0, 0) # send Ctrl+C to current TTY
            else:
                os.kill(0, signal.SIGINT)
            time.sleep(1)
        except KeyboardInterrupt:
            pass
        else:
            self.fail("Expected KeyboardInterrupt")

    @skip_without_tty
    @skip_on_windows
    def test_same_sesion(self):
        from plumbum.cmd import sleep
        p = sleep.popen([1000])
        self.assertTrue(p.poll() is None)
        self._generate_sigint()
        time.sleep(1)
        self.assertTrue(p.poll() is not None)

    @skip_without_tty
    def test_new_session(self):
        from plumbum.cmd import sleep
        p = sleep.popen([1000], new_session = True)
        self.assertTrue(p.poll() is None)
        self._generate_sigint()
        time.sleep(1)
        self.assertTrue(p.poll() is None)
        p.terminate()

    def test_local_daemon(self):
        from plumbum.cmd import sleep
        proc = local.daemonic_popen(sleep[5])
        try:
            os.waitpid(proc.pid, 0)
        except OSError:
            pass
        else:
            self.fail("I shouldn't have any children by now -- they are daemons!")
        proc.wait()

    @skip_on_windows
    def test_atomic_file(self):
        af1 = AtomicFile("tmp.txt")
        af2 = AtomicFile("tmp.txt")
        af1.write_atomic(six.b("foo"))
        af2.write_atomic(six.b("bar"))
        self.assertEqual(af1.read_atomic(), six.b("bar"))
        self.assertEqual(af2.read_atomic(), six.b("bar"))
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
            self.assertEqual(output.strip(), "already locked")

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
            self.assertEqual(output.strip(), "already locked")

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
for _ in range(%s):
    print(afc.next())
    time.sleep(0.1)
""" % (num_of_increments,)

        procs = []
        for _ in range(num_of_procs):
            procs.append(local.python["-c", code].popen())
        results = []
        for p in procs:
            out, _ = p.communicate()
            self.assertEqual(p.returncode, 0)
            results.extend(int(num) for num in out.splitlines())

        self.assertEqual(len(results), num_of_procs * num_of_increments)
        self.assertEqual(len(set(results)), len(results))
        self.assertEqual(min(results), 0)
        self.assertEqual(max(results), num_of_procs * num_of_increments - 1)
        local.path("counter").delete()

    @skip_on_windows
    def test_atomic_counter2(self):
        local.path("counter").delete()
        afc = AtomicCounterFile.open("counter")
        self.assertEqual(afc.next(), 0)
        self.assertEqual(afc.next(), 1)
        self.assertEqual(afc.next(), 2)

        self.assertRaises(TypeError, afc.reset, "hello")

        afc.reset(70)
        self.assertEqual(afc.next(), 70)
        self.assertEqual(afc.next(), 71)
        self.assertEqual(afc.next(), 72)

        local.path("counter").delete()

    @skip_on_windows
    def test_bound_env(self):
        try:
            from plumbum.cmd import printenv
        except CommandNotFound:
            self.skipTest("printenv is missing")
        with local.env(FOO = "hello"):
            self.assertEqual(printenv.with_env(BAR = "world")("FOO"), "hello\n")
            self.assertEqual(printenv.with_env(BAR = "world")("BAR"), "world\n")
            self.assertEqual(printenv.with_env(FOO = "sea", BAR = "world")("FOO"), "sea\n")
            self.assertEqual(printenv("FOO"), "hello\n")

    def test_nesting_lists_as_argv(self):
        from plumbum.cmd import ls
        c = ls["-l", ["-a", "*.py"]]
        self.assertEqual(c.formulate()[1:], ['-l', '-a', '*.py'])

    def test_contains(self):
        self.assertTrue("ls" in local, "Expected to find `ls`")

    def test_issue_139(self):
        LocalPath(local.cwd)

    def test_pipeline_failure(self):
        from plumbum.cmd import ls, head
        self.assertRaises(ProcessExecutionError, (ls["--no-such-option"] | head))


if __name__ == "__main__":
    unittest.main()

