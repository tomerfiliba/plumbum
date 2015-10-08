import unittest
import time

from plumbum import cli, local
from plumbum.cli.terminal import ask, choose, hexdump, Progress
from plumbum.lib import captured_stdout

class SimpleApp(cli.Application):
    @cli.switch(["a"])
    def spam(self):
        print("!!a")

    @cli.switch(["b", "bacon"], argtype=int, mandatory = True, envname="PLUMBUM_TEST_BACON")
    def bacon(self, param):
        """give me some bacon"""
        print ("!!b", param)

    eggs = cli.SwitchAttr(["e"], str, help = "sets the eggs attribute", envname="PLUMBUM_TEST_EGGS")
    verbose = cli.CountOf(["v"], help = "increases the verbosity level")
    benedict = cli.CountOf(["--benedict"], help = """a very long help message with lots of
        useless information that nobody would ever want to read, but heck, we need to test
        text wrapping in help messages as well""")

    def main(self, *args):
        old = self.eggs
        self.eggs = "lalala"
        self.eggs = old
        self.tailargs = args



class Geet(cli.Application):
    debug = cli.Flag("--debug")
    cleanups = []
    def main(self):
        del self.cleanups[:]
        print ("hi this is geet main")

    def cleanup(self, retcode):
        self.cleanups.append(1)
        print("geet cleaning up with rc = %s" % (retcode,))

@Geet.subcommand("add")
class GeetAdd(cli.Application):
    def main(self, *files):
        return "adding", files

@Geet.subcommand("commit")
class GeetCommit(cli.Application):
    message = cli.Flag("-m", str)

    def main(self):
        if self.parent.debug:
            return "committing in debug"
        else:
            return "committing"

    def cleanup(self, retcode):
        self.parent.cleanups.append(2)
        print("geet commit cleaning up with rc = %s" % (retcode,))

class Sample(cli.Application):
    foo = cli.SwitchAttr("--foo")

Sample.unbind_switches("--version")

class Mumble(cli.Application):
    pass

Sample.subcommand("mumble", Mumble)

class LazyLoaded(cli.Application):
    def main(self):
        print("hello world")

if not hasattr(unittest.TestCase, "assertIn"):
    def assertIn(self, member, container, msg = None):
        if msg:
            assert member in container, msg
        else:
            assert member in container
    def assertNotIn(self, member, container, msg = None):
        if msg:
            assert member not in container, msg
        else:
            assert member not in container
    unittest.TestCase.assertIn = assertIn
    unittest.TestCase.assertNotIn = assertNotIn


