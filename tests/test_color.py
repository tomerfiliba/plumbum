from __future__ import with_statement, print_function
import unittest
from plumbum.cli import COLOR, with_color


class TestColor(unittest.TestCase):

    def testColorStrings(self):
        self.assertEqual('\033[0m', COLOR.RESET)
        self.assertEqual('\033[1m', COLOR.BOLD)

    def testUndoColor(self):
        self.assertEqual('\033[39m', -COLOR.FG)
        self.assertEqual('\033[39m', ''-COLOR.FG)
        self.assertEqual('\033[49m', -COLOR.BG)
        self.assertEqual('\033[49m', ''-COLOR.BG)
        self.assertEqual('\033[21m', -COLOR.BOLD)
        self.assertEqual('\033[22m', -COLOR.DIM)
        for i in (1, 2, 4, 5, 7, 8):
            self.assertEqual('\033[%im' % i, -COLOR('\033[%im' % (20 + i)))
            self.assertEqual('\033[%im' % (i + 20), -COLOR('\033[%im' % i))
        for i in range(10):
            self.assertEqual('\033[39m', -COLOR('\033[%im' % (30 + i)))
            self.assertEqual('\033[49m', -COLOR('\033[%im' % (40 + i)))
            self.assertEqual('\033[39m', -COLOR.FG(i))
            self.assertEqual('\033[49m', -COLOR.BG(i))
        for i in range(256):
            self.assertEqual('\033[39m', -COLOR.FG[i])
            self.assertEqual('\033[49m', -COLOR.BG[i])
        self.assertEqual('\033[0m', -COLOR.RESET)
        self.assertEqual('\033[0m', -COLOR('this is random'))

    def testVisualColors(self):
        print()
        for c in (COLOR.FG(x) for x in range(1, 6)):
            with with_color(c):
                print('Cycle color test', end=' ')
            print(' - > back to normal')
        with with_color():
            print(COLOR.FG.GREEN + "Green "
                  + COLOR.BOLD + "Bold "
                  - COLOR.BOLD + "Normal")
        print("Reset all")

    def testToggleColors(self):
        print()
        print(COLOR.FG.RED("this is in red"), "but this is not")
        print(COLOR.FG.GREEN + "Hi, " + COLOR.BG[23]
              + "This is on a BG" - COLOR.BG + " and this is not")
        COLOR.RESET()

if __name__ == '__main__':
    unittest.main()
