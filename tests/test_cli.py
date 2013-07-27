from __future__ import with_statement
import sys
import unittest
from plumbum import cli
from contextlib import contextmanager
if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from StringIO import StringIO


@contextmanager
def captured_stdout():
    prev = sys.stdout
    stream = StringIO()
    sys.stdout = stream
    try:
        yield stream
    finally:
        sys.stdout = prev


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

class GeetAdd(cli.Application):
    def main(self, *files):
        return "adding", files

class GeetCommit(cli.Application):
    message = cli.Flag("-m", str)
    
    def main(self):
        if self.parent.debug:
            return "committing in debug"
        else:
            return "committing"

# python 2.5 compatibility (otherwise, could be used as a decorator)
Geet.subcommand("add", GeetAdd)
Geet.subcommand("commit", GeetCommit)

class Sample(cli.Application):
    foo = cli.SwitchAttr("--foo")

Sample.unbind_switches("--version")

class Mumble(cli.Application):
    pass

Sample.subcommand("mumble", Mumble)

if not hasattr(unittest.TestCase, "assertIn"):
    def assertIn(self, member, container, msg = None):
        if msg:
            assert member in container, msg
        else:
            assert member in container
    def assertNotIn(self, member, container, msg = None):
        if msg:
            assert member not in container, msg
        else:
            assert member not in container
    unittest.TestCase.assertIn = assertIn
    unittest.TestCase.assertNotIn = assertNotIn
    

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
    
    def test_unbind(self):
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "--help"], exit = False)
        self.assertEqual(rc, 0)
        self.assertIn("--foo", stream.getvalue())
        self.assertNotIn("--version", stream.getvalue())

    def test_default_main(self):
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("No sub-command given", stream.getvalue())
        
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "pimple"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("Unknown sub-command 'pimple'", stream.getvalue())
        
        with captured_stdout() as stream:
            _, rc = Sample.run(["sample", "mumble"], exit = False)
        self.assertEqual(rc, 1)
        self.assertIn("main() not implemented", stream.getvalue())



if __name__ == "__main__":
    unittest.main()