class CLITest(unittest.TestCase):
    def test_meta_switches(self):
        _, rc = SimpleApp.run(["foo", "-h"], exit = False)
        self.assertEqual(rc, 0)
        _, rc = SimpleApp.run(["foo", "--version"], exit = False)
        self.assertEqual(rc, 0)

    def test_okay(self):
        _, rc = SimpleApp.run(["foo", "--bacon=81"], exit = False)
        self.assertEqual(rc, 0)

        inst, rc = SimpleApp.run(["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv",
            "--", "lala", "-e", "7"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual(inst.eggs, "7")

    def test_failures(self):
        _, rc = SimpleApp.run(["foo"], exit = False)
        self.assertEqual(rc, 2)

        _, rc = SimpleApp.run(["foo", "--bacon=hello"], exit = False)
        self.assertEqual(rc, 2)

    def test_subcommands(self):
        _, rc = Geet.run(["geet", "--debug"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual(Geet.cleanups, [1])
        _, rc = Geet.run(["geet", "--debug", "add", "foo.txt", "bar.txt"], exit = False)
        self.assertEqual(rc, ("adding", ("foo.txt", "bar.txt")))
        self.assertEqual(Geet.cleanups, [1])
        _, rc = Geet.run(["geet", "--debug", "commit"], exit = False)
        self.assertEqual(rc, "committing in debug")
        self.assertEqual(Geet.cleanups, [2, 1])
        _, rc = Geet.run(["geet", "--help"], exit = False)
        self.assertEqual(rc, 0)
        _, rc = Geet.run(["geet", "commit", "--help"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual(Geet.cleanups, [1])

    def test_unbind(self):
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "--help"], exit = False)
        self.assertEqual(rc, 0)
        self.assertIn("--foo", stream.getvalue())
        self.assertNotIn("--version", stream.getvalue())

    def test_default_main(self):
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("No sub-command given", stream.getvalue())

        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "pimple"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("Unknown sub-command 'pimple'", stream.getvalue())

        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "mumble"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("main() not implemented", stream.getvalue())

    def test_lazy_subcommand(self):
        class Foo(cli.Application):
            pass

        Foo.subcommand("lazy", "test_cli.LazyLoaded")

        with captured_stdout() as stream:
            _, rc = Foo.run(["foo", "lazy"], exit = False)

        self.assertEqual(rc, 0)
        self.assertIn("hello world", stream.getvalue())

    def test_reset_switchattr(self):
        inst, rc = SimpleApp.run(["foo", "--bacon=81", "-e", "bar"], exit=False)
        self.assertEqual(rc, 0)
        self.assertEqual(inst.eggs, "bar")

        inst, rc = SimpleApp.run(["foo", "--bacon=81"], exit=False)
        self.assertEqual(rc, 0)
        self.assertEqual(inst.eggs, None)

    def test_invoke(self):
        inst, rc = SimpleApp.invoke("arg1", "arg2", eggs="sunny", bacon=10, verbose=2)
        self.assertEqual((inst.eggs, inst.verbose, inst.tailargs), ("sunny", 2, ("arg1", "arg2")))

    def test_env_var(self):
        with captured_stdout() as stream:
            _, rc = SimpleApp.run(["arg", "--bacon=10"], exit=False)
            self.assertEqual(rc, 0)
            self.assertIn("10", stream.getvalue())

        with captured_stdout() as stream:
            with local.env(
                PLUMBUM_TEST_BACON='20',
                PLUMBUM_TEST_EGGS='raw',
            ):
                inst, rc = SimpleApp.run(["arg"], exit=False)

            self.assertEqual(rc, 0)
            self.assertIn("20", stream.getvalue())
            self.assertEqual(inst.eggs, 'raw')

    def test_mandatory_env_var(self):
        with captured_stdout() as stream:
            _, rc = SimpleApp.run(["arg"], exit = False)
            self.assertEqual(rc, 2)
            self.assertIn("bacon is mandatory", stream.getvalue())


class TestTerminal(unittest.TestCase):
    def test_ask(self):
        with captured_stdout("\n") as stream:
            self.assertTrue(ask("Do you like cats?", default = True))
        self.assertEqual(stream.getvalue(), "Do you like cats? [Y/n] ")
        with captured_stdout("\nyes") as stream:
            self.assertTrue(ask("Do you like cats?"))
        self.assertEqual(stream.getvalue(), "Do you like cats? (y/n) Invalid response, please try again\nDo you like cats? (y/n) ")

    def test_choose(self):
        with captured_stdout("foo\n2\n") as stream:
            self.assertEqual(choose("What is your favorite color?", ["blue", "yellow", "green"]), "yellow")
        self.assertEqual(stream.getvalue(), "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: ")
        with captured_stdout("foo\n2\n") as stream:
            self.assertEqual(choose("What is your favorite color?", [("blue", 10), ("yellow", 11), ("green", 12)]), 11)
        self.assertEqual(stream.getvalue(), "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: ")
        with captured_stdout("foo\n\n") as stream:
            self.assertEqual(choose("What is your favorite color?", ["blue", "yellow", "green"], default = "yellow"), "yellow")
        self.assertEqual(stream.getvalue(), "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice [2]: Invalid choice, please try again\nChoice [2]: ")

    def test_hexdump(self):
        data = "hello world my name is queen marry" + "A" * 66 + "foo bar"
        output = """\
000000 | 68 65 6c 6c 6f 20 77 6f 72 6c 64 20 6d 79 20 6e | hello world my n
000010 | 61 6d 65 20 69 73 20 71 75 65 65 6e 20 6d 61 72 | ame is queen mar
000020 | 72 79 41 41 41 41 41 41 41 41 41 41 41 41 41 41 | ryAAAAAAAAAAAAAA
000030 | 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 | AAAAAAAAAAAAAAAA
*
000060 | 41 41 41 41 66 6f 6f 20 62 61 72                | AAAAfoo bar"""
        self.assertEqual("\n".join(hexdump(data)), output)

    def test_progress(self):
        with captured_stdout() as stream:
            for i in Progress.range(4, has_output=True, timer=False):
                print('hi')
                time.sleep(.5)
            stream.seek(0)
            output = """\
0% complete
0% complete
hi
25% complete
hi
50% complete
hi
75% complete
hi
100% complete

"""
            self.assertEqual(stream.read(), output)



if __name__ == "__main__":
    unittest.main()




