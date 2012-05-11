import unittest
from plumbum import cli


class TestApp(cli.Application):
    @cli.switch(["a"])
    def spam(self):
        print("!!a")

    @cli.switch(["b", "bacon"], argtype=int, mandatory = True)
    def bacon(self, param):
        """give me some bacon"""
        print ("!!b", param)
    
    eggs = cli.SwitchAttr(["e"], str, help = "sets the eggs attribute")
    verbose = cli.CountingAttr(["v"], help = "increases the verbosity level")

    def main(self, *args):
        self.tailargs = args


class CLITest(unittest.TestCase):
    def test_meta_switches(self):
        _, rc = TestApp._run(["foo", "-h"])
        self.assertEqual(rc, 0)
        _, rc = TestApp._run(["foo", "--version"])
        self.assertEqual(rc, 0)
    
    def test_okay(self):
        inst, rc = TestApp._run(["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv", 
            "--", "lala", "-e", "7"])
        self.assertEqual(rc, 0)
        self.assertEqual(inst.eggs, "7")



if __name__ == "__main__":
    unittest.main()
