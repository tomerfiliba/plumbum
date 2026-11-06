from __future__ import annotations

import os
from contextlib import ExitStack

import pytest

from plumbum.commands import daemons


@pytest.fixture
def opened_streams(monkeypatch):
    streams = []

    with ExitStack() as cleanup:

        def tracked_open(*args, **kwargs):
            stream = cleanup.enter_context(open(*args, **kwargs))
            streams.append(stream)
            return stream

        monkeypatch.setattr(daemons, "open", tracked_open, raising=False)
        yield streams


@pytest.mark.parametrize(
    ("failing_stream", "opened_count"), [("stdout", 1), ("stderr", 2)]
)
def test_win32_daemonize_closes_streams_on_open_failure(
    failing_stream, opened_count, opened_streams, tmp_path, mocker
):
    missing_path = str(tmp_path / "missing" / "output.log")
    paths = {
        "stdout": str(tmp_path / "stdout.log"),
        "stderr": str(tmp_path / "stderr.log"),
    }
    paths[failing_stream] = missing_path
    command = mocker.Mock()

    with pytest.raises(FileNotFoundError) as exc_info:
        daemons.win32_daemonize(command, str(tmp_path), **paths)

    command.popen.assert_not_called()
    assert exc_info.value.filename == missing_path
    assert len(opened_streams) == opened_count
    # Keep the exception and streams alive so garbage collection cannot hide
    # a failure to close handles acquired before the failing open().
    assert all(stream.closed for stream in opened_streams)


@pytest.mark.parametrize("append", [False, True])
@pytest.mark.parametrize("spawn_fails", [False, True])
@pytest.mark.parametrize("shared_output", [False, True])
def test_win32_daemonize_closes_streams_after_popen(
    append, spawn_fails, shared_output, opened_streams, tmp_path, monkeypatch, mocker
):
    # Supply Windows flags on other platforms; no process is actually spawned.
    monkeypatch.setattr(
        daemons.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False
    )
    monkeypatch.setattr(daemons.subprocess, "DETACHED_PROCESS", 8, raising=False)
    stdout = tmp_path / "stdout.log"
    stderr = stdout if shared_output else tmp_path / "stderr.log"
    stdout.write_text("existing", encoding="utf-8")
    stderr.write_text("existing", encoding="utf-8")
    process = object()
    spawn_error = OSError("spawn failed")

    def popen(**kwargs):
        assert kwargs["cwd"] == str(tmp_path)
        assert kwargs["creationflags"] == 520
        for name, stream in zip(("stdin", "stdout", "stderr"), opened_streams):
            assert kwargs[name] == stream.fileno()
            os.fstat(kwargs[name])
        if spawn_fails:
            raise spawn_error
        return process

    command = mocker.Mock()
    command.popen.side_effect = popen
    kwargs = {
        "stdout": str(stdout),
        "stderr": None if shared_output else str(stderr),
        "append": append,
    }
    if spawn_fails:
        with pytest.raises(OSError, match="spawn failed") as exc_info:
            daemons.win32_daemonize(command, str(tmp_path), **kwargs)
        assert exc_info.value is spawn_error
    else:
        assert daemons.win32_daemonize(command, str(tmp_path), **kwargs) is process

    command.popen.assert_called_once()
    assert len(opened_streams) == 3
    assert all(stream.closed for stream in opened_streams)
    expected = "existing" if append else ""
    assert stdout.read_text(encoding="utf-8") == expected
    assert stderr.read_text(encoding="utf-8") == expected
