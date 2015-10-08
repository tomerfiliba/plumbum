import os
import unittest
import sys
import time
from plumbum import local, NOHUP
try:
    from plumbum.cmd import bash, echo
except ImportError:
    bash = None
    echo = None
from plumbum.path.utils import delete
from plumbum._testtools import skip_on_windows



@skip_on_windows
class NOHUP_LOCAL(unittest.TestCase):
    def read_file(self, filename):
        self.assertTrue(filename in os.listdir('.'))
        with open(filename) as f:
            return f.read()

    def test_slow(self):
        delete('nohup.out')
        sp = bash['slow_process.bash']
        sp & NOHUP
        time.sleep(.5)
        self.assertEqual(self.read_file('slow_process.out'), 'Starting test\n1\n')
        self.assertEqual(self.read_file('nohup.out'), '1\n')
        time.sleep(1)
        self.assertEqual(self.read_file('slow_process.out'), 'Starting test\n1\n2\n')
        self.assertEqual(self.read_file('nohup.out'), '1\n2\n')
        time.sleep(2)
        delete('nohup.out', 'slow_process.out')

    def test_append(self):
        delete('nohup.out')
        output = echo['This is output']
        output & NOHUP
        time.sleep(.2)
        self.assertEqual(self.read_file('nohup.out'), 'This is output\n')
        output & NOHUP
        time.sleep(.2)
        self.assertEqual(self.read_file('nohup.out'), 'This is output\n'*2)
        delete('nohup.out')

    def test_redir(self):
        delete('nohup_new.out')
        output = echo['This is output']

        output & NOHUP(stdout = 'nohup_new.out')
        time.sleep(.2)
        self.assertEqual(self.read_file('nohup_new.out'), 'This is output\n')
        delete('nohup_new.out')

        (output > 'nohup_new.out') & NOHUP
        time.sleep(.2)
        self.assertEqual(self.read_file('nohup_new.out'), 'This is output\n')
        delete('nohup_new.out')

        output & NOHUP
        time.sleep(.2)
        self.assertEqual(self.read_file('nohup.out'), 'This is output\n')
        delete('nohup.out')


if __name__ == "__main__":
    unittest.main()

