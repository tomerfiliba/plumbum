#!/usr/bin/env python3
from __future__ import annotations

import pytest

from plumbum import colors
from plumbum.colorlib import htmlcolors
from plumbum.colorlib.styles import ANSIStyle as Style
from plumbum.colorlib.styles import ColorNotFound


class TestImportColors:
    def testDifferentImports(self):
        from plumbum.colors import bold
        from plumbum.colors.fg import red

        assert str(red) == str(colors.red)
        assert str(bold) == str(colors.bold)


class TestANSIColor:
    def setup_method(self, method):  # noqa: ARG002
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
        assert colors(1, 30, 77) == colors.rgb(1, 30, 77)
        assert colors[1, 30, 77] == colors.rgb(1, 30, 77)

    def testColorStrings(self):
        assert colors.reset == "\033[0m"
        assert colors.bold == "\033[1m"
        assert colors.fg.reset == "\033[39m"

    def testNegateIsReset(self):
        assert colors.reset == ~colors
        assert colors.fg.reset == ~colors.fg
        assert colors.bg.reset == ~colors.bg

    def testFromPreviousColor(self):
        assert colors(colors.red) == colors.red
        assert colors(colors.bg.red) == colors.bg.red
        assert colors(colors.bold) == colors.bold

    def testFromCode(self):
        assert colors("\033[31m") == colors.red

    def testEmptyStyle(self):
        assert str(colors()) == ""
        assert str(colors("")) == ""
        assert str(colors(None)) == ""

    def testLoadColorByName(self):
        assert colors["LightBlue"] == colors.fg["LightBlue"]
        assert colors.bg["light_green"] == colors.bg["LightGreen"]
        assert colors["DeepSkyBlue1"] == colors["#00afff"]
        assert colors["DeepSkyBlue1"] == colors.hex("#00afff")

        assert colors["DeepSkyBlue1"] == colors[39]
        assert colors.DeepSkyBlue1 == colors[39]
        assert colors.deepskyblue1 == colors[39]
        assert colors.Deep_Sky_Blue1 == colors[39]
        assert colors.red == colors.RED

        with pytest.raises(AttributeError):
            colors.Notacolorsatall  # noqa: B018

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

        colors2 = colors.rgb(1, 45, 214)
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

    def testFromAnsiString(self):
        mystr = "\033[31mThis is a string\033[39m"
        seq = list(colors.from_ansi_string(mystr))
        assert seq == [colors.red, "This is a string", colors.fg.reset]
        assert colors.sequence_to_string(seq) == mystr

    def testWrappedColor(self):
        string = "This is a string"
        wrapped = "\033[31mThis is a string\033[39m"
        assert colors.red.wrap(string) == wrapped
        assert colors.red | string == wrapped
        assert colors.red[string] == wrapped

        newcolors = colors.blue & colors.underline
        assert newcolors[string] == string | newcolors
        assert newcolors.wrap(string) == string | colors.blue & colors.underline

    def testUndoColor(self):
        assert ~colors.fg == "\033[39m"
        assert ~colors.bg == "\033[49m"
        assert ~colors.bold == "\033[22m"
        assert ~colors.dim == "\033[22m"
        for i in range(7):
            assert ~colors(i) == "\033[39m"
            assert ~colors.bg(i) == "\033[49m"
            assert ~colors.fg(i) == "\033[39m"
            assert ~colors.bg(i) == "\033[49m"
        for i in range(256):
            assert ~colors.fg[i] == "\033[39m"
            assert ~colors.bg[i] == "\033[49m"
        assert ~colors.reset == "\033[0m"
        assert colors.do_nothing == ~colors.do_nothing

        assert colors.bold.reset == ~colors.bold

    def testLackOfColor(self):
        Style.use_color = False
        assert colors.fg.red == ""
        assert ~colors.fg == ""
        assert colors.fg["LightBlue"] == ""

    def testFromHex(self):
        with pytest.raises(ColorNotFound):
            colors.hex("asdf")

        with pytest.raises(ColorNotFound):
            colors.hex("#1234Z2")

        with pytest.raises(ColorNotFound):
            colors.hex(12)

    def testDirectCall(self, capsys):
        colors.blue()
        assert capsys.readouterr()[0] == str(colors.blue)

    def testPrint(self, capsys):
        colors.yellow.print("This is printed to stdout", end="")
        assert capsys.readouterr()[0] == str(
            colors.yellow.wrap("This is printed to stdout")
        )


class TestHTMLColor:
    def test_html(self):
        red_tagged = '<font color="#C00000">This is tagged</font>'
        assert htmlcolors.red["This is tagged"] == red_tagged
        assert "This is tagged" | htmlcolors.red == red_tagged

        twin_tagged = '<font color="#C00000"><em>This is tagged</em></font>'
        assert "This is tagged" | htmlcolors.red & htmlcolors.em == twin_tagged
        assert "This is tagged" | htmlcolors.em & htmlcolors.red == twin_tagged
        assert htmlcolors.em & htmlcolors.red | "This is tagged" == twin_tagged

    def test_from_ansi_string(self):
        mystr = "\033[31mThis is a string\033[39m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        assert seq == [htmlcolors.red, "This is a string", htmlcolors.fg.reset]
        assert (
            htmlcolors.sequence_to_string(seq)
            == '<font color="#C00000">This is a string</font>'
        )

    def test_from_ansi_string_global_reset(self):
        mystr = "\033[31mThis is a string\033[0m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        # Base from_ansi_string produces a global reset style for code 0
        assert seq == [htmlcolors.red, "This is a string", htmlcolors.reset]
        assert (
            htmlcolors.sequence_to_string(seq)
            == '<font color="#C00000">This is a string</font>'
        )

    def test_from_ansi_string_with_bold(self):
        mystr = "\033[31mThis is a string\033[1m with bold\033[39m and reset\033[0m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        # Base from_ansi_string produces plain styles, sequence_to_string handles closing order
        assert seq == [
            htmlcolors.red,
            "This is a string",
            htmlcolors.bold,
            " with bold",
            htmlcolors.fg.reset,  # Code 39 foreground reset
            " and reset",
            htmlcolors.reset,  # Code 0 global reset
        ]
        assert (
            htmlcolors.sequence_to_string(seq)
            == '<font color="#C00000">This is a string<b> with bold</b></font> and reset'
        )

    def test_from_ansi_string_background_only(self):
        # ANSI 41: red background, 49: background reset
        mystr = "\033[41mThis is a string\033[49m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        # Ensure sequence_to_string correctly renders a pure background color span
        assert (
            htmlcolors.sequence_to_string(seq) == htmlcolors.bg.red["This is a string"]
        )

    def test_from_ansi_string_foreground_and_background(self):
        # ANSI 31: red foreground, 44: blue background, 39: fg reset, 49: bg reset
        mystr = "\033[31;44mThis is a string\033[39;49m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        # Expected HTML is what we'd get by applying both fg and bg styles together
        expected = "This is a string" | (htmlcolors.red & htmlcolors.bg.blue)
        assert htmlcolors.sequence_to_string(seq) == expected

    def test_from_ansi_string_background_with_global_reset(self):
        # ANSI 44: blue background, 0: global reset
        mystr = "\033[44mThis is a string\033[0m"
        seq = list(htmlcolors.from_ansi_string(mystr))
        # Global reset should close the background span at the end, yielding the same as bg only
        assert (
            htmlcolors.sequence_to_string(seq) == htmlcolors.bg.blue["This is a string"]
        )
