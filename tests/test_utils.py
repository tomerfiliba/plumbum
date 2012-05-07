import unittest
from plumbum import cp, rm, mv, local, SshMachine


class UtilsTest(unittest.TestCase):
    def test_utils(self):
        from plumbum.cmd import touch
        
        with local.tempdir() as dir:
            (dir / "orog").mkdir()
            (dir / "orog" / "rec").mkdir()
            for i in range(20):
                touch(dir / "orog" / ("f%d.txt" % (i,)))
            for i in range(20,40):
                touch(dir / "orog" / "rec" / ("f%d.txt" % (i,)))

            mv(dir / "orog", dir / "orig") 

            s1 = sorted(f.basename for f in (dir / "orig").walk())
            
            cp(dir / "orig", dir / "dup")
            s2 = sorted(f.basename for f in (dir / "dup").walk())
            self.assertEqual(s1, s2)
        
            with SshMachine("localhost") as rem:
                with rem.tempdir() as dir2:
                    cp(dir / "orig", dir2)
                    s3 = sorted(f.basename for f in (dir2 / "orig").walk())
                    self.assertEqual(s1, s3)

                    cp(dir2 / "orig", dir2 / "dup")
                    s4 = sorted(f.basename for f in (dir2 / "dup").walk())
                    self.assertEqual(s1, s4)

                    cp(dir2 / "dup", dir / "dup2")
                    s5 = sorted(f.basename for f in (dir / "dup2").walk())
                    self.assertEqual(s1, s5)
                
                    with SshMachine("localhost") as rem2:
                        with rem2.tempdir() as dir3:
                            cp(dir2 / "dup", dir3)
                            s6 = sorted(f.basename for f in (dir3 / "dup").walk())
                            self.assertEqual(s1, s6)
                            
                            # test rm
                            rm(dir)
                            rm(dir3)




if __name__ == "__main__":
    unittest.main()
