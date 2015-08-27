#!/usr/bin/env python
from __future__ import with_statement, print_function
import unittest
from plumbum import colors

class TestVisualColor(unittest.TestCase):

    def setUp(self):
        try:
            import colorama
            colorama.init()
            self.colorama = colorama
            colors.use_color = True
            print()
            print("Colorama initialized")
        except ImportError:
            self.colorama = None

    def tearDown(self):
        if self.colorama:
            self.colorama.deinit()

    def testVisualColors(self):
        print()
        for c in colors.fg[:16]:
            with c:
                print('Cycle color test', end=' ')
            print(' - > back to normal')
        with colors:
            print(colors.fg.green + "Green "
                  + colors.bold + "Bold "
                  + ~colors.bold + "Normal")
        print("Reset all")

    def testToggleColors(self):
        print()
        print(colors.fg.red["This is in red"], "but this is not")
        print(colors.fg.green + "Hi, " + colors.bg[23]
              + "This is on a BG" + ~colors.bg + " and this is not")
        colors.yellow.print("This is printed from color.")
        colors.reset()

if __name__ == '__main__':
    unittest.main()
