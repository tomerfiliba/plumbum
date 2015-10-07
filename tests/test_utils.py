import unittest
from plumbum import local, SshMachine
from plumbum.path.utils import copy, delete, move
from plumbum._testtools import skip_on_windows

@skip_on_windows
class UtilsTest(unittest.TestCase):
    def test_copy_move_delete(self):
        from plumbum.cmd import touch

        with local.tempdir() as dir:
            (dir / "orog").mkdir()
            (dir / "orog" / "rec").mkdir()
            for i in range(20):
                touch(dir / "orog" / ("f%d.txt" % (i,)))
            for i in range(20,40):
                touch(dir / "orog" / "rec" / ("f%d.txt" % (i,)))

            move(dir / "orog", dir / "orig")

            s1 = sorted(f.name for f in (dir / "orig").walk())

            copy(dir / "orig", dir / "dup")
            s2 = sorted(f.name for f in (dir / "dup").walk())
            self.assertEqual(s1, s2)

            with SshMachine("localhost") as rem:
                with rem.tempdir() as dir2:
                    copy(dir / "orig", dir2)
                    s3 = sorted(f.name for f in (dir2 / "orig").walk())
                    self.assertEqual(s1, s3)

                    copy(dir2 / "orig", dir2 / "dup")
                    s4 = sorted(f.name for f in (dir2 / "dup").walk())
                    self.assertEqual(s1, s4)

                    copy(dir2 / "dup", dir / "dup2")
                    s5 = sorted(f.name for f in (dir / "dup2").walk())
                    self.assertEqual(s1, s5)

                    with SshMachine("localhost") as rem2:
                        with rem2.tempdir() as dir3:
                            copy(dir2 / "dup", dir3)
                            s6 = sorted(f.name for f in (dir3 / "dup").walk())
                            self.assertEqual(s1, s6)

                            move(dir3 / "dup", dir / "superdup")
                            self.assertFalse((dir3 / "dup").exists())

                            s7 = sorted(f.name for f in (dir / "superdup").walk())
                            self.assertEqual(s1, s7)

                            # test rm
                            delete(dir)


if __name__ == "__main__":
    unittest.main()
