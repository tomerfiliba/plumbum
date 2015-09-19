import unittest
from plumbum.cli.compapplication import CompApplication
from plumbum import cli
from plumbum.lib import six

"""
Usage:
    test_argcompleter.py [SWITCHES] args...

Meta-switches:
    -h, --help                 Prints this help message and quits
    --help-all                 Print help messages of all subcommands and quit
    --version                  Prints the program's version and quits

Switches:
    -a                         <function spam at 0x7f051f591140>
    -b, --bacon PARAM:int      give me some bacon; required
    --benedict                 a very long help message with lots of useless information that nobody would ever
                               want to read, but heck, we need to test text wrapping in help messages as well; may
                               be given multiple times
    -e VALUE:str               sets the eggs attribute
    -v                         increases the verbosity level; may be given multiple times
"""

class TestApp(CompApplication):
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

class ArgTest(unittest.TestCase):

    def test_firstword(self):
        self.assertEqual(TestApp._autocomplete_args('./TestApp ', 9), [''])

    def test_onedash(self):
        self.assertEqual(set(TestApp._autocomplete_args('./TestApp -', 10)),
                set('-a -b --bacon --benedict -e -v -h --help --help-all --version'.split()))
    def test_twodash(self):
        self.assertEqual(set(TestApp._autocomplete_args('./TestApp --', 11)),
                set('--bacon --benedict --help --help-all --version'.split()))
    def test_partial(self):
        self.assertEqual(set(TestApp._autocomplete_args('./TestApp --b', 12)),
                set('--bacon --benedict'.split()))
    def test_twodash_completable(self):
        self.assertEqual(TestApp._autocomplete_args('./TestApp --ba', 13), ['con'])



if __name__ == "__main__":
    unittest.main()
