"""Regression tests for remote shell-quoting / injection holes (issue #820).

These tests exercise the command-string construction without needing a live
SSH connection: a fake session records every command passed to ``run`` and
returns canned output.
"""

from __future__ import annotations

import re

import pytest

from plumbum.machines.remote import (
    BaseRemoteMachine,
    RemoteEnv,
    _check_env_name,
)


class FakeSession:
    """Records commands and returns a fixed (rc, stdout, stderr) tuple."""

    def __init__(self, stdout: str = "") -> None:
        self.commands: list[str] = []
        self.stdout = stdout

    def run(self, cmd, retcode=0):  # noqa: ARG002
        self.commands.append(cmd)
        return (0, self.stdout, "")


class FakeRemote:
    """A stand-in for BaseRemoteMachine exposing just what we need."""

    def __init__(self, stdout: str = "") -> None:
        self._session = FakeSession(stdout)
        self.uname = "Linux"

    # borrow the real implementations under test
    expanduser = BaseRemoteMachine.expanduser
    expand = BaseRemoteMachine.expand
    _path_glob = BaseRemoteMachine._path_glob
    _path_stat = BaseRemoteMachine._path_stat


class TestCheckEnvName:
    @pytest.mark.parametrize("name", ["X", "_x", "FOO_BAR", "a1", "_"])
    def test_valid(self, name):
        assert _check_env_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "X; rm -rf ~",
            "1FOO",
            "FOO BAR",
            "FOO=BAR",
            "$(touch pwned)",
            "`id`",
            "FOO-BAR",
            "",
        ],
    )
    def test_invalid(self, name):
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            _check_env_name(name)


class TestRemoteEnvValidation:
    def _make_env(self):
        env = object.__new__(RemoteEnv)
        env.remote = FakeRemote()
        return env

    def test_setitem_rejects_injection(self):
        env = self._make_env()
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            env["X; rm -rf ~"] = "1"
        # nothing should have been sent to the session
        assert env.remote._session.commands == []

    def test_delitem_rejects_injection(self):
        env = self._make_env()
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            del env["BAD;NAME"]
        assert env.remote._session.commands == []

    def test_pop_rejects_injection(self):
        env = self._make_env()
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            env.pop("`id`")
        assert env.remote._session.commands == []


class TestExpanduser:
    def test_no_tilde_returns_unchanged(self):
        rem = FakeRemote()
        assert rem.expanduser("/abs/path") == "/abs/path"
        assert rem.expanduser("rel/path") == "rel/path"
        assert rem.expanduser("./~notfirst") == "./~notfirst"
        # the session must not be touched at all
        assert rem._session.commands == []

    def test_literal_suffix_is_not_executed(self):
        # The home dir is expanded but the dangerous suffix must round-trip
        # literally and must NOT be passed through the shell.
        rem = FakeRemote(stdout="/home/me")
        result = rem.expanduser("~/a b; rm -rf c")
        assert result == "/home/me/a b; rm -rf c"
        # only a single safe "echo ~" was run; the suffix never reached a command
        assert rem._session.commands == ["echo ~"]
        assert not any("rm -rf" in c for c in rem._session.commands)

    def test_glob_metachars_in_suffix_round_trip(self):
        rem = FakeRemote(stdout="/home/me")
        result = rem.expanduser("~/a*?$(touch x)`id`")
        assert result == "/home/me/a*?$(touch x)`id`"
        assert rem._session.commands == ["echo ~"]

    def test_named_user_expands(self):
        rem = FakeRemote(stdout="/home/john")
        result = rem.expanduser("~john/sub dir")
        assert result == "/home/john/sub dir"
        assert rem._session.commands == ["echo ~john"]

    def test_unsafe_username_left_untouched(self):
        # A "~user" whose user part is not a safe login name is not expanded
        # (mirroring os.path.expanduser returning the input unchanged), and is
        # never sent to the shell.
        rem = FakeRemote()
        expr = "~ev;il/foo"
        assert rem.expanduser(expr) == expr
        assert rem._session.commands == []


class TestPathGlobQuoting:
    def test_non_recursive_quotes_directory(self):
        rem = FakeRemote(stdout="")
        rem._path_glob("/tmp/a b; rm -rf c", "*.txt")
        cmd = rem._session.commands[0]
        # directory is shquoted and there is no echo-of-unquoted-var
        assert "'/tmp/a b; rm -rf c'" in cmd
        assert "echo $fn" not in cmd
        assert cmd.startswith("find ")

    def test_non_recursive_matches_and_preserves_whitespace(self):
        # find returns full paths; whitespace in matched names must survive.
        out = "/dir/a b.txt\n/dir/c.txt\n/dir/skip.log\n"
        rem = FakeRemote(stdout=out)
        matches = rem._path_glob("/dir", "*.txt")
        assert matches == ["/dir/a b.txt", "/dir/c.txt"]

    def test_recursive_still_quotes_directory(self):
        rem = FakeRemote(stdout="")
        rem._path_glob("/tmp/x;y", "**/*.py")
        cmd = rem._session.commands[0]
        assert "'/tmp/x;y'" in cmd
        assert cmd.startswith("find ")


class TestSshPopenQuoting:
    def test_cwd_and_env_quoted(self):
        # Build the command line the way SshMachine.popen does, without a
        # connection, by driving the quoting logic directly.
        from plumbum.commands import shquote

        cwd = "/a dir; rm -rf x"
        assert shquote(cwd) == "'/a dir; rm -rf x'"
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            _check_env_name("BAD;NAME")
        assert _check_env_name("GOOD_NAME") == "GOOD_NAME"


def test_env_name_regex_anchored():
    # guard against partial matches sneaking through
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", "OK_1")
    with pytest.raises(ValueError, match="Invalid"):
        _check_env_name("OK\nrm -rf /")
