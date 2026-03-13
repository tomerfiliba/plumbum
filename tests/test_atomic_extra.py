from __future__ import annotations

from typing import Any

import pytest

from plumbum import local
from plumbum._testtools import skip_on_windows
from plumbum.fs.atomic import AtomicCounterFile, AtomicFile, PidFile, PidFileTaken


@skip_on_windows
def test_atomicfile_context_large_write_and_read_shared() -> None:
    with local.tempdir() as tmp:
        af = AtomicFile(str(tmp / "atomic.bin"))
        payload = b"x" * (AtomicFile.CHUNK_SIZE + 7)

        with af as ctx:
            assert ctx is af
            af.write_atomic(payload)
            assert af.read_shared() == payload
            assert af.read_atomic() == payload

        assert "closed" in repr(af)


@skip_on_windows
def test_atomicfile_locked_raises_when_deleted() -> None:
    with local.tempdir() as tmp:
        af = AtomicFile(str(tmp / "atomic.bin"))
        af.path.delete()

        with pytest.raises(ValueError, match="removed from filesystem"), af.locked():
            pass


@skip_on_windows
def test_atomic_counter_context_manager_closes_file() -> None:
    with local.tempdir() as tmp:
        with AtomicCounterFile.open(str(tmp / "counter")) as counter:
            assert counter.next() == 0

        assert "closed" in repr(counter.atomicfile)


class _RaisingCtx:
    def __enter__(self):
        raise OSError("lock unavailable")

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> bool:
        return False


@skip_on_windows
def test_pidfile_acquire_reports_unknown_pid_on_read_error() -> None:
    class _FakeAtomicFile:
        path = "mypid"

        @staticmethod
        def locked(blocking: bool = False):
            _ = blocking
            return _RaisingCtx()

        @staticmethod
        def read_shared():
            raise OSError("no read")

        @staticmethod
        def write_atomic(_data: bytes):
            pass

        @staticmethod
        def delete():
            return None

        @staticmethod
        def close():
            return None

    with local.tempdir() as tmp:
        pidfile = PidFile(str(tmp / "mypid"))
        pidfile.atomicfile = _FakeAtomicFile()  # type: ignore[assignment]

        with pytest.raises(PidFileTaken) as excinfo:
            pidfile.acquire()

        assert excinfo.value.pid == "Unknown"


@skip_on_windows
def test_pidfile_release_without_context_is_noop() -> None:
    with local.tempdir() as tmp:
        pidfile = PidFile(str(tmp / "mypid"))
        pidfile.release()
        pidfile.close()


@skip_on_windows
def test_pidfile_acquire_is_idempotent(monkeypatch) -> None:
    class _Ctx:
        def __init__(self):
            self.enter_calls = 0

        def __enter__(self):
            self.enter_calls += 1

        def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> bool:
            return False

    class _FakeAtomicFile:
        path = "mypid"

        def __init__(self, ctx: Any):
            self.ctx = ctx

        def locked(self, blocking: bool = False):
            _ = blocking
            return self.ctx

        @staticmethod
        def write_atomic(_data: bytes):
            pass

        @staticmethod
        def delete():
            return None

        @staticmethod
        def close():
            return None

    with local.tempdir() as tmp:
        pidfile = PidFile(str(tmp / "mypid"))
        ctx = _Ctx()
        pidfile.atomicfile = _FakeAtomicFile(ctx)  # type: ignore[assignment]
        monkeypatch.setattr("plumbum.fs.atomic.atexit.register", lambda _fn: None)

        pidfile.acquire()
        pidfile.acquire()

        assert ctx.enter_calls == 1
        pidfile.release()
