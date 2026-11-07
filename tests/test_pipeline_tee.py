from __future__ import annotations

import sys

import pytest

from plumbum import TEE, ProcessExecutionError, local
from plumbum.lib import IS_WIN32

pytestmark = pytest.mark.skipif(IS_WIN32, reason="TEE uses select on process pipes")

TOKENS = ("é", "☃", "😀")


def tee_pipeline(stages, repeats, failed_stage=None):
    command = None
    for stage in range(stages):
        # Bound a broken implementation's backpressure deadlock without leaving
        # children behind when the regression fails.
        script = (
            "import signal, sys; signal.alarm(10); "
            f"sys.stderr.write({TOKENS[stage]!r} * {repeats}); sys.stderr.flush(); "
            + ("data = 'payload'" if stage == 0 else "data = sys.stdin.read()")
            + "; sys.stdout.write(data); sys.stdout.flush(); "
            + f"sys.exit({3 if stage == failed_stage else 0})"
        )
        child = local[sys.executable]["-X", "utf8", "-c", script]
        command = child if command is None else command | child
    return command


@pytest.mark.parametrize("stages", [1, 2, 3])
@pytest.mark.parametrize("repeats", [1, 131_073])
@pytest.mark.parametrize("buffered", [True, False])
def test_pipeline_tee_drains_every_stderr(stages, repeats, buffered, capsys):
    result = tee_pipeline(stages, repeats).run_tee(buffered=buffered)

    assert result[:2] == (0, "payload")
    captured = capsys.readouterr()
    assert captured.out == result[1]
    assert captured.err == result[2]
    assert len(result[2]) == stages * repeats
    for token in TOKENS[:stages]:
        assert result[2].count(token) == repeats


@pytest.mark.parametrize("failed_stage", [0, 1, 2])
def test_pipeline_tee_allowed_failure(failed_stage, capsys):
    result = tee_pipeline(3, 1, failed_stage).run_tee(retcode=None)

    assert result[:2] == (3, "payload")
    captured = capsys.readouterr()
    assert captured.out == "payload"
    assert captured.err == result[2]
    assert sorted(result[2]) == sorted(TOKENS)


def test_pipeline_tee_unexpected_failure(capsys):
    with pytest.raises(ProcessExecutionError) as error:
        tee_pipeline(3, 1, failed_stage=0) & TEE

    assert error.value.retcode == 3
    captured = capsys.readouterr()
    assert captured.out == "payload"
    assert sorted(captured.err) == sorted(TOKENS)


def test_pipeline_tee_preserves_stderr_redirection(tmp_path, capsys):
    target = tmp_path / "producer.stderr"
    producer = tee_pipeline(1, 1) >= str(target)
    consumer = local[sys.executable][
        "-c",
        "import sys; sys.stdout.write(sys.stdin.read()); sys.stderr.write('last')",
    ]

    assert (producer | consumer).run_tee() == (0, "payload", "last")
    assert capsys.readouterr() == ("payload", "last")
    assert target.read_text(encoding="utf-8") == TOKENS[0]
