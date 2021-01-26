# -*- coding: utf-8 -*-
import sys

import pytest

from plumbum import cli, local
from plumbum.cli.terminal import get_terminal_size


class SimpleApp(cli.Application):
    @cli.switch(["a"])
    def spam(self):
        print("!!a")

    @cli.switch(
        ["b", "bacon"], argtype=int, mandatory=True, envname="PLUMBUM_TEST_BACON"
    )
    def bacon(self, param):
        """give me some bacon"""
        print("!!b", param)

    eggs = cli.SwitchAttr(
        ["e"], str, help="sets the eggs attribute", envname="PLUMBUM_TEST_EGGS"
    )
    cheese = cli.Flag(["--cheese"], help="cheese, please")
    chives = cli.Flag(["--chives"], help="chives, instead")
    verbose = cli.CountOf(["v"], help="increases the verbosity level")
    benedict = cli.CountOf(
        ["--benedict"],
        help="""a very long help message with lots of
        useless information that nobody would ever want to read, but heck, we need to test
        text wrapping in help messages as well""",
    )

    csv = cli.SwitchAttr(["--csv"], cli.Set("MIN", "MAX", int, csv=True))
    num = cli.SwitchAttr(["--num"], cli.Set("MIN", "MAX", int))

    def main(self, *args):
        old = self.eggs
        self.eggs = "lalala"
        self.eggs = old
        self.tailargs = args


class PositionalApp(cli.Application):
    def main(self, one):
        print("Got", one)


class Geet(cli.Application):
    debug = cli.Flag("--debug")
    cleanups = []

    def main(self):
        del self.cleanups[:]
        print("hi this is geet main")

    def cleanup(self, retcode):
        self.cleanups.append(1)
        print("geet cleaning up with rc = {}".format(retcode))


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
        print("geet commit cleaning up with rc = {}".format(retcode))


class Sample(cli.Application):
    DESCRIPTION = "A sample cli application"
    DESCRIPTION_MORE = """
    ABC This is just a sample help text typed with a Dvorak keyboard.
 Although this paragraph is not left or right justified
      in source, we expect it to appear
   formatted nicely on the output, maintaining the indentation of the first line.

  DEF this one has a different indentation.

Let's test that list items are not combined as paragraphs.

   - Item 1
  GHI more text for item 1, which may be very very very very very very long and even more long and long and long to
     prove that we can actually wrap list items as well.
   - Item 2 and this is
     some text for item 2
   - Item 3

List items with invisible bullets should be printed without the bullet.

 /XYZ Invisible 1
 /Invisible 2

  * Star 1
  * Star 2

  Last paragraph can fill more than one line on the output as well. So many features is bound to cause lots of bugs.
  Oh well...
    """

    foo = cli.SwitchAttr("--foo")


Sample.unbind_switches("--version")


class Mumble(cli.Application):
    pass


Sample.subcommand("mumble", Mumble)


class LazyLoaded(cli.Application):
    def main(self):
        print("hello world")


class AppA(cli.Application):
    @cli.switch(["--one"])
    def one(self):
        pass

    two = cli.SwitchAttr(["--two"])


class AppB(AppA):
    @cli.switch(["--three"])
    def three(self):
        pass

    four = cli.SwitchAttr(["--four"])

    def main(self):
        pass


