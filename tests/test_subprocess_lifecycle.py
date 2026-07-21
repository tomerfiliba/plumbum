"""Regression tests for subprocess / pipeline lifecycle robustness (issue #820)."""

from __future__ import annotations

import contextlib
import os
import pickle
import signal
import subprocess
import time

import pytest

from plumbum import local
from plumbum._testtools import skip_on_windows
from plumbum.commands.processes import CommandNotFound, MinHeap


class TestCommandNotFound:
    def test_repr_does_not_contain_self(self):
        err = CommandNotFound("frobnicate", ["/usr/bin", "/bin"])
        # args must be (program, path), not (self, program, path)
        assert err.args == ("frobnicate", ["/usr/bin", "/bin"])
        assert err.program == "frobnicate"
        assert err.path == ["/usr/bin", "/bin"]

    def test_pickle_roundtrip(self):
        err = CommandNotFound("frobnicate", ["/usr/bin", "/bin"])
        restored = pickle.loads(pickle.dumps(err))
        assert restored.args == err.args
        assert restored.program == "frobnicate"
        assert restored.path == ["/usr/bin", "/bin"]


class TestTimeoutHeap:
    def test_equal_deadlines_do_not_compare_procs(self):
        """Equal deadlines must not make heapq compare the (uncomparable) procs."""

        class FakeProc:
            # Deliberately not orderable; comparing two would raise TypeError.
            __hash__ = None  # type: ignore[assignment]

        heap = MinHeap()
        deadline = 123.0
        # Same deadline, distinct monotonic counter values as the tiebreaker.
        heap.push((deadline, 0, FakeProc()))  # type: ignore[arg-type]
        heap.push((deadline, 1, FakeProc()))  # type: ignore[arg-type]
        # peek/pop must not raise TypeError from comparing FakeProc objects
        first = heap.peek()
        assert first[0] == deadline
        heap.pop()
        assert len(heap) == 1


class TestPipelineArgsPlacement:
    def test_formulate_places_args_on_source(self):
        a = local["echo"]
        b = local["cat"]
        pipe = a | b
        formulated = pipe.formulate(0, ["hello"])
        text = " ".join(formulated)
        # args belong to the source, matching popen behavior: ``echo hello | cat``.
        # Split on the pipe so the check is robust to absolute exe paths (Windows).
        src, sep, dst = text.partition("|")
        assert sep, "pipeline should formulate with a '|'"
        assert "hello" in src
        assert "hello" not in dst
        # the bound-command path goes through the same logic
        bsrc, bsep, bdst = str(pipe.bound_command("hello")).partition("|")
        assert bsep
        assert "hello" in bsrc
        assert "hello" not in bdst


class TestBgrunCleanupOnException:
    @skip_on_windows
    def test_runner_invoked_on_exception(self):
        sentinel = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"), local["true"].bgrun() as p:
            # the process started but the body raises before p.run()
            raise sentinel
        # finally-block ran runner(): the process was reaped
        assert p.poll() is not None
        assert p.returncode is not None

    @skip_on_windows
    def test_exception_not_masked_by_nonzero_exit(self):
        """A body exception must not be replaced by ProcessExecutionError."""
        procs = []

        def body():
            with local["false"].bgrun() as p:
                procs.append(p)
                p.wait()  # let the process exit (nonzero) before the body raises
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            body()
        assert procs[0].poll() is not None

    @skip_on_windows
    def test_exception_kills_long_running_process(self):
        """A body exception must not wait for the process to finish naturally."""
        start = time.monotonic()
        with (
            pytest.raises(RuntimeError, match="boom"),
            local["sleep"]["30"].bgrun() as p,
        ):
            raise RuntimeError("boom")
        assert time.monotonic() - start < 10
        assert p.poll() is not None

    @skip_on_windows
    def test_normal_run_reaps_exactly_once(self):
        with local["echo"]["hi"].bgrun() as p:
            rc, out, _err = p.run()
        assert rc == 0
        assert out.strip() == "hi"
        # the implicit finally runner() must be a no-op (already run)
        assert p.poll() is not None


class TestDaemonWaitTimeout:
    @skip_on_windows
    @pytest.mark.timeout(30)
    def test_wait_timeout_raises(self):
        """wait(timeout=...) on a live daemon must raise TimeoutExpired."""
        proc = local.daemonic_popen(local["sleep"][10])
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                proc.wait(timeout=0.5)
        finally:
            with contextlib.suppress(OSError):
                os.kill(proc.pid, signal.SIGTERM)
