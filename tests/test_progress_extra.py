from __future__ import annotations

import pytest

from plumbum.cli import progress


class TestProgressExtra:
    def test_next_before_start_raises(self) -> None:
        prog = progress.Progress(range(2))
        with pytest.raises(ValueError, match="Iteration not started"):
            next(prog)

    def test_increment_before_start_raises(self) -> None:
        prog = progress.Progress(range(2))
        with pytest.raises(ValueError, match="Iteration not started"):
            prog.increment()

    def test_time_remaining_without_start_time_raises(self) -> None:
        class _ProgressForTest(progress.Progress[int]):
            def force_started_without_timer(self) -> None:
                self.value = 1
                self._start_time = None

        prog = _ProgressForTest(range(2))
        prog.force_started_without_timer()
        with pytest.raises(ValueError, match="Iteration not started"):
            prog.time_remaining()

    def test_wrap_sets_body_and_iterates(self) -> None:
        prog = progress.Progress.wrap(["a", "b"], timer=False)
        assert prog.body is True
        assert list(prog) == ["a", "b"]

    def test_string_wide_terminal_contains_center_percent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(progress, "get_terminal_size", lambda **kwargs: (80, 24))

        prog = progress.Progress(length=10, timer=False, has_output=False)
        prog.start()
        prog.value = 5

        rendered = str(prog)
        assert " 50% " in rendered
        assert "5 of 10 complete" in rendered

    def test_string_narrow_terminal_uses_compact_timer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(progress, "get_terminal_size", lambda **kwargs: (20, 24))

        prog = progress.Progress(length=3, timer=True, has_output=False)
        prog.start()
        prog.value = 1

        rendered = str(prog)
        assert rendered.startswith("33% complete: ")

    def test_display_writes_carriage_return_when_rewritable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(progress, "get_terminal_size", lambda **kwargs: (80, 24))

        prog = progress.Progress(length=3, timer=False, has_output=False)
        prog.start()
        prog.display()

        out = capsys.readouterr().out
        assert "\r" in out

    def test_done_clears_line_when_clear_true(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(progress, "get_terminal_size", lambda **kwargs: (80, 24))

        prog = progress.Progress(length=1, timer=False, has_output=False, clear=True)
        prog.start()
        prog.done()

        out = capsys.readouterr().out
        assert out.endswith("\r")
        assert "\n" not in out

    def test_next_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(progress, "get_terminal_size", lambda **kwargs: (80, 24))
        prog = progress.Progress([10], timer=False)
        iter(prog)
        assert prog.next() == 10
