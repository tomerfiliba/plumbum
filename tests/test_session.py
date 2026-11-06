from __future__ import annotations

import io

import pytest

from plumbum.machines.session import IncorrectLogin, MarkedPipe, SessionPopen


class ExitsAfterPolls:
    returncode = None

    def __init__(self, polls: int, returncode: int) -> None:
        self.polls = polls
        self.exit_code = returncode

    def poll(self) -> int | None:
        self.polls -= 1
        if self.polls <= 0:
            self.returncode = self.exit_code
        return self.returncode


def test_login_failure_detected_when_exit_lags_eof():
    popen = SessionPopen(
        ExitsAfterPolls(polls=3, returncode=5),  # type: ignore[arg-type]
        b"true",
        False,
        io.BytesIO(),
        MarkedPipe(io.BytesIO(), "marker"),
        MarkedPipe(io.BytesIO(), "marker"),
        "utf-8",
        host="localhost",
    )

    with pytest.raises(IncorrectLogin):
        popen.communicate()
