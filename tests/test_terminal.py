# -*- coding: utf-8 -*-
import sys
import time
from contextlib import contextmanager

import pytest

from plumbum.cli.terminal import Progress, ask, choose, hexdump, prompt
from plumbum.lib import StringIO

try:
    from collections import OrderedDict
except ImportError:
    try:
        from ordereddict import OrderedDict
    except ImportError:
        OrderedDict = None
needs_od = pytest.mark.skipif(
    OrderedDict is None, reason="Ordered dict not available (Py 2.6)"
)


@contextmanager
def send_stdin(stdin="\n"):
    prevstdin = sys.stdin
    sys.stdin = StringIO(stdin)
    try:
        yield sys.stdin
    finally:
        sys.stdin = prevstdin


class TestPrompt:
    def test_simple(self, capsys):
        with send_stdin("12"):
            assert prompt("Enter a random int:", type=int) == 12
        assert capsys.readouterr()[0] == "Enter a random int: "

    def test_try_twice(self, capsys):
        with send_stdin("\n13"):
            assert prompt("Enter a random int:", type=int) == 13
        assert capsys.readouterr()[0] == "Enter a random int: Enter a random int: "

    def test_str(self):
        with send_stdin("1234"):
            assert prompt("Enter a string", type=str) == "1234"

    def test_default(self, capsys):
        with send_stdin(""):
            assert prompt("Enter nothing", default="hi") == "hi"
        assert capsys.readouterr()[0] == "Enter nothing [hi]: "

    def test_typefail(self, capsys):
        with send_stdin("1.2\n13"):
            assert prompt("Enter int", type=int) == 13
        assert "try again" in capsys.readouterr()[0]

    def test_validator(self, capsys):
        with send_stdin("12\n9"):
            assert (
                prompt("Enter in range < 10", type=int, validator=lambda x: x < 10) == 9
            )
        assert "try again" in capsys.readouterr()[0]


class TestTerminal:
    def test_ask(self, capsys):
        with send_stdin("\n"):
            assert ask("Do you like cats?", default=True)
        assert capsys.readouterr()[0] == "Do you like cats? [Y/n] "

        with send_stdin("\nyes"):
            assert ask("Do you like cats?")
        assert (
            capsys.readouterr()[0]
            == "Do you like cats? (y/n) Invalid response, please try again\nDo you like cats? (y/n) "
        )

    def test_choose(self, capsys):
        with send_stdin("foo\n2\n"):
            assert (
                choose("What is your favorite color?", ["blue", "yellow", "green"])
                == "yellow"
            )
        assert (
            capsys.readouterr()[0]
            == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: "
        )

        with send_stdin("foo\n2\n"):
            assert (
                choose(
                    "What is your favorite color?",
                    [("blue", 10), ("yellow", 11), ("green", 12)],
                )
                == 11
            )
        assert (
            capsys.readouterr()[0]
            == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice: Invalid choice, please try again\nChoice: "
        )

        with send_stdin("foo\n\n"):
            assert (
                choose(
                    "What is your favorite color?",
                    ["blue", "yellow", "green"],
                    default="yellow",
                )
                == "yellow"
            )
        assert (
            capsys.readouterr()[0]
            == "What is your favorite color?\n(1) blue\n(2) yellow\n(3) green\nChoice [2]: Invalid choice, please try again\nChoice [2]: "
        )

    def test_choose_dict(self):
        with send_stdin("23\n1"):
            value = choose("Pick", dict(one="a", two="b"))
            assert value in ("a", "b")

    @needs_od
    def test_ordered_dict(self):
        dic = OrderedDict()
        dic["one"] = "a"
        dic["two"] = "b"
        with send_stdin("1"):
            value = choose("Pick", dic)
            assert value == "a"
        with send_stdin("2"):
            value = choose("Pick", dic)
            assert value == "b"

    @needs_od
    def test_choose_dict_default(self, capsys):
        dic = OrderedDict()
        dic["one"] = "a"
        dic["two"] = "b"
        with send_stdin():
            assert choose("Pick", dic, default="a") == "a"
        assert "[1]" in capsys.readouterr()[0]

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

        assert "\n".join(hexdump(StringIO(data))) == output

    def test_progress(self, capsys):
        for i in Progress.range(4, has_output=True, timer=False):
            print("hi")
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
        assert stdout == output

    def test_progress_empty(self, capsys):
        for i in Progress.range(0, has_output=True, timer=False):
            print("hi")
        stdout, stderr = capsys.readouterr()
        output = "0/0 complete"
        assert output in stdout
