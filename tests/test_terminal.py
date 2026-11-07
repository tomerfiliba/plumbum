from __future__ import annotations

import sys
from collections import OrderedDict
from contextlib import contextmanager
from io import BytesIO, StringIO
from types import SimpleNamespace

import pytest

from plumbum.cli.terminal import Progress, ask, choose, hexdump, pager, prompt
from plumbum.machines.local import LocalCommand


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
            value = choose("Pick", {"one": "a", "two": "b"})
            assert value in ("a", "b")

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

    def test_choose_dict_default(self, capsys):
        dic = OrderedDict()
        dic["one"] = "a"
        dic["two"] = "b"
        with send_stdin():
            assert choose("Pick", dic, default="a") == "a"
        assert "[1]" in capsys.readouterr()[0]

    def test_ask_eof_with_default(self):
        # Exhausted stdin (EOF) must fall back to the default, not loop forever.
        with send_stdin(""):
            assert ask("Do you like cats?", default=True) is True
        with send_stdin(""):
            assert ask("Do you like cats?", default=False) is False

    def test_ask_eof_no_default_raises(self):
        with send_stdin(""), pytest.raises(EOFError):
            ask("Do you like cats?")

    def test_choose_eof_with_default(self):
        with send_stdin(""):
            assert choose("Pick", ["blue", "yellow"], default="yellow") == "yellow"

    def test_choose_eof_no_default_raises(self):
        with send_stdin(""), pytest.raises(EOFError):
            choose("Pick", ["blue", "yellow"])

    def test_prompt_eof_with_default(self):
        with send_stdin(""):
            assert prompt("Enter", default="hi") == "hi"

    def test_prompt_eof_no_default_raises(self):
        with send_stdin(""), pytest.raises(EOFError):
            prompt("Enter", type=int)

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
        for _ in Progress.range(4, has_output=True, timer=False):
            print("hi")
        stdout, _stderr = capsys.readouterr()
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
        for _ in Progress.range(0, has_output=True, timer=False):
            print("hi")
        stdout = capsys.readouterr().out
        output = "0/0 complete"
        assert output in stdout


class TestPager:
    @pytest.mark.parametrize("encoding", ["utf-8", "latin-1", None])
    @pytest.mark.parametrize("rows_type", [str, list, iter, StringIO])
    def test_binary_stdin(self, tmp_path, mocker, encoding, rows_type):
        output = tmp_path / "pager-output"
        command = LocalCommand(sys.executable, encoding=encoding)[
            "-c",
            "import pathlib, sys; "
            "pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
            str(output),
        ]
        process = command.popen(stdout=None, stderr=None)
        popen = mocker.patch.object(type(command), "popen", return_value=process)
        reset = mocker.patch("plumbum.cli.terminal.os.system")
        rows = (
            rows_type("café\nsecond")
            if rows_type in (str, StringIO)
            else rows_type(["café", "second"])
        )
        expected = "café\n\nsecond\n" if rows_type is StringIO else "café\nsecond\n"

        try:
            pager(rows, pagercmd=command)
        finally:
            if not process.stdin.closed:
                process.stdin.close()
            process.wait()

        popen.assert_called_once_with(stdout=None, stderr=None)
        reset.assert_not_called()
        assert process.returncode == 0
        assert output.read_bytes() == expected.encode(encoding or "utf-8")
        if rows_type is StringIO:
            assert rows.closed

    def test_text_stdin(self, mocker):
        stdin = StringIO()
        write = mocker.spy(stdin, "write")
        process = SimpleNamespace(stdin=stdin, wait=mocker.Mock(), poll=lambda: 0)
        command = SimpleNamespace(popen=lambda **_kwargs: process)

        pager(["café"], pagercmd=command)

        write.assert_called_once_with("café\n")
        assert stdin.closed
        process.wait.assert_called_once_with()

    @pytest.mark.parametrize("operation", ["write", "flush"])
    def test_closed_pager(self, mocker, operation):
        stdin = mocker.Mock(spec=BytesIO)
        getattr(stdin, operation).side_effect = BrokenPipeError
        process = SimpleNamespace(stdin=stdin, wait=mocker.Mock(), poll=lambda: 0)
        command = SimpleNamespace(
            popen=lambda **_kwargs: process, _get_encoding=lambda: "utf-8"
        )
        closed = mocker.Mock()

        def rows():
            try:
                yield "café"
                pytest.fail("Rows consumed after the pager closed")
            finally:
                closed()

        pager(rows(), pagercmd=command)

        stdin.write.assert_called_once_with("café\n".encode())
        stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with()
        closed.assert_called_once_with()
