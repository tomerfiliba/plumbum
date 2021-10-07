# -*- coding: utf-8 -*-
import pytest

from plumbum import SshMachine, local
from plumbum._testtools import skip_on_windows
from plumbum.path.utils import copy, delete, move


@skip_on_windows
@pytest.mark.ssh
def test_copy_move_delete():
    from plumbum.cmd import touch

    with local.tempdir() as dir:
        (dir / "orog").mkdir()
        (dir / "orog" / "rec").mkdir()
        for i in range(20):
            touch(dir / "orog" / ("f%d.txt" % (i,)))
        for i in range(20, 40):
            touch(dir / "orog" / "rec" / ("f%d.txt" % (i,)))

        move(dir / "orog", dir / "orig")

        s1 = sorted(f.name for f in (dir / "orig").walk())

        copy(dir / "orig", dir / "dup")
        s2 = sorted(f.name for f in (dir / "dup").walk())
        assert s1 == s2

        with SshMachine("localhost") as rem:
            with rem.tempdir() as dir2:
                copy(dir / "orig", dir2)
                s3 = sorted(f.name for f in (dir2 / "orig").walk())
                assert s1 == s3

                copy(dir2 / "orig", dir2 / "dup")
                s4 = sorted(f.name for f in (dir2 / "dup").walk())
                assert s1 == s4

                copy(dir2 / "dup", dir / "dup2")
                s5 = sorted(f.name for f in (dir / "dup2").walk())
                assert s1 == s5

                with SshMachine("localhost") as rem2:
                    with rem2.tempdir() as dir3:
                        copy(dir2 / "dup", dir3)
                        s6 = sorted(f.name for f in (dir3 / "dup").walk())
                        assert s1 == s6

                        move(dir3 / "dup", dir / "superdup")
                        assert not (dir3 / "dup").exists()

                        s7 = sorted(f.name for f in (dir / "superdup").walk())
                        assert s1 == s7

                        # test rm
                        delete(dir)
