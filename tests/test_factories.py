#!/usr/bin/env python
from __future__ import with_statement, print_function
import unittest
from plumbum import colors
from plumbum.colorlib.styles import ANSIStyle as Style, ColorNotFound
from plumbum.colorlib import htmlcolors
import sys


class TestImportColors(unittest.TestCase):
    def testDifferentImports(self):
        import plumbum.colors
        from plumbum.colors import bold
        from plumbum.colors.fg import red
        self.assertEqual(str(red), str(colors.red))
        self.assertEqual(str(bold), str(colors.bold))

class TestANSIColor(unittest.TestCase):

    def setUp(self):
        colors.use_color = True

    def testColorSlice(self):
        vals = colors[:8]
        self.assertEqual(len(vals),8)
        self.assertEqual(vals[1], colors.red)
        vals = colors[40:50]
        self.assertEqual(len(vals),10)
        self.assertEqual(vals[1], colors.full(41))

    def testLoadNumericalColor(self):
        self.assertEqual(colors.full(2), colors[2])
        self.assertEqual(colors.simple(2), colors(2))
        self.assertEqual(colors(54), colors[54])
        self.assertEqual(colors(1,30,77),colors.rgb(1,30,77))
        self.assertEqual(colors[1,30,77],colors.rgb(1,30,77))

    def testColorStrings(self):
        self.assertEqual('\033[0m', colors.reset)
        self.assertEqual('\033[1m', colors.bold)
        self.assertEqual('\033[39m', colors.fg.reset)

    def testNegateIsReset(self):
        self.assertEqual(colors.reset, ~colors)
        self.assertEqual(colors.fg.reset, ~colors.fg)
        self.assertEqual(colors.bg.reset, ~colors.bg)

    def testFromPreviousColor(self):
        self.assertEqual(colors(colors.red), colors.red)
        self.assertEqual(colors(colors.bg.red), colors.bg.red)
        self.assertEqual(colors(colors.bold), colors.bold)

    def testFromCode(self):
        self.assertEqual(colors('\033[31m'),colors.red)

    def testEmptyStyle(self):
        self.assertEqual(str(colors()), '')
        self.assertEqual(str(colors('')), '')
        self.assertEqual(str(colors(None)), '')

    def testLoadColorByName(self):
        self.assertEqual(colors['LightBlue'], colors.fg['LightBlue'])
        self.assertEqual(colors.bg['light_green'], colors.bg['LightGreen'])
        self.assertEqual(colors['DeepSkyBlue1'], colors['#00afff'])
        self.assertEqual(colors['DeepSkyBlue1'], colors.hex('#00afff'))

        self.assertEqual(colors['DeepSkyBlue1'], colors[39])
        self.assertEqual(colors.DeepSkyBlue1, colors[39])
        self.assertEqual(colors.deepskyblue1, colors[39])
        self.assertEqual(colors.Deep_Sky_Blue1, colors[39])
        self.assertEqual(colors.RED, colors.red)

        self.assertRaises(AttributeError, lambda: colors.Notacolorsatall)


    def testMultiColor(self):
        sumcolors = colors.bold & colors.blue
        self.assertEqual(colors.bold.reset & colors.fg.reset, ~sumcolors)

    def testSums(self):
        # Sums should not be communitave, last one is used
        self.assertEqual(colors.red, colors.blue & colors.red)
        self.assertEqual(colors.bg.green, colors.bg.red & colors.bg.green)

    def testRepresentations(self):
        colors1 = colors.full(87)
        self.assertEqual(colors1, colors.DarkSlateGray2)
        self.assertEqual(colors1.basic, colors.DarkSlateGray2)
        self.assertEqual(str(colors1.basic), str(colors.LightGray))

        colors2 = colors.rgb(1,45,214)
        self.assertEqual(str(colors2.full), str(colors.Blue3A))


    def testFromAnsi(self):
        for c in colors[1:7]:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in colors.bg[1:7]:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in colors:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in colors.bg:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in colors[:16]:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in colors.bg[:16]:
            self.assertEqual(c, colors.from_ansi(str(c)))
        for c in (colors.bold, colors.underline, colors.italics):
            self.assertEqual(c, colors.from_ansi(str(c)))

        col = colors.bold & colors.fg.green & colors.bg.blue & colors.underline
        self.assertEqual(col, colors.from_ansi(str(col)))
        col = colors.reset
        self.assertEqual(col, colors.from_ansi(str(col)))

    def testWrappedColor(self):
        string = 'This is a string'
        wrapped = '\033[31mThis is a string\033[39m'
        self.assertEqual(colors.red.wrap(string), wrapped)
        self.assertEqual(colors.red | string, wrapped)
        self.assertEqual(colors.red[string], wrapped)

        newcolors = colors.blue & colors.underline
        self.assertEqual(newcolors[string], string | newcolors)
        self.assertEqual(newcolors.wrap(string), string | colors.blue & colors.underline)

    def testUndoColor(self):
        self.assertEqual('\033[39m', ~colors.fg)
        self.assertEqual('\033[49m', ~colors.bg)
        self.assertEqual('\033[22m', ~colors.bold)
        self.assertEqual('\033[22m', ~colors.dim)
        for i in range(7):
            self.assertEqual('\033[39m', ~colors(i))
            self.assertEqual('\033[49m', ~colors.bg(i))
            self.assertEqual('\033[39m', ~colors.fg(i))
            self.assertEqual('\033[49m', ~colors.bg(i))
        for i in range(256):
            self.assertEqual('\033[39m', ~colors.fg[i])
            self.assertEqual('\033[49m', ~colors.bg[i])
        self.assertEqual('\033[0m', ~colors.reset)
        self.assertEqual(colors.do_nothing, ~colors.do_nothing)

        self.assertEqual(colors.bold.reset, ~colors.bold)

    def testLackOfColor(self):
        Style.use_color = False
        self.assertEqual('', colors.fg.red)
        self.assertEqual('', ~colors.fg)
        self.assertEqual('', colors.fg['LightBlue'])

    def testFromHex(self):
        self.assertRaises(ColorNotFound, lambda: colors.hex('asdf'))
        self.assertRaises(ColorNotFound, lambda: colors.hex('#1234Z2'))
        self.assertRaises(ColorNotFound, lambda: colors.hex(12))

    def testDirectCall(self):
        colors.blue()

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("Need to run in buffered mode!")

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output,str(colors.blue))


    def testPrint(self):
        colors.yellow.print('This is printed to stdout')

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("Need to run in buffered mode!")

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output,str(colors.yellow.wrap('This is printed to stdout')))


class TestHTMLColor(unittest.TestCase):
    def test_html(self):
        red_tagged = '<font color="#C00000">This is tagged</font>'
        self.assertEqual(htmlcolors.red["This is tagged"], red_tagged)
        self.assertEqual("This is tagged" | htmlcolors.red, red_tagged)

        twin_tagged = '<font color="#C00000"><em>This is tagged</em></font>'
        self.assertEqual("This is tagged" |  htmlcolors.red & htmlcolors.em, twin_tagged)
        self.assertEqual("This is tagged" | htmlcolors.em & htmlcolors.red, twin_tagged)
        self.assertEqual(htmlcolors.em & htmlcolors.red | "This is tagged", twin_tagged)

if __name__ == '__main__':
    unittest.main(buffer=True)
