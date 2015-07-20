from __future__ import with_statement, print_function
import unittest
from plumbum import COLOR
from plumbum.color.styles import ANSIStyle as Style
from plumbum.color import HTMLCOLOR
import sys

class TestColor(unittest.TestCase):

    def setUp(self):
        Style.use_color = True

    def testColorStrings(self):
        self.assertEqual('\033[0m', COLOR.RESET)
        self.assertEqual('\033[1m', COLOR.BOLD)
        self.assertEqual('\033[39m', COLOR.FG.RESET)

    def testNegateIsReset(self):
        self.assertEqual(COLOR.RESET, -COLOR)
        self.assertEqual(COLOR.FG.RESET, -COLOR.FG)
        self.assertEqual(COLOR.BG.RESET, -COLOR.BG)

    def testShifts(self):
        self.assertEqual("This" << COLOR.RED, "This" >> COLOR.RED)
        self.assertEqual("This" << COLOR.RED, "This" << COLOR.RED)
        if sys.version_info >= (2, 7):
            self.assertEqual("This" << COLOR.RED, "This" * COLOR.RED)
        self.assertEqual("This" << COLOR.RED, COLOR.RED << "This")
        self.assertEqual("This" << COLOR.RED, COLOR.RED << "This")
        self.assertEqual("This" << COLOR.RED, COLOR.RED * "This")
        self.assertEqual(COLOR.RED.wrap("This"), "This" << COLOR.RED)

    def testLoadColorByName(self):
        self.assertEqual(COLOR['LightBlue'], COLOR.FG['LightBlue'])
        self.assertEqual(COLOR.BG['light_green'], COLOR.BG['LightGreen'])
        self.assertEqual(COLOR['DeepSkyBlue1'], COLOR['#00afff'])
        self.assertEqual(COLOR['DeepSkyBlue1'], COLOR.hex('#00afff'))

        self.assertEqual(COLOR['DeepSkyBlue1'], COLOR[39])

    def testMultiColor(self):
        sumcolor = COLOR.BOLD + COLOR.BLUE
        self.assertEqual(COLOR.BOLD.RESET + COLOR.FG.RESET, -sumcolor)

    def testSums(self):
        # Sums should not be communitave, last one is used
        self.assertEqual(COLOR.RED, COLOR.BLUE + COLOR.RED)
        self.assertEqual(COLOR.BG.GREEN, COLOR.BG.RED + COLOR.BG.GREEN)

    def testFromAnsi(self):
        for color in COLOR.simple_colorful:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR.BG.simple_colorful:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR.BG:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in (COLOR.BOLD, COLOR.UNDERLINE, COLOR.BLINK):
            self.assertEqual(color, COLOR.from_ansi(str(color)))

        color = COLOR.BOLD + COLOR.FG.GREEN + COLOR.BG.BLUE + COLOR.UNDERLINE
        self.assertEqual(color, COLOR.from_ansi(str(color)))
        color = COLOR.RESET
        self.assertEqual(color, COLOR.from_ansi(str(color)))

    def testWrappedColor(self):
        string = 'This is a string'
        wrapped = '\033[31mThis is a string\033[39m'
        self.assertEqual(COLOR.RED.wrap(string), wrapped)
        self.assertEqual(string << COLOR.RED, wrapped)
        self.assertEqual(COLOR.RED(string), wrapped)
        self.assertEqual(COLOR.RED[string], wrapped)

        newcolor = COLOR.BLUE + COLOR.UNDERLINE
        self.assertEqual(newcolor(string), string << newcolor)
        self.assertEqual(newcolor(string), string << COLOR.BLUE + COLOR.UNDERLINE)

    def testUndoColor(self):
        self.assertEqual('\033[39m', -COLOR.FG)
        self.assertEqual('\033[39m', ~COLOR.FG)
        self.assertEqual('\033[39m', ''-COLOR.FG)
        self.assertEqual('\033[49m', -COLOR.BG)
        self.assertEqual('\033[49m', ''-COLOR.BG)
        self.assertEqual('\033[21m', -COLOR.BOLD)
        self.assertEqual('\033[22m', -COLOR.DIM)
        for i in range(7):
            self.assertEqual('\033[39m', -COLOR(i))
            self.assertEqual('\033[49m', -COLOR.BG(i))
            self.assertEqual('\033[39m', -COLOR.FG(i))
            self.assertEqual('\033[49m', -COLOR.BG(i))
        for i in range(256):
            self.assertEqual('\033[39m', -COLOR.FG[i])
            self.assertEqual('\033[49m', -COLOR.BG[i])
        self.assertEqual('\033[0m', -COLOR.RESET)
        self.assertEqual(COLOR.DO_NOTHING, -COLOR.DO_NOTHING)

        self.assertEqual(COLOR.BOLD.RESET, -COLOR.BOLD)

    def testLackOfColor(self):
        Style.use_color = False
        self.assertEqual('', COLOR.FG.RED)
        self.assertEqual('', -COLOR.FG)
        self.assertEqual('', COLOR.FG['LightBlue'])

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
        print(COLOR.FG.RED("this is in red"), "but this is not")
        print(COLOR.FG.GREEN + "Hi, " + COLOR.BG[23]
              + "This is on a BG" - COLOR.BG + " and this is not")
        COLOR.RESET()

    def test_html(self):
        red_tagged = '<font color="#800000">This is tagged</font>'
        self.assertEqual(HTMLCOLOR.RED("This is tagged"), red_tagged)
        self.assertEqual("This is tagged" << HTMLCOLOR.RED, red_tagged)
        self.assertEqual("This is tagged" * HTMLCOLOR.RED, red_tagged)

        twin_tagged = '<font color="#800000"><em>This is tagged</em></font>'
        self.assertEqual("This is tagged" << HTMLCOLOR.RED + HTMLCOLOR.EM, twin_tagged)
        self.assertEqual("This is tagged" << HTMLCOLOR.EM << HTMLCOLOR.RED, twin_tagged)
        self.assertEqual(HTMLCOLOR.EM * HTMLCOLOR.RED * "This is tagged", twin_tagged)
        self.assertEqual(HTMLCOLOR.RED << "This should be wrapped", "This should be wrapped" << HTMLCOLOR.RED)

if __name__ == '__main__':
    unittest.main()
