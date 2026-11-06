from __future__ import annotations

import pytest

from plumbum import ProcessExecutionError, local
from plumbum._testtools import skip_on_windows
from plumbum.machines.session import ShellSession, SSHCommsError

pytestmark = [skip_on_windows, pytest.mark.timeout(10)]


@pytest.mark.parametrize(
    ("encoding", "word", "command_object"),
    [
        ("utf-8", "plain", False),
        ("utf-8", "café", False),
        ("latin-1", "café", False),
        ("utf-8", "café", True),
    ],
)
def test_session_failure_displays_command(encoding, word, command_object):
    script = f"printf '%s' '{word}'; printf '%s' 'error-{word}' >&2; false"
    command = local["sh"]["-c", script] if command_object else script
    with (
        ShellSession(local["sh"].popen(), encoding=encoding) as session,
        pytest.raises(ProcessExecutionError) as raised,
    ):
        session.run(command)

    error = raised.value
    assert error.retcode == 1
    assert error.stdout == word
    assert error.stderr == f"error-{word}"
    assert isinstance(error.argv, list)
    assert len(error.argv) == 1
    assert isinstance(error.argv[0], str)
    assert word in error.argv[0]
    command_line = str(error).splitlines()[1]
    assert command_line.startswith("Command line: | ")
    assert "printf" in command_line
    assert word in command_line


def test_session_success_keeps_string_and_command_object_results():
    with local.session() as session:
        assert session.run("printf plain") == (0, "plain", "")
        assert session.run(local["printf"]["object"]) == (0, "object", "")


def test_direct_popen_and_command_failure_keep_args():
    command = local["sh"]["-c", "printf out; printf err >&2; false"]
    with command.popen() as proc:
        assert proc.args == command.formulate()
        stdout, stderr = proc.communicate()
        assert proc.returncode == 1
    assert stdout == b"out"
    assert stderr == b"err"

    with pytest.raises(ProcessExecutionError) as raised:
        command()

    error = raised.value
    assert error.argv == command.formulate()
    assert error.retcode == 1
    assert error.stdout == "out"
    assert error.stderr == "err"
    assert "printf" in str(error).splitlines()[1]


def test_session_eof_keeps_communication_error_command():
    with local.session() as session, pytest.raises(SSHCommsError) as raised:
        session.run("exit 3")

    error = raised.value
    assert error.retcode == 3
    assert [arg.strip() for arg in error.argv] == ["exit 3"]
    assert "SSH communication failed" in str(error)
