from __future__ import annotations

from types import SimpleNamespace

import pytest

import plumbum.path.utils as path_utils
from plumbum import SshMachine, local
from plumbum._testtools import skip_on_windows
from plumbum.path.utils import copy, delete, gui_open, move


@skip_on_windows
@pytest.mark.ssh
def test_copy_move_delete():
    from plumbum.cmd import touch

    with local.tempdir() as dir:
        (dir / "orog").mkdir()
        (dir / "orog" / "rec").mkdir()
        for i in range(20):
            touch(dir / "orog" / f"f{i}.txt")
        for i in range(20, 40):
            touch(dir / "orog" / "rec" / f"f{i}.txt")

        move(dir / "orog", dir / "orig")

        s1 = sorted(f.name for f in (dir / "orig").walk())

        copy(dir / "orig", dir / "dup")
        s2 = sorted(f.name for f in (dir / "dup").walk())
        assert s1 == s2

        with SshMachine("localhost") as rem, rem.tempdir() as dir2:
            copy(dir / "orig", dir2)
            s3 = sorted(f.name for f in (dir2 / "orig").walk())
            assert s1 == s3

            copy(dir2 / "orig", dir2 / "dup")
            s4 = sorted(f.name for f in (dir2 / "dup").walk())
            assert s1 == s4

            copy(dir2 / "dup", dir / "dup2")
            s5 = sorted(f.name for f in (dir / "dup2").walk())
            assert s1 == s5

            with SshMachine("localhost") as rem2, rem2.tempdir() as dir3:
                copy(dir2 / "dup", dir3)
                s6 = sorted(f.name for f in (dir3 / "dup").walk())
                assert s1 == s6

                move(dir3 / "dup", dir / "superdup")
                assert not (dir3 / "dup").exists()

                s7 = sorted(f.name for f in (dir / "superdup").walk())
                assert s1 == s7

                # test rm
                delete(dir)


def test_copy_move_delete_local_only():
    with local.tempdir() as base:
        source = base / "source"
        source.mkdir()
        (source / "a.txt").write_text("a", encoding="utf-8")
        (source / "b.txt").write_text("b", encoding="utf-8")

        copied = base / "copied"
        moved = base / "moved"

        copy(source, copied)
        assert (copied / "a.txt").read() == "a"
        assert (copied / "b.txt").read() == "b"

        move(copied, moved)
        assert not copied.exists()
        assert (moved / "a.txt").exists()

        delete([source, str(moved)])
        assert not source.exists()
        assert not moved.exists()


def test_copy_move_multiple_sources_require_directory():
    with local.tempdir() as base:
        src1 = base / "src1.txt"
        src2 = base / "src2.txt"
        src1.write_text("1", encoding="utf-8")
        src2.write_text("2", encoding="utf-8")

        not_a_dir = base / "target.txt"
        not_a_dir.write_text("x", encoding="utf-8")

        with pytest.raises(ValueError):
            copy([src1, src2], not_a_dir)

        with pytest.raises(ValueError):
            move([src1, src2], not_a_dir)


def test_delete_rejects_invalid_type():
    with pytest.raises(TypeError):
        delete(123)


def test_gui_open_uses_startfile_when_available(monkeypatch):
    called = []

    def fake_startfile(filename):
        called.append(filename)

    monkeypatch.setattr(path_utils.os, "startfile", fake_startfile, raising=False)
    gui_open("demo.txt")

    assert called == ["demo.txt"]


def test_gui_open_falls_back_to_local_get(monkeypatch):
    calls = []

    def fake_opener(filename):
        calls.append(filename)

    monkeypatch.delattr(path_utils.os, "startfile", raising=False)
    monkeypatch.setattr(
        path_utils,
        "local",
        SimpleNamespace(get=lambda *args: fake_opener),
    )

    gui_open("demo.txt")

    assert calls == ["demo.txt"]
