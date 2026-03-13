from __future__ import annotations

import io
import os
import pickle
import types

from plumbum.commands import daemon_launcher


class _StdinWithPayload:
    def __init__(self, payload: bytes):
        self.buffer = io.BytesIO(payload)


class _CommandSuccess:
    last_kwargs = None

    def __init__(self):
        self.kwargs = None

    def popen(self, **kwargs):
        self.kwargs = kwargs
        _CommandSuccess.last_kwargs = kwargs
        return types.SimpleNamespace(pid=43210)


class _CommandFail:
    def popen(self, **kwargs):
        raise RuntimeError("boom")


def _make_payload(
    command, cwd: str, stdout_path: str, stderr_path: str, append: bool
) -> bytes:
    return pickle.dumps(
        {
            "command": command,
            "cwd": cwd,
            "stdout": stdout_path,
            "stderr": stderr_path,
            "append": append,
        }
    )


def test_main_returns_2_when_missing_fd(monkeypatch) -> None:
    monkeypatch.setattr(daemon_launcher.sys, "argv", ["daemon_launcher.py"])

    assert daemon_launcher._main() == 2


def test_main_success_writes_pid_and_uses_expected_popen_kwargs(
    monkeypatch, tmp_path
) -> None:
    read_fd, write_fd = os.pipe()
    command = _CommandSuccess()

    payload = _make_payload(
        command,
        cwd=str(tmp_path),
        stdout_path=str(tmp_path / "stdout.log"),
        stderr_path=str(tmp_path / "stderr.log"),
        append=False,
    )

    monkeypatch.setattr(
        daemon_launcher.sys, "argv", ["daemon_launcher.py", str(write_fd)]
    )
    monkeypatch.setattr(daemon_launcher.sys, "stdin", _StdinWithPayload(payload))

    try:
        rc = daemon_launcher._main()
        response = os.read(read_fd, 1024)
    finally:
        os.close(read_fd)

    assert rc == 0
    assert response == b"43210"
    kwargs = _CommandSuccess.last_kwargs
    assert kwargs is not None
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["close_fds"] is True
    assert kwargs["start_new_session"] is True
    assert isinstance(kwargs["stdin"], int)
    assert isinstance(kwargs["stdout"], int)
    assert isinstance(kwargs["stderr"], int)


def test_main_exception_writes_traceback(monkeypatch, tmp_path) -> None:
    read_fd, write_fd = os.pipe()
    payload = _make_payload(
        _CommandFail(),
        cwd=str(tmp_path),
        stdout_path=str(tmp_path / "stdout.log"),
        stderr_path=str(tmp_path / "stderr.log"),
        append=True,
    )

    monkeypatch.setattr(
        daemon_launcher.sys, "argv", ["daemon_launcher.py", str(write_fd)]
    )
    monkeypatch.setattr(daemon_launcher.sys, "stdin", _StdinWithPayload(payload))

    try:
        rc = daemon_launcher._main()
        response = os.read(read_fd, 65536)
    finally:
        os.close(read_fd)

    assert rc == 1
    assert b"RuntimeError: boom" in response