# Testing #363
class TestInheritedApp:
    def test_help(self, capsys):
        _, rc = AppB.run(["AppB", "-h"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "--one" in stdout
        assert "--two" in stdout
        assert "--three" in stdout
        assert "--four" in stdout


class TestCLI:
    def test_meta_switches(self):
        _, rc = SimpleApp.run(["foo", "-h"], exit=False)
        assert rc == 0
        _, rc = SimpleApp.run(["foo", "--version"], exit=False)
        assert rc == 0

    def test_okay(self):
        _, rc = SimpleApp.run(["foo", "--bacon=81"], exit=False)
        assert rc == 0

        inst, rc = SimpleApp.run(
            [
                "foo",
                "--bacon=81",
                "-a",
                "-v",
                "-e",
                "7",
                "-vv",
                "--",
                "lala",
                "-e",
                "7",
            ],
            exit=False,
        )
        assert rc == 0
        assert inst.eggs == "7"

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--csv=100"], exit=False)
        assert rc == 0

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--csv=MAX,MIN,100"], exit=False)
        assert rc == 0

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=100"], exit=False)
        assert rc == 0

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=MAX"], exit=False)
        assert rc == 0

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=MIN"], exit=False)
        assert rc == 0

    def test_failures(self):
        _, rc = SimpleApp.run(["foo"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--csv=xx"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--csv=xx"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=MOO"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=MIN,MAX"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=81", "--num=10.5"], exit=False)
        assert rc == 2

        _, rc = SimpleApp.run(["foo", "--bacon=hello"], exit=False)
        assert rc == 2

    # Testing #371
    def test_extra_args(self, capsys):

        _, rc = PositionalApp.run(["positionalapp"], exit=False)
        assert rc != 0
        stdout, stderr = capsys.readouterr()
        assert "Expected at least" in stdout

        _, rc = PositionalApp.run(["positionalapp", "one"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()

        _, rc = PositionalApp.run(["positionalapp", "one", "two"], exit=False)
        assert rc != 0
        stdout, stderr = capsys.readouterr()
        assert "Expected at most" in stdout

    def test_subcommands(self):
        _, rc = Geet.run(["geet", "--debug"], exit=False)
        assert rc == 0
        assert Geet.cleanups == [1]
        _, rc = Geet.run(["geet", "--debug", "add", "foo.txt", "bar.txt"], exit=False)
        assert rc == ("adding", ("foo.txt", "bar.txt"))
        assert Geet.cleanups == [1]
        _, rc = Geet.run(["geet", "--debug", "commit"], exit=False)
        assert rc == "committing in debug"
        assert Geet.cleanups == [2, 1]
        _, rc = Geet.run(["geet", "--help"], exit=False)
        assert rc == 0
        _, rc = Geet.run(["geet", "commit", "--help"], exit=False)
        assert rc == 0
        assert Geet.cleanups == [1]

    def test_help_all(self, capsys):
        _, rc = Geet.run(["geet", "--help-all"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "--help-all" in stdout
        assert "geet add" in stdout
        assert "geet commit" in stdout

    def test_unbind(self, capsys):
        _, rc = Sample.run(["sample", "--help"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "--foo" in stdout
        assert "--version" not in stdout

    def test_description(self, capsys):
        _, rc = Sample.run(["sample", "--help"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        cols, _ = get_terminal_size()

        if cols < 9:
            # Terminal is too narrow to test
            pass
        else:
            # Paragraph indentation should be preserved
            assert "    ABC" in stdout
            assert "  DEF" in stdout
            assert "   - Item" in stdout
            # List items should not be combined into paragraphs
            assert "  * Star 2"
            # Lines of the same list item should be combined. (The right-hand expression of the 'or' operator
            # below is for when the terminal is too narrow, causing "GHI" to be wrapped to the next line.)
            assert "  GHI" not in stdout or "     GHI" in stdout
            # List item with invisible bullet should be indented without the bullet
            assert " XYZ" in stdout

    def test_default_main(self, capsys):
        _, rc = Sample.run(["sample"], exit=False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "No sub-command given" in stdout

        _, rc = Sample.run(["sample", "pimple"], exit=False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "Unknown sub-command 'pimple'" in stdout

        _, rc = Sample.run(["sample", "mumble"], exit=False)
        assert rc == 1
        stdout, stderr = capsys.readouterr()
        assert "main() not implemented" in stdout

    def test_lazy_subcommand(self, capsys):
        class Foo(cli.Application):
            pass

        Foo.subcommand("lazy", "test_cli.LazyLoaded")

        _, rc = Foo.run(["foo", "lazy"], exit=False)
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
        assert (inst.eggs, inst.verbose, inst.tailargs) == (
            "sunny",
            2,
            ("arg1", "arg2"),
        )

    def test_env_var(self, capsys):
        _, rc = SimpleApp.run(["arg", "--bacon=10"], exit=False)
        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "10" in stdout

        with local.env(
            PLUMBUM_TEST_BACON="20",
            PLUMBUM_TEST_EGGS="raw",
        ):
            inst, rc = SimpleApp.run(["arg"], exit=False)

        assert rc == 0
        stdout, stderr = capsys.readouterr()
        assert "20" in stdout
        assert inst.eggs == "raw"

    def test_mandatory_env_var(self, capsys):

        _, rc = SimpleApp.run(["arg"], exit=False)
        assert rc == 2
        stdout, stderr = capsys.readouterr()
        assert "bacon is mandatory" in stdout

    def test_partial_switches(self, capsys):
        app = SimpleApp
        app.ALLOW_ABBREV = True
        inst, rc = app.run(["foo", "--bacon=2", "--ch"], exit=False)
        stdout, stderr = capsys.readouterr()
        assert "Ambiguous partial switch" in stdout
        assert rc == 2

        inst, rc = app.run(["foo", "--bacon=2", "--chee"], exit=False)
        assert rc == 0
        assert inst.cheese is True
        assert inst.chives is False
