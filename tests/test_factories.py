#!/usr/bin/env python
import pytest
from plumbum import colors
from plumbum.colorlib.styles import ANSIStyle as Style, ColorNotFound
from plumbum.colorlib import htmlcolors
import sys


class TestImportColors:
    def testDifferentImports(self):
        import plumbum.colors
        from plumbum.colors import bold
        from plumbum.colors.fg import red
        assert str(red) == str(colors.red)
        assert str(bold) == str(colors.bold)

class TestANSIColor:
    
    def setup_method(self, method):
        colors.use_color = True

    def testColorSlice(self):
        vals = colors[:8]
        assert len(vals) == 8
        assert vals[1] == colors.red
        vals = colors[40:50]
        assert len(vals) == 10
        assert vals[1] == colors.full(41)

    def testLoadNumericalColor(self):
        assert colors.full(2) == colors[2]
        assert colors.simple(2) == colors(2)
        assert colors(54) == colors[54]
        assert colors(1,30,77) == colors.rgb(1,30,77)
        assert colors[1,30,77] == colors.rgb(1,30,77)

    def testColorStrings(self):
        assert '\033[0m' == colors.reset
        assert '\033[1m' == colors.bold
        assert '\033[39m' == colors.fg.reset

    def testNegateIsReset(self):
        assert colors.reset == ~colors
        assert colors.fg.reset == ~colors.fg
        assert colors.bg.reset == ~colors.bg

    def testFromPreviousColor(self):
        assert colors(colors.red) == colors.red
        assert colors(colors.bg.red) == colors.bg.red
        assert colors(colors.bold) == colors.bold

    def testFromCode(self):
        assert colors('\033[31m') == colors.red

    def testEmptyStyle(self):
        assert str(colors()) == ''
        assert str(colors('')) == ''
        assert str(colors(None)) == ''

    def testLoadColorByName(self):
        assert colors['LightBlue'] == colors.fg['LightBlue']
        assert colors.bg['light_green'] == colors.bg['LightGreen']
        assert colors['DeepSkyBlue1'] == colors['#00afff']
        assert colors['DeepSkyBlue1'] == colors.hex('#00afff')

        assert colors['DeepSkyBlue1'] == colors[39]
        assert colors.DeepSkyBlue1 == colors[39]
        assert colors.deepskyblue1 == colors[39]
        assert colors.Deep_Sky_Blue1 == colors[39]
        assert colors.RED == colors.red

        with pytest.raises(AttributeError):
            colors.Notacolorsatall


    def testMultiColor(self):
        sumcolors = colors.bold & colors.blue
        assert colors.bold.reset & colors.fg.reset == ~sumcolors

    def testSums(self):
        # Sums should not be communitave, last one is used
        assert colors.red == colors.blue & colors.red
        assert colors.bg.green == colors.bg.red & colors.bg.green

    def testRepresentations(self):
        colors1 = colors.full(87)
        assert colors1 == colors.DarkSlateGray2
        assert colors1.basic == colors.DarkSlateGray2
        assert str(colors1.basic) == str(colors.LightGray)

        colors2 = colors.rgb(1,45,214)
        assert str(colors2.full) == str(colors.Blue3A)


    def testFromAnsi(self):
        for c in colors[1:7]:
            assert c == colors.from_ansi(str(c))
        for c in colors.bg[1:7]:
            assert c == colors.from_ansi(str(c))
        for c in colors:
            assert c == colors.from_ansi(str(c))
        for c in colors.bg:
            assert c == colors.from_ansi(str(c))
        for c in colors[:16]:
            assert c == colors.from_ansi(str(c))
        for c in colors.bg[:16]:
            assert c == colors.from_ansi(str(c))
        for c in (colors.bold, colors.underline, colors.italics):
            assert c == colors.from_ansi(str(c))

        col = colors.bold & colors.fg.green & colors.bg.blue & colors.underline
        assert col == colors.from_ansi(str(col))
        col = colors.reset
        assert col == colors.from_ansi(str(col))

    def testWrappedColor(self):
        string = 'This is a string'
        wrapped = '\033[31mThis is a string\033[39m'
        assert colors.red.wrap(string) == wrapped
        assert colors.red | string == wrapped
        assert colors.red[string] == wrapped

        newcolors = colors.blue & colors.underline
        assert newcolors[string] == string | newcolors
        assert newcolors.wrap(string) == string | colors.blue & colors.underline

    def testUndoColor(self):
        assert '\033[39m' == ~colors.fg
        assert '\033[49m' == ~colors.bg
        assert '\033[22m' == ~colors.bold
        assert '\033[22m' == ~colors.dim
        for i in range(7):
            assert '\033[39m' == ~colors(i)
            assert '\033[49m' == ~colors.bg(i)
            assert '\033[39m' == ~colors.fg(i)
            assert '\033[49m' == ~colors.bg(i)
        for i in range(256):
            assert '\033[39m' == ~colors.fg[i]
            assert '\033[49m' == ~colors.bg[i]
        assert '\033[0m' == ~colors.reset
        assert colors.do_nothing == ~colors.do_nothing

        assert colors.bold.reset == ~colors.bold

    def testLackOfColor(self):
        Style.use_color = False
        assert '' == colors.fg.red
        assert '' == ~colors.fg
        assert '' == colors.fg['LightBlue']

    def testFromHex(self):
        with pytest.raises(ColorNotFound):
            colors.hex('asdf')

        with pytest.raises(ColorNotFound):
            colors.hex('#1234Z2')

        with pytest.raises(ColorNotFound):
            colors.hex(12)

    def testDirectCall(self, capsys):
        colors.blue()
        assert capsys.readouterr()[0] == str(colors.blue)


    def testPrint(self, capsys):
        colors.yellow.print('This is printed to stdout', end='')
        assert capsys.readouterr()[0] == str(colors.yellow.wrap('This is printed to stdout'))


class TestHTMLColor:
    def test_html(self):
        red_tagged = '<font color="#C00000">This is tagged</font>'
        assert htmlcolors.red["This is tagged"] == red_tagged
        assert "This is tagged" | htmlcolors.red == red_tagged

        twin_tagged = '<font color="#C00000"><em>This is tagged</em></font>'
        assert "This is tagged" |  htmlcolors.red & htmlcolors.em == twin_tagged
        assert "This is tagged" | htmlcolors.em & htmlcolors.red == twin_tagged
        assert htmlcolors.em & htmlcolors.red | "This is tagged" == twin_tagged

