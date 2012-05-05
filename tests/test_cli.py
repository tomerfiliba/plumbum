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
    verbose = cli.CountAttr(["v"], help = "increases the verbosity level")
    
    def main(self, *args):
        self.tailargs = args


class CLITest(unittest.TestCase):
    def test_meta_switches(self):
        self.assertRaises(SystemExit, TestApp.run, ["foo", "-h"])
        self.assertRaises(SystemExit, TestApp.run, ["foo", "--version"])
    
    def test_okay(self):
        self.assertRaises(SystemExit, TestApp.run, 
            ["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv", "--", "lala", "-e", "7"])



if __name__ == "__main__":
    unittest.main()
