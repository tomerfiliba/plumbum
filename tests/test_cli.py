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
    verbose = cli.CountOf(["v"], help = "increases the verbosity level")
    benedict = cli.CountOf(["--benedict"], help = """a very long help message with lots of 
        useless information that nobody would ever want to read, but heck, we need to test 
        text wrapping in help messages as well""")

    def main(self, *args):
        old = self.eggs
        self.eggs = "lalala"
        self.eggs = old
        self.tailargs = args

class Geet(cli.Application):
    debug = cli.Flag("--debug")
    
    def main(self):
        print ("hi this is geet main")

@Geet.subcommand("add")
class GeetAdd(cli.Application):
    def main(self, *files):
        return "adding", files

@Geet.subcommand("commit")
class GeetCommit(cli.Application):
    message = cli.Flag("-m", str)
    
    def main(self):
        if self.parent.debug:
            return "committing in debug"
        else:
            return "committing"


class CLITest(unittest.TestCase):
    def test_meta_switches(self):
        _, rc = TestApp.run(["foo", "-h"], exit = False)
        self.assertEqual(rc, 0)
        _, rc = TestApp.run(["foo", "--version"], exit = False)
        self.assertEqual(rc, 0)
    
    def test_okay(self):
        _, rc = TestApp.run(["foo", "--bacon=81"], exit = False)
        self.assertEqual(rc, 0)

        inst, rc = TestApp.run(["foo", "--bacon=81", "-a", "-v", "-e", "7", "-vv", 
            "--", "lala", "-e", "7"], exit = False)
        self.assertEqual(rc, 0)
        self.assertEqual(inst.eggs, "7")
    
    def test_failures(self):
        _, rc = TestApp.run(["foo"], exit = False)
        self.assertEqual(rc, 2)

        _, rc = TestApp.run(["foo", "--bacon=hello"], exit = False)
        self.assertEqual(rc, 2)
    
    def test_subcommands(self):
        _, rc = Geet.run(["geet", "--debug"], exit = False)
        self.assertEqual(rc, 0)
        _, rc = Geet.run(["geet", "--debug", "add", "foo.txt", "bar.txt"], exit = False)
        self.assertEqual(rc, ("adding", ("foo.txt", "bar.txt")))
        _, rc = Geet.run(["geet", "--debug", "commit"], exit = False)
        self.assertEqual(rc, "committing in debug")
        _, rc = Geet.run(["geet", "--help"], exit = False)
        self.assertEqual(rc, 0)
        _, rc = Geet.run(["geet", "commit", "--help"], exit = False)
        self.assertEqual(rc, 0)




if __name__ == "__main__":
    unittest.main()
