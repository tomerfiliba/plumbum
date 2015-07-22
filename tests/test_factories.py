#!/usr/bin/env python
from __future__ import with_statement, print_function
import unittest
from plumbum import COLOR
from plumbum.color.styles import ANSIStyle as Style, ColorNotFound
from plumbum.color import HTMLCOLOR
import sys

class TestANSIColor(unittest.TestCase):

    def setUp(self):
        COLOR.use_color = True

    def testColorSlice(self):
        vals = COLOR[:8]
        self.assertEqual(len(vals),8)
        self.assertEqual(vals[1], COLOR.RED)
        vals = COLOR[40:50]
        self.assertEqual(len(vals),10)
        self.assertEqual(vals[1], COLOR.full(41))

    def testLoadNumericalColor(self):
        self.assertEqual(COLOR.full(2), COLOR[2])
        self.assertEqual(COLOR.simple(2), COLOR(2))
        self.assertEqual(COLOR(54), COLOR[54])

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
        self.assertEqual(COLOR.DeepSkyBlue1, COLOR[39])
        self.assertEqual(COLOR.deepskyblue1, COLOR[39])
        self.assertEqual(COLOR.Deep_Sky_Blue1, COLOR[39])

        self.assertRaises(AttributeError, lambda: COLOR.Notacoloratall)


    def testMultiColor(self):
        sumcolor = COLOR.BOLD + COLOR.BLUE
        self.assertEqual(COLOR.BOLD.RESET + COLOR.FG.RESET, -sumcolor)

    def testSums(self):
        # Sums should not be communitave, last one is used
        self.assertEqual(COLOR.RED, COLOR.BLUE + COLOR.RED)
        self.assertEqual(COLOR.BG.GREEN, COLOR.BG.RED + COLOR.BG.GREEN)

    def testRepresentations(self):
        color1 = COLOR.full(87)
        self.assertEqual(color1, COLOR.DarkSlateGray2)
        self.assertEqual(color1.basic, COLOR.DarkSlateGray2)
        self.assertEqual(str(color1.basic), str(COLOR.LightGray))

        color2 = COLOR.rgb(1,45,214)
        self.assertEqual(str(color2.full), str(COLOR.Blue3A))


    def testFromAnsi(self):
        for color in COLOR[1:7]:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR.BG[1:7]:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR.BG:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR[:16]:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in COLOR.BG[:16]:
            self.assertEqual(color, COLOR.from_ansi(str(color)))
        for color in (COLOR.BOLD, COLOR.UNDERLINE, COLOR.ITALICS):
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
        self.assertEqual(COLOR.RED*string, wrapped)
        self.assertEqual(COLOR.RED[string], wrapped)

        newcolor = COLOR.BLUE + COLOR.UNDERLINE
        self.assertEqual(newcolor[string], string << newcolor)
        self.assertEqual(newcolor.wrap(string), string << COLOR.BLUE + COLOR.UNDERLINE)

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

    def testFromHex(self):
        self.assertRaises(ColorNotFound, lambda: COLOR.hex('asdf'))
        self.assertRaises(ColorNotFound, lambda: COLOR.hex('#1234Z2'))
        self.assertRaises(ColorNotFound, lambda: COLOR.hex(12))

    def testDirectCall(self):
        COLOR.BLUE()

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("Need to run in buffered mode!")

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output,str(COLOR.BLUE))

    def testDirectCallArgs(self):
        COLOR.BLUE("This is")

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("Need to run in buffered mode!")

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output,str("This is" << COLOR.BLUE))

    def testPrint(self):
        COLOR.YELLOW.print('This is printed to stdout')

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("Need to run in buffered mode!")

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output,str(COLOR.YELLOW.wrap('This is printed to stdout')))


class TestHTMLColor(unittest.TestCase):
    def test_html(self):
        red_tagged = '<font color="#C00000">This is tagged</font>'
        self.assertEqual(HTMLCOLOR.RED["This is tagged"], red_tagged)
        self.assertEqual("This is tagged" << HTMLCOLOR.RED, red_tagged)
        self.assertEqual("This is tagged" * HTMLCOLOR.RED, red_tagged)

        twin_tagged = '<font color="#C00000"><em>This is tagged</em></font>'
        self.assertEqual("This is tagged" << HTMLCOLOR.RED + HTMLCOLOR.EM, twin_tagged)
        self.assertEqual("This is tagged" << HTMLCOLOR.EM << HTMLCOLOR.RED, twin_tagged)
        self.assertEqual(HTMLCOLOR.EM * HTMLCOLOR.RED * "This is tagged", twin_tagged)
        self.assertEqual(HTMLCOLOR.RED << "This should be wrapped", "This should be wrapped" << HTMLCOLOR.RED)

if __name__ == '__main__':
    unittest.main(buffer=True)
