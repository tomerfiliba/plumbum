from __future__ import annotations

import signal

import pytest

from plumbum import cli, local
from plumbum.cli.switches import SwitchInfo
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

    csv = cli.SwitchAttr(
        ["--csv"], cli.Set("MIN", "MAX", int, csv=True, all_markers={"all"})
    )
    num = cli.SwitchAttr(["--num"], cli.Set("MIN", "MAX", int))

    def main(self, *args):
        old = self.eggs
        self.eggs = "lalala"
        self.eggs = old
        self.tailargs = args

        print(self.csv)


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
        print(f"geet cleaning up with rc = {retcode}")


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
        return "committing"

    def cleanup(self, retcode):
        self.parent.cleanups.append(2)
        print(f"geet commit cleaning up with rc = {retcode}")


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
        stdout, _ = capsys.readouterr()
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

    def test_okay(self, capsys):
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

        capsys.readouterr()
        _, rc = SimpleApp.run(["foo", "--bacon=81", "--csv=all,100"], exit=False)
        assert rc == 0
        output = capsys.readouterr()
        assert "min" in output.out
        assert "max" in output.out
        assert "100" in output.out

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
        stdout, _ = capsys.readouterr()
        assert "Expected at least" in stdout

        _, rc = PositionalApp.run(["positionalapp", "one"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()

        _, rc = PositionalApp.run(["positionalapp", "one", "two"], exit=False)
        assert rc != 0
        stdout, _ = capsys.readouterr()
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
        stdout, _ = capsys.readouterr()
        assert "--help-all" in stdout
        assert "geet add" in stdout
        assert "geet commit" in stdout

    def test_unbind(self, capsys):
        _, rc = Sample.run(["sample", "--help"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()
        assert "--foo" in stdout
        assert "--version" not in stdout

    def test_description(self, capsys):
        _, rc = Sample.run(["sample", "--help"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()
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
            assert "  * Star 2" in stdout
            # Lines of the same list item should be combined. (The right-hand expression of the 'or' operator
            # below is for when the terminal is too narrow, causing "GHI" to be wrapped to the next line.)
            assert "  GHI" not in stdout or "     GHI" in stdout
            # List item with invisible bullet should be indented without the bullet
            assert " XYZ" in stdout

    def test_default_main(self, capsys):
        _, rc = Sample.run(["sample"], exit=False)
        assert rc == 1
        stdout, _ = capsys.readouterr()
        assert "No sub-command given" in stdout

        _, rc = Sample.run(["sample", "pimple"], exit=False)
        assert rc == 1
        stdout, _ = capsys.readouterr()
        assert "Unknown sub-command 'pimple'" in stdout

        _, rc = Sample.run(["sample", "mumble"], exit=False)
        assert rc == 1
        stdout, _ = capsys.readouterr()
        assert "main() not implemented" in stdout

    def test_lazy_subcommand(self, capsys):
        class Foo(cli.Application):
            pass

        Foo.subcommand("lazy", "test_cli.LazyLoaded")

        _, rc = Foo.run(["foo", "lazy"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()
        assert "hello world" in stdout

    def test_multiple_subcommand_names(self):
        """Test that a single subapp can be assigned to multiple subcommand names"""

        class MainApp(cli.Application):
            pass

        @MainApp.subcommand("new-name")
        @MainApp.subcommand("legacy-name")
        class SubApp(cli.Application):
            def main(self):
                return "SubApp executed"

        # Test that both names are registered
        _, rc = MainApp.run(["mainapp", "new-name"], exit=False)
        assert rc == "SubApp executed"

        _, rc = MainApp.run(["mainapp", "legacy-name"], exit=False)
        assert rc == "SubApp executed"

        # Test using loop registration (v2 style)
        class AnotherApp(cli.Application):
            pass

        class AnotherSub(cli.Application):
            def main(self):
                return "AnotherSub executed"

        for name in ("alias1", "alias2", "alias3"):
            AnotherApp.subcommand(name, AnotherSub)

        _, rc = AnotherApp.run(["anotherapp", "alias1"], exit=False)
        assert rc == "AnotherSub executed"

        _, rc = AnotherApp.run(["anotherapp", "alias2"], exit=False)
        assert rc == "AnotherSub executed"

        _, rc = AnotherApp.run(["anotherapp", "alias3"], exit=False)
        assert rc == "AnotherSub executed"

    def test_reset_switchattr(self):
        inst, rc = SimpleApp.run(["foo", "--bacon=81", "-e", "bar"], exit=False)
        assert rc == 0
        assert inst.eggs == "bar"

        inst, rc = SimpleApp.run(["foo", "--bacon=81"], exit=False)
        assert rc == 0
        assert inst.eggs is None

    def test_invoke(self):
        inst, _ = SimpleApp.invoke("arg1", "arg2", eggs="sunny", bacon=10, verbose=2)
        assert (inst.eggs, inst.verbose, inst.tailargs) == (
            "sunny",
            2,
            ("arg1", "arg2"),
        )

    def test_invoke_flag(self):
        # Test that Flag kwargs work correctly with invoke()
        # When debug=False, flag should remain False (not toggled)
        inst, _ = Geet.invoke(debug=False)
        assert inst.debug is False

        # When debug=True, flag should be True
        inst, _ = Geet.invoke(debug=True)
        assert inst.debug is True

        # When no argument, flag should use default (False)
        inst, _ = Geet.invoke()
        assert inst.debug is False

    def test_env_var(self, capsys):
        _, rc = SimpleApp.run(["arg", "--bacon=10"], exit=False)
        assert rc == 0
        stdout, _ = capsys.readouterr()
        assert "10" in stdout

        with local.env(
            PLUMBUM_TEST_BACON="20",
            PLUMBUM_TEST_EGGS="raw",
        ):
            inst, rc = SimpleApp.run(["arg"], exit=False)

        assert rc == 0
        stdout, _ = capsys.readouterr()
        assert "20" in stdout
        assert inst.eggs == "raw"

    def test_mandatory_env_var(self, capsys):
        _, rc = SimpleApp.run(["arg"], exit=False)
        assert rc == 2
        stdout, _ = capsys.readouterr()
        assert "bacon is mandatory" in stdout

    def test_partial_switches(self, capsys):
        app = SimpleApp
        app.ALLOW_ABBREV = True
        inst, rc = app.run(["foo", "--bacon=2", "--ch"], exit=False)
        stdout, _stderr = capsys.readouterr()
        assert "Ambiguous partial switch" in stdout
        assert rc == 2

        inst, rc = app.run(["foo", "--bacon=2", "--chee"], exit=False)
        assert rc == 0
        assert inst.cheese is True
        assert inst.chives is False

    def test_help_pipe_no_broken_pipe(self, tmp_path):
        """Test that piping help output doesn't raise BrokenPipeError"""
        import subprocess
        import sys

        # Create a test script file that uses an app with subcommands
        test_script_file = tmp_path / "test_app.py"
        test_script_file.write_text(
            f"""
import sys
sys.path.insert(0, {str(local.cwd)!r})
from plumbum.cli import Application, Flag

class TestApp(Application):
    debug = Flag(['debug', 'd'])

    def main(self):
        print(f"{{self.debug=}}")

@TestApp.subcommand("dothing")
class ThingDoer(Application):
    def main(self):
        print("Doing the thing!")

if __name__ == '__main__':
    TestApp()
"""
        )

        # Run the script piped to head - this should not raise BrokenPipeError
        result = subprocess.run(
            f"{sys.executable} {test_script_file} -h | head -5",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(local.cwd),
            check=False,
        )

        # The command should exit cleanly (return code 0)
        assert result.returncode == 0, (
            f"Non-zero return code: {result.returncode}, stderr: {result.stderr}"
        )
        # Output should contain help text
        assert "Usage:" in result.stdout, (
            f"Help output missing 'Usage:', got: {result.stdout}"
        )
        # No BrokenPipeError should be in stderr
        assert "BrokenPipeError" not in result.stderr, (
            f"BrokenPipeError in stderr: {result.stderr}"
        )
        # No traceback should be in stderr
        assert "Traceback" not in result.stderr, f"Traceback in stderr: {result.stderr}"

    @pytest.mark.skipif(not hasattr(signal, "SIGPIPE"), reason="requires SIGPIPE")
    def test_broken_pipe_at_shutdown_flush(self, tmp_path):
        """Output still buffered when the reader is gone must not print
        'Exception ignored ... BrokenPipeError' at interpreter shutdown."""
        import subprocess
        import sys

        script = tmp_path / "straggler.py"
        script.write_text(
            f"""
import sys, time
sys.path.insert(0, {str(local.cwd)!r})
from plumbum.cli import Application

class App(Application):
    def main(self):
        print("1\\n2\\n3\\n4\\n5", flush=True)
        time.sleep(0.5)  # let head exit
        print("straggler")  # stays in the buffer until shutdown

if __name__ == '__main__':
    App.run()
"""
        )
        result = subprocess.run(
            f"{sys.executable} {script} | head -5",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stderr == ""

    @pytest.mark.skipif(not hasattr(signal, "SIGPIPE"), reason="requires SIGPIPE")
    def test_run_keeps_sigpipe_disposition(self):
        # SIG_DFL would make a socket send() to a closed peer kill the whole
        # process (e.g. an rpyc server) instead of raising BrokenPipeError.
        before = signal.getsignal(signal.SIGPIPE)
        try:
            _, rc = SimpleApp.run(["foo", "--bacon=2"], exit=False)
        finally:
            after = signal.getsignal(signal.SIGPIPE)
            signal.signal(signal.SIGPIPE, before)
        assert rc == 0
        assert after == before

    def test_run_handles_broken_pipe(self):
        class BrokenApp(cli.Application):
            def main(self):
                raise BrokenPipeError

        _, rc = BrokenApp.run(["app"], exit=False)
        assert rc == 1


class ExcludesApp(cli.Application):
    alpha = cli.Flag("--alpha")
    beta = cli.Flag("--beta", excludes=["--alpha"])

    def main(self):
        pass


class RequiresApp(cli.Application):
    alpha = cli.Flag("--alpha")
    beta = cli.Flag("--beta", requires=["--alpha"])

    def main(self):
        pass


class TestSwitchCombinations:
    """``requires=``/``excludes=`` switch combinations.

    Regression test for #816: validating these put ``SwitchInfo`` objects into a
    set, which crashed with ``TypeError: unhashable type: 'SwitchInfo'`` after
    ``SwitchInfo`` became a (value-comparing, therefore unhashable) dataclass.
    """

    def test_excludes_runs_when_not_conflicting(self):
        _, rc = ExcludesApp.run(["app", "--beta"], exit=False)
        assert rc == 0

    def test_excludes_rejects_conflicting_switches(self, capsys):
        _, rc = ExcludesApp.run(["app", "--alpha", "--beta"], exit=False)
        assert rc == 2
        assert "invalid" in capsys.readouterr()[0]

    def test_requires_runs_when_satisfied(self):
        _, rc = RequiresApp.run(["app", "--alpha", "--beta"], exit=False)
        assert rc == 0

    def test_requires_rejects_when_dependency_missing(self, capsys):
        _, rc = RequiresApp.run(["app", "--beta"], exit=False)
        assert rc == 2
        assert "missing" in capsys.readouterr()[0]

    def test_switchinfo_is_hashable(self):
        # The set membership above only works if SwitchInfo is hashable; the
        # list fields mean it can only be hashed by identity, not by value.
        info = SwitchInfo(
            names=["--x"],
            envname=None,
            argtype=None,
            list=False,
            func=lambda: None,
            mandatory=False,
            overridable=False,
            group="Switches",
            requires=[],
            excludes=[],
            argname="VALUE",
            help=None,
        )
        assert isinstance(hash(info), int)


class AbbrevApp(cli.Application):
    ALLOW_ABBREV = True

    foo = cli.Flag("--foo")
    foobar = cli.Flag("--foobar")
    verbose = cli.Flag("--verbose")

    def main(self, *args):
        self.tailargs = args


class TestAbbrev:
    def test_exact_match_wins_over_abbreviation(self):
        # --foo is an exact switch name; it must not be rejected as an
        # ambiguous prefix of --foobar.
        inst, rc = AbbrevApp.run(["app", "--foo"], exit=False)
        assert rc == 0
        assert inst.foo is True
        assert inst.foobar is False

    def test_ambiguous_partial_still_errors(self, capsys):
        _, rc = AbbrevApp.run(["app", "--foob"], exit=False)
        # --foob is unambiguous (only --foobar), should succeed
        assert rc == 0
        _, rc = AbbrevApp.run(["app", "--fo"], exit=False)
        assert rc == 2
        assert "Ambiguous partial switch" in capsys.readouterr()[0]


class TestFlagEquals:
    def test_flag_with_value_errors(self, capsys):
        # A no-argument flag given --verbose=yes must not leak '=yes' into the
        # positional args; it should raise a clear error.
        _inst, rc = AbbrevApp.run(["app", "--verbose=yes"], exit=False)
        assert rc == 2
        assert "does not take an argument" in capsys.readouterr()[0]


class BadRequiresApp(cli.Application):
    alpha = cli.Flag("--alpha", requires=["--nope"])

    def main(self):
        pass


class BadExcludesApp(cli.Application):
    alpha = cli.Flag("--alpha", excludes=["--nope"])

    def main(self):
        pass


class TestBadRequiresExcludes:
    def test_unknown_requires_raises_switch_error(self, capsys):
        _, rc = BadRequiresApp.run(["app", "--alpha"], exit=False)
        assert rc == 2
        out = capsys.readouterr()[0]
        assert "nope" in out
        assert "unknown switch" in out.lower()

    def test_unknown_excludes_raises_switch_error(self, capsys):
        _, rc = BadExcludesApp.run(["app", "--alpha"], exit=False)
        assert rc == 2
        out = capsys.readouterr()[0]
        assert "nope" in out
        assert "unknown switch" in out.lower()


class TestHelpAllDoesNotCorruptSharedSwitchInfo:
    def test_helpall_leaves_shared_switchinfo_group_unchanged(self, capsys):
        # Regression: helpall used to mutate the shared SwitchInfo objects that
        # live on the function objects, permanently corrupting every later
        # --help render in the process.
        before = cli.Application.help._switch_info.group
        _, rc = Geet.run(["geet", "--help-all"], exit=False)
        assert rc == 0
        capsys.readouterr()
        after = cli.Application.help._switch_info.group
        assert before == after == "Meta-switches"
