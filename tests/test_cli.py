import pytest
import time
import sys
from contextlib import contextmanager

from plumbum import cli, local
from plumbum.cli.terminal import ask, choose, hexdump, Progress
from plumbum.lib import StringIO

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



class TestCLI:
    def test_meta_switches(self):
        _, rc = SimpleApp.run(["foo", "-h"], exit = False)
        assert rc == 0
        _, rc = SimpleApp.run(["foo", "--version"], exit = False)
        assert rc == 0

    def test_okay(self):
        _, rc = SimpleApp.run(["foo", "--bacon=81"], exit = False)
        assert rc == 0

        inst, rc = SimpleApp.run(["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv",
            "--", "lala", "-e", "7"], exit = False)
        assert rc == 0
        assert inst.eggs == "7"

    def test_failures(self):
        _, rc = SimpleApp.run(["foo"], exit = False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=hello"], exit = False)
        assert rc == 2

    def test_subcommands(self):
        _, rc = Geet.run(["geet", "--debug"], exit = False)
        assert rc == 0
        assert Geet.cleanups == [1]
        _, rc = Geet.run(["geet", "--debug", "add", "foo.txt", "bar.txt"], exit = False)
        assert rc == ("adding", ("foo.txt", "bar.txt"))
        assert Geet.cleanups == [1]
        _, rc = Geet.run(["geet", "--debug", "commit"], exit = False)
        assert rc == "committing in debug"
        assert Geet.cleanups == [2, 1]
        _, rc = Geet.run(["geet", "--help"], exit = False)
        assert rc == 0
        _, rc = Geet.run(["geet", "commit", "--help"], exit = False)
        assert rc == 0
        assert Geet.cleanups == [1]

    def test_unbind(self, capsys):
        _, rc = Sample.run(["sample", "--help"], exit = False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "--foo" in stdout
        assert "--version" not in stdout

    def test_default_main(self, capsys):
        _, rc = Sample.run(["sample"], exit = False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "No sub-command given" in stdout

        _, rc = Sample.run(["sample", "pimple"], exit = False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "Unknown sub-command 'pimple'" in stdout

        _, rc = Sample.run(["sample", "mumble"], exit = False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "main() not implemented" in stdout

    def test_lazy_subcommand(self, capsys):
        class Foo(cli.Application):
            pass

        Foo.subcommand("lazy", "test_cli.LazyLoaded")

        _, rc = Foo.run(["foo", "lazy"], exit = False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "hello world" in stdout

    def test_reset_switchattr(self):
        inst, rc = SimpleApp.run(["foo", "--bacon=81", "-e", "bar"], exit=False)
        assert rc == 0
        assert inst.eggs == "bar"

        inst, rc = SimpleApp.run(["foo", "--bacon=81"], exit=False)
        assert rc == 0
        assert inst.eggs is None

    def test_invoke(self):
        inst, rc = SimpleApp.invoke("arg1", "arg2", eggs="sunny", bacon=10, verbose=2)
        assert (inst.eggs, inst.verbose, inst.tailargs) == ("sunny", 2, ("arg1", "arg2"))

    def test_env_var(self, capsys):
        _, rc = SimpleApp.run(["arg", "--bacon=10"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "10" in stdout

        with local.env(
            PLUMBUM_TEST_BACON='20',
            PLUMBUM_TEST_EGGS='raw',
        ):
            inst, rc = SimpleApp.run(["arg"], exit=False)

        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "20" in stdout
        assert inst.eggs == 'raw'

    def test_mandatory_env_var(self, capsys):
        
        _, rc = SimpleApp.run(["arg"], exit = False)
        assert rc == 2
        stdout, stderr = capsys.readouterr()
        assert "bacon is mandatory" in stdout


@contextmanager
def send_stdin(stdin = "\n"):
    prevstdin = sys.stdin
    sys.stdin = StringIO(stdin)
    try:
        yield sys.stdin
    finally:
        sys.stdin = prevstdin

class TestTerminal:
    def test_ask(self, capsys):
        with send_stdin("\n"):
            assert ask("Do you like cats?", default = True)
        assert capsys.readouterr()[0] == "Do you like cats? [Y/n] "

        with send_stdin("\nyes"):
            assert ask("Do you like cats?")
        assert capsys.readouterr()[0] == "Do you like cats? (y/n) Invalid response, please try again\nDo you like cats? (y/n) "

    def test_choose(self, capsys):
        with send_stdin("foo\n2\n"):
            assert choose("What is your favorite color?", ["blue", "yellow", "green"]) == "yellow"
        assert capsys.readouterr()[0] == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: "

        with send_stdin("foo\n2\n"):
            assert choose("What is your favorite color?", [("blue", 10), ("yellow", 11), ("green", 12)]) == 11
        assert capsys.readouterr()[0] == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: "

        with send_stdin("foo\n\n"):
            assert choose("What is your favorite color?", ["blue", "yellow", "green"], default = "yellow") == "yellow"
        assert capsys.readouterr()[0] == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice [2]: Invalid choice, please try again\nChoice [2]: "

    def test_hexdump(self):
        data = "hello world my name is queen marry" + "A" * 66 + "foo bar"
        output = """\
000000 | 68 65 6c 6c 6f 20 77 6f 72 6c 64 20 6d 79 20 6e | hello world my n
000010 | 61 6d 65 20 69 73 20 71 75 65 65 6e 20 6d 61 72 | ame is queen mar
000020 | 72 79 41 41 41 41 41 41 41 41 41 41 41 41 41 41 | ryAAAAAAAAAAAAAA
000030 | 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41 | AAAAAAAAAAAAAAAA
*
000060 | 41 41 41 41 66 6f 6f 20 62 61 72                | AAAAfoo bar"""
        assert "\n".join(hexdump(data)) == output

    def test_progress(self, capsys):
        for i in Progress.range(4, has_output=True, timer=False):
            print('hi')
            time.sleep(.5)
        stdout, stderr = capsys.readouterr()
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
        assert stdout ==  output

