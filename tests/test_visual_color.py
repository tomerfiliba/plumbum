#!/usr/bin/env python
from __future__ import with_statement, print_function
import unittest
from plumbum import COLOR

class TestVisualColor(unittest.TestCase):

    def setUp(self):
        try:
            import colorama
            colorama.init()
            self.colorama = colorama
            COLOR.use_color = True
            print()
            print("Colorama initialized")
        except ImportError:
            self.colorama = None

    def tearDown(self):
        if self.colorama:
            self.colorama.deinit()

    def testVisualColors(self):
        print()
        for c in (COLOR.FG(x) for x in range(1, 6)):
            with c:
                print('Cycle color test', end=' ')
            print(' - > back to normal')
        with COLOR:
            print(COLOR.FG.GREEN + "Green "
                  + COLOR.BOLD + "Bold "
                  - COLOR.BOLD + "Normal")
        print("Reset all")

    def testToggleColors(self):
        print()
        print(COLOR.FG.RED("This is in red"), "but this is not")
        print(COLOR.FG.GREEN + "Hi, " + COLOR.BG[23]
              + "This is on a BG" - COLOR.BG + " and this is not")
        COLOR.YELLOW.print("This is printed from color.")
        COLOR.RESET()

if __name__ == '__main__':
    unittest.main()
